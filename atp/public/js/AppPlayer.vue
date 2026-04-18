<script setup>
import { ref, onMounted, computed, reactive, watch } from 'vue';

const enrollmentName = ref('');
const course = ref(null);
const flow = ref(null);
const currentNodeId = ref(null);
const loading = ref(true);
const completed = ref(false);
const finalScore = ref(null);
const reviewMode = ref(false);
const initError = ref(null); // null | 'no-enrollment' | 'not-found' | 'prerequisites'
const unmetPrereqs = ref([]); // course titles of unmet prerequisites
const nodeEntryTime = ref(null); // for time-on-task sensor

// Quiz state per node
const quizAnswers = reactive({});
const quizSubmitted = reactive({});
const taskDone = reactive({});
const surveyAnswers = reactive({});

const props = defineProps(['enrollmentName']);

// ── Computed ──────────────────────────────────────────────────────────────

const currentNode = computed(() => {
	if (!flow.value || !currentNodeId.value) return null;
	return flow.value.nodes.find((n) => n.id === currentNodeId.value);
});

const nextNode = computed(() => {
	if (!flow.value || !currentNodeId.value) return null;
	const edge = flow.value.edges.find((e) => e.source === currentNodeId.value);
	return edge ? flow.value.nodes.find((n) => n.id === edge.target) : null;
});

const previousNode = computed(() => {
	if (!flow.value || !currentNodeId.value) return null;
	const edge = flow.value.edges.find((e) => e.target === currentNodeId.value);
	return edge ? flow.value.nodes.find((n) => n.id === edge.source) : null;
});

const totalNodes = computed(() => flow.value?.nodes?.length || 0);

const currentIndex = computed(() => {
	if (!flow.value || !currentNodeId.value) return 0;
	return flow.value.nodes.findIndex((n) => n.id === currentNodeId.value) + 1;
});

const progressPercent = computed(() => {
	if (!totalNodes.value) return 0;
	return Math.round(((currentIndex.value - 1) / totalNodes.value) * 100);
});

const isLastNode = computed(() => !nextNode.value);

// ── Init ──────────────────────────────────────────────────────────────────

const init = async () => {
	if (props.enrollmentName) enrollmentName.value = props.enrollmentName;
	else if (window.cur_enrollment) enrollmentName.value = window.cur_enrollment;
	else {
		const route = frappe.get_route();
		if (route[0] === 'course_player' && route[1]) {
			enrollmentName.value = decodeURIComponent(route[1]);
			window.cur_enrollment = enrollmentName.value;
		} else {
			const params = new URLSearchParams(window.location.search);
			const q = params.get('enrollment');
			if (q) { enrollmentName.value = decodeURIComponent(q); window.cur_enrollment = enrollmentName.value; }
		}
	}

	if (!enrollmentName.value) {
		initError.value = 'no-enrollment';
		loading.value = false;
		return;
	}

	try {
		const enrollment = await frappe.db.get_doc('Course Enrollment', enrollmentName.value);

		if (enrollment.status === 'Completed') {
			reviewMode.value = true;
			const courseDoc = await frappe.db.get_doc('Course', enrollment.course);
			course.value = courseDoc;
			if (courseDoc.flow_data) {
				try { flow.value = JSON.parse(courseDoc.flow_data); } catch { /* corrupted — treat as empty */ }
				if (flow.value) currentNodeId.value = findStartNode(flow.value);
			}
			loading.value = false;
			return;
		}

		const courseDoc = await frappe.db.get_doc('Course', enrollment.course);
		course.value = courseDoc;

		// Check prerequisites
		if (courseDoc.scene_config) {
			try {
				const sc = JSON.parse(courseDoc.scene_config);
				const prereqs = sc.prerequisites || [];
				if (prereqs.length > 0) {
					const completed_enrollments = await frappe.db.get_list('Course Enrollment', {
						filters: { student: frappe.session.user, course: ['in', prereqs], status: 'Completed' },
						fields: ['course'],
						limit: prereqs.length + 1,
					});
					const completedSet = new Set(completed_enrollments.map((e) => e.course));
					const unmet = prereqs.filter((p) => !completedSet.has(p));
					if (unmet.length > 0) {
						// Fetch titles for unmet prereqs
						const titles = await Promise.all(
							unmet.map(async (p) => {
								try {
									const { message } = await frappe.call({
										method: 'frappe.client.get_value',
										args: { doctype: 'Course', filters: p, fieldname: 'title' },
									});
									return message?.title || p;
								} catch { return p; }
							}),
						);
						unmetPrereqs.value = titles;
						initError.value = 'prerequisites';
						loading.value = false;
						return;
					}
				}
			} catch {}
		}

		if (courseDoc.flow_data) {
			try { flow.value = JSON.parse(courseDoc.flow_data); } catch { /* corrupted — treat as empty */ }
			if (flow.value) {
				const startId = findStartNode(flow.value);
				if (enrollment.progress) {
					let saved = null;
					try { saved = JSON.parse(enrollment.progress); } catch { /* corrupted — start from beginning */ }
					const exists = saved && flow.value.nodes.find((n) => n.id === saved.currentNodeId);
					currentNodeId.value = exists ? saved.currentNodeId : startId;
					if (!exists) updateProgress();
				} else {
					currentNodeId.value = startId;
				}
			}
		}
	} catch (e) {
		console.error('AppPlayer init error', e);
		initError.value = 'not-found';
	} finally {
		loading.value = false;
	}
};

const findStartNode = (flowData) => {
	if (!flowData?.nodes?.length) return null;
	const targets = new Set(flowData.edges.map((e) => e.target));
	const start = flowData.nodes.find((n) => !targets.has(n.id));
	return start ? start.id : flowData.nodes[0]?.id;
};

// ── Navigation ────────────────────────────────────────────────────────────

const canProceed = computed(() => {
	if (reviewMode.value) return true;
	const node = currentNode.value;
	if (!node) return true;
	const type = node.data?.componentType;
	if (type === 'Quiz') {
		return !!quizSubmitted[node.id];
	}
	if (type === 'Task') {
		return !!taskDone[node.id];
	}
	return true;
});

const navigating = ref(false);

const next = async () => {
	if (!canProceed.value || navigating.value) return;
	navigating.value = true;
	try {
		if (nextNode.value) {
			currentNodeId.value = nextNode.value.id;
			if (!reviewMode.value) await updateProgress();
		} else {
			if (reviewMode.value) {
				frappe.set_route('student_dashboard');
			} else {
				await finishCourse();
			}
		}
	} finally {
		navigating.value = false;
	}
};

const prev = async () => {
	if (navigating.value) return;
	navigating.value = true;
	try {
		if (previousNode.value) {
			currentNodeId.value = previousNode.value.id;
			if (!reviewMode.value) await updateProgress();
		}
	} finally {
		navigating.value = false;
	}
};

const updateProgress = async () => {
	const timeSpentSeconds = nodeEntryTime.value ? Math.round((Date.now() - nodeEntryTime.value) / 1000) : 0;
	nodeEntryTime.value = Date.now();

	const nodeConfig = currentNode.value?.data?.config || {};
	const sensorData = JSON.stringify({
		timeSpentSeconds,
		nodeComponentType: currentNode.value?.data?.componentType || null,
		nodeSensors: nodeConfig.sensors || null,
		nodeLearnerModel: nodeConfig.learnerModel || null,
	});

	try {
		await frappe.call({
			method: 'atp.atp.api.update_progress',
			args: {
				enrollment_name: enrollmentName.value,
				current_node_id: currentNodeId.value,
				sensor_data: sensorData,
			},
		});
	} catch {
		// Fallback to direct set_value (no sensor data)
		try {
			await frappe.call({
				method: 'frappe.client.set_value',
				args: {
					doctype: 'Course Enrollment',
					name: enrollmentName.value,
					fieldname: 'progress',
					value: JSON.stringify({ currentNodeId: currentNodeId.value }),
				},
			});
		} catch (e) {
			console.error('Progress save failed', e);
		}
	}
};

const finishCourse = async () => {
	try {
		await frappe.call({
			method: 'atp.atp.api.complete_course',
			args: { enrollment_name: enrollmentName.value },
		});
	} catch {
		// Fallback
		await frappe.call({
			method: 'frappe.client.set_value',
			args: {
				doctype: 'Course Enrollment',
				name: enrollmentName.value,
				fieldname: 'status',
				value: 'Completed',
			},
		});
	}
	completed.value = true;
};

// ── Quiz logic ────────────────────────────────────────────────────────────

const initQuizAnswers = (nodeId) => {
	if (!quizAnswers[nodeId]) quizAnswers[nodeId] = {};
};

const submitQuiz = (node) => {
	const questions = node.data?.config?.questions || [];
	let correct = 0;
	for (let i = 0; i < questions.length; i++) {
		if (quizAnswers[node.id]?.[i] === questions[i].correct) correct++;
	}
	finalScore.value = questions.length ? Math.round((correct / questions.length) * 100) : 100;
	quizSubmitted[node.id] = { correct, total: questions.length, pct: finalScore.value };
};

const allQuizAnswered = (node) => {
	const questions = node.data?.config?.questions || [];
	if (!questions.length) return true;
	return questions.every((_, i) => quizAnswers[node.id]?.[i] !== undefined);
};

const retryQuiz = (nodeId) => {
	delete quizSubmitted[nodeId];
	quizAnswers[nodeId] = {};
};

// ── Survey logic ──────────────────────────────────────────────────────────

const initSurveyAnswers = (nodeId) => {
	if (!surveyAnswers[nodeId]) surveyAnswers[nodeId] = {};
};

// ── Video embed ───────────────────────────────────────────────────────────

const getVideoEmbed = (url) => {
	if (!url) return null;
	const ytMatch = url.match(/^.*(youtu\.be\/|v\/|u\/\w\/|embed\/|watch\?v=|&v=)([^#&?]*).*/);
	if (ytMatch && ytMatch[2].length === 11) return `https://www.youtube.com/embed/${ytMatch[2]}`;
	const vimeoMatch = url.match(/(?:https?:\/\/)?(?:www\.)?vimeo\.com\/(.+)/);
	if (vimeoMatch) return `https://player.vimeo.com/video/${vimeoMatch[1]}`;
	return null;
};

const goToDashboard = () => frappe.set_route('student_dashboard');

onMounted(() => init());

// Initialize answer stores synchronously before render to avoid v-model crash
// Also reset time-on-task timer when node changes
watch(currentNode, (node) => {
	if (!node) return;
	nodeEntryTime.value = Date.now();
	if (node.data?.componentType === 'Quiz') initQuizAnswers(node.id);
	else if (node.data?.componentType === 'Survey') initSurveyAnswers(node.id);
}, { immediate: true, flush: 'sync' });
</script>

<template>
	<div class="player-wrap">
		<!-- Loading -->
		<div v-if="loading" class="player-loading">
			<div class="spinner"></div>
			<span>Loading course…</span>
		</div>

		<!-- Error: no enrollment param -->
		<div v-else-if="initError === 'no-enrollment'" class="player-error">
			<div class="error-icon">📋</div>
			<p>No course selected.</p>
			<p class="error-sub">Return to your dashboard and open a course to begin.</p>
			<button class="btn-primary-lg" @click="goToDashboard">
				Back to Dashboard
			</button>
		</div>

		<!-- Error: enrollment not found / permission denied -->
		<div v-else-if="initError === 'not-found'" class="player-error">
			<div class="error-icon">⚠️</div>
			<p>Course not found or access denied.</p>
			<p class="error-sub">This course may have been removed or your access has changed.</p>
			<button class="btn-primary-lg" @click="goToDashboard">
				Back to Dashboard
			</button>
		</div>

		<!-- Error: prerequisites not met -->
		<div v-else-if="initError === 'prerequisites'" class="player-error">
			<div class="error-icon">🔒</div>
			<p>This course is locked.</p>
			<p class="error-sub">You need to complete the following course{{ unmetPrereqs.length !== 1 ? 's' : '' }} first:</p>
			<ul class="prereq-list">
				<li v-for="t in unmetPrereqs" :key="t">{{ t }}</li>
			</ul>
			<button class="btn-primary-lg" @click="goToDashboard">
				Back to Dashboard
			</button>
		</div>

		<!-- Error: course has no content yet -->
		<div v-else-if="!currentNode && !completed" class="player-error">
			<div class="error-icon">⚙️</div>
			<p>No content configured for this course.</p>
			<div class="error-debug">
				Enrollment: {{ enrollmentName || 'unknown' }} ·
				Nodes: {{ flow?.nodes?.length || 0 }}
			</div>
		</div>

		<!-- Completion screen -->
		<div v-else-if="completed" class="completion-screen">
			<div class="completion-icon">🎉</div>
			<h2>Course Completed!</h2>
			<p>Great work completing <strong>{{ course?.title }}</strong>.</p>
			<div v-if="finalScore !== null" class="score-box">
				Final quiz score: <strong>{{ finalScore }}%</strong>
			</div>
			<button class="btn-primary-lg" @click="goToDashboard">
				Back to Dashboard
			</button>
		</div>

		<!-- Active course -->
		<div v-else class="player-card">
			<!-- Card header -->
			<div class="card-header">
				<div v-if="reviewMode" class="review-banner">Review Mode — course already completed</div>
				<div class="header-top">
					<button class="back-link" @click="goToDashboard">
						← Dashboard
					</button>
					<span class="step-counter">{{ currentIndex }} / {{ totalNodes }}</span>
				</div>
				<h1 class="course-title">{{ course?.title }}</h1>
				<div class="step-label">{{ currentNode?.label }}</div>
				<!-- Progress bar -->
				<div class="header-progress">
					<div class="hprog-fill" :style="{ width: progressPercent + '%' }"></div>
				</div>
			</div>

			<!-- Card body — dynamic content -->
			<div class="card-body">
				<!-- PDF -->
				<template v-if="currentNode?.data?.componentType === 'PDF'">
					<div class="content-intro" v-if="currentNode.data.config.description">
						{{ currentNode.data.config.description }}
					</div>
					<div v-if="currentNode.data.config.fileUrl" class="pdf-container">
						<iframe :src="currentNode.data.config.fileUrl" class="content-iframe" allowfullscreen></iframe>
					</div>
					<div v-if="currentNode.data.config.fileUrl" class="content-actions">
						<a :href="currentNode.data.config.fileUrl" target="_blank" class="action-link">Open in new tab ↗</a>
					</div>
					<div v-if="!currentNode.data.config.fileUrl" class="coming-soon">
						<div class="coming-soon-icon">📄</div>
						<p class="coming-soon-title">Content coming soon</p>
						<p class="coming-soon-sub">This material will be available shortly.</p>
					</div>
				</template>

				<!-- Video -->
				<template v-else-if="currentNode?.data?.componentType === 'Video'">
					<div class="content-intro" v-if="currentNode.data.config.description">
						{{ currentNode.data.config.description }}
					</div>
					<div v-if="currentNode.data.config.videoUrl">
						<div v-if="getVideoEmbed(currentNode.data.config.videoUrl)" class="video-wrapper">
							<iframe
								:src="getVideoEmbed(currentNode.data.config.videoUrl)"
								frameborder="0"
								allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
								allowfullscreen
							></iframe>
						</div>
						<div v-else class="content-actions">
							<a :href="currentNode.data.config.videoUrl" target="_blank" class="action-link">Open Video ↗</a>
						</div>
					</div>
					<div v-else class="coming-soon">
						<div class="coming-soon-icon">🎬</div>
						<p class="coming-soon-title">Content coming soon</p>
						<p class="coming-soon-sub">This video will be available shortly.</p>
					</div>
				</template>

				<!-- Presentation -->
				<template v-else-if="currentNode?.data?.componentType === 'Presentation'">
					<div v-if="currentNode.data.config.presentationUrl" class="presentation-area">
						<div class="pres-icon">📊</div>
						<p>{{ currentNode.label }}</p>
						<a :href="currentNode.data.config.presentationUrl" target="_blank" class="action-link">
							Download / View Presentation ↗
						</a>
					</div>
					<div v-else class="coming-soon">
						<div class="coming-soon-icon">📊</div>
						<p class="coming-soon-title">Content coming soon</p>
						<p class="coming-soon-sub">This presentation will be available shortly.</p>
					</div>
				</template>

				<!-- Quiz -->
				<template v-else-if="currentNode?.data?.componentType === 'Quiz'">
					<div v-if="!currentNode.data.config.questions?.length" class="empty-content">
						No questions configured.
					</div>
					<div v-else>
						<div
							v-if="!quizSubmitted[currentNode.id]"
							class="quiz-form"
						>
							<div
								v-for="(q, qIdx) in currentNode.data.config.questions"
								:key="qIdx"
								class="quiz-q"
							>
								<div class="q-text">{{ qIdx + 1 }}. {{ q.text }}</div>
								<div class="q-options">
									<label
										v-for="(opt, oIdx) in q.options"
										:key="oIdx"
										class="q-option"
									>
										<input
											type="radio"
											:name="`quiz-${currentNode.id}-q${qIdx}`"
											:value="oIdx"
											v-model="quizAnswers[currentNode.id][qIdx]"
										/>
										{{ opt }}
									</label>
								</div>
							</div>
							<button
								class="btn-submit-quiz"
								:disabled="!allQuizAnswered(currentNode)"
								@click="submitQuiz(currentNode)"
							>
								Submit Quiz
							</button>
						</div>
						<div v-else class="quiz-result-panel">
							<div :class="['result-badge', quizSubmitted[currentNode.id].pct >= 70 ? 'pass' : 'retry']">
								{{ quizSubmitted[currentNode.id].pct >= 70 ? '✓ Passed' : '↺ Needs Review' }}
							</div>
							<div class="result-score">
								{{ quizSubmitted[currentNode.id].correct }} / {{ quizSubmitted[currentNode.id].total }} correct
								({{ quizSubmitted[currentNode.id].pct }}%)
							</div>
							<div class="result-answers">
								<div
									v-for="(q, qIdx) in currentNode.data.config.questions"
									:key="qIdx"
									class="result-row"
									:class="{ correct: quizAnswers[currentNode.id][qIdx] === q.correct, wrong: quizAnswers[currentNode.id][qIdx] !== q.correct }"
								>
									<span class="result-icon">{{ quizAnswers[currentNode.id][qIdx] === q.correct ? '✓' : '✗' }}</span>
									<div>
										<div class="result-q">{{ q.text }}</div>
										<div class="result-answer">
											Your answer: {{ q.options[quizAnswers[currentNode.id][qIdx]] || '—' }}
											<span v-if="quizAnswers[currentNode.id][qIdx] !== q.correct" class="correct-answer">
												· Correct: {{ q.options[q.correct] }}
											</span>
										</div>
									</div>
								</div>
							</div>
							<button
								v-if="!reviewMode"
								class="btn-retry-quiz"
								@click="retryQuiz(currentNode.id)"
							>
								Try Again
							</button>
						</div>
					</div>
				</template>

				<!-- Task -->
				<template v-else-if="currentNode?.data?.componentType === 'Task'">
					<div class="task-card">
						<div class="task-instructions" v-if="currentNode.data.config.instructions">
							{{ currentNode.data.config.instructions }}
						</div>
						<div class="task-criteria" v-if="currentNode.data.config.completionCriteria">
							<strong>Completion:</strong> {{ currentNode.data.config.completionCriteria }}
						</div>
						<label class="task-done-check">
							<input type="checkbox" v-model="taskDone[currentNode.id]" />
							I have completed this task
						</label>
					</div>
				</template>

				<!-- Survey -->
				<template v-else-if="currentNode?.data?.componentType === 'Survey'">
					<div
						class="survey-form"
					>
						<div
							v-for="(q, qIdx) in (currentNode.data.config.questions || [])"
							:key="qIdx"
							class="survey-q"
						>
							<div class="q-text">{{ qIdx + 1 }}. {{ q.text }}</div>
							<textarea
								v-if="q.type === 'text'"
								v-model="surveyAnswers[currentNode.id][qIdx]"
								class="survey-text"
								placeholder="Your answer…"
							></textarea>
							<div v-else-if="q.type === 'scale'" class="scale-row">
								<span
									v-for="n in 5"
									:key="n"
									class="scale-btn"
									:class="{ active: surveyAnswers[currentNode.id]?.[qIdx] === n }"
									@click="surveyAnswers[currentNode.id][qIdx] = n"
								>{{ n }}</span>
							</div>
							<div v-else-if="q.type === 'mcq'" class="q-options">
								<label v-for="(opt, oIdx) in (q.options || [])" :key="oIdx" class="q-option">
									<input
										type="radio"
										:name="`survey-${currentNode.id}-q${qIdx}`"
										:value="oIdx"
										v-model="surveyAnswers[currentNode.id][qIdx]"
									/>
									{{ opt }}
								</label>
							</div>
						</div>
						<div v-if="!currentNode.data.config.questions?.length" class="empty-content">
							No survey questions configured.
						</div>
					</div>
				</template>

				<!-- Virtual Agent -->
				<template v-else-if="currentNode?.data?.componentType === 'Virtual Agent'">
					<div class="content-intro" v-if="currentNode.data.config.description">
						{{ currentNode.data.config.description }}
					</div>
					<div v-if="currentNode.data.config.agentUrl" class="agent-embed">
						<iframe
							:src="currentNode.data.config.agentUrl"
							class="content-iframe agent-iframe"
							allow="microphone"
						></iframe>
						<div class="content-actions">
							<a :href="currentNode.data.config.agentUrl" target="_blank" class="action-link">Open in new tab ↗</a>
						</div>
					</div>
					<div v-else class="empty-content">No agent URL configured.</div>
				</template>

				<!-- Fallback -->
				<template v-else>
					<div class="placeholder-content">
						<div class="placeholder-icon">📋</div>
						<p>{{ currentNode?.data?.componentType }} — no content yet.</p>
					</div>
				</template>
			</div>

			<!-- Card footer -->
			<div class="card-footer">
				<div class="step-label-small">
					{{ currentNode?.label }}
				</div>
				<div class="nav-btns">
					<button @click="prev" :disabled="!previousNode" class="nav-btn secondary">
						← Previous
					</button>
					<button
						@click="next"
						:disabled="!canProceed"
						class="nav-btn primary"
						:title="!canProceed ? 'Complete this step to continue' : ''"
					>
						{{ isLastNode ? (reviewMode ? 'Back to Dashboard' : 'Finish Course ✓') : 'Next →' }}
					</button>
				</div>
			</div>
		</div>
	</div>
</template>

<style scoped>
.player-wrap {
	max-width: 860px;
	margin: 1.5rem auto;
	font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
	padding: 0 1rem;
}

/* Loading */
.player-loading {
	display: flex;
	flex-direction: column;
	align-items: center;
	gap: 1rem;
	padding: 4rem;
	color: #6b7280;
}

.spinner {
	width: 32px;
	height: 32px;
	border: 3px solid #e5e7eb;
	border-top-color: #3b82f6;
	border-radius: 50%;
	animation: spin 0.7s linear infinite;
}

@keyframes spin { to { transform: rotate(360deg); } }

/* Error */
.player-error {
	text-align: center;
	padding: 3rem 1rem;
}

.error-icon { font-size: 3rem; margin-bottom: 0.75rem; }

.error-sub {
	font-size: 0.82rem;
	color: #9ca3af;
	margin: 0.25rem 0 0.75rem;
}

.prereq-list {
	list-style: none;
	padding: 0;
	margin: 0 0 1.5rem;
}

.prereq-list li {
	font-size: 0.875rem;
	font-weight: 600;
	color: #374151;
	padding: 0.3rem 0.75rem;
	background: #f3f4f6;
	border-radius: 5px;
	margin-bottom: 0.3rem;
}

.error-debug {
	margin-top: 1rem;
	font-size: 0.75rem;
	color: #9ca3af;
	font-family: monospace;
}

/* Content coming soon */
.coming-soon {
	text-align: center;
	padding: 3rem 1rem;
}

.coming-soon-icon {
	font-size: 2.5rem;
	margin-bottom: 0.75rem;
}

.coming-soon-title {
	font-size: 0.95rem;
	font-weight: 600;
	color: #374151;
	margin: 0 0 0.3rem;
}

.coming-soon-sub {
	font-size: 0.82rem;
	color: #9ca3af;
	margin: 0;
}

/* Completion */
.completion-screen {
	text-align: center;
	padding: 4rem 2rem;
	background: #ffffff;
	border-radius: 12px;
	border: 1px solid #e5e7eb;
	box-shadow: 0 4px 8px rgba(0,0,0,0.06);
}

.completion-icon { font-size: 4rem; margin-bottom: 1rem; }

.completion-screen h2 {
	font-size: 1.75rem;
	font-weight: 700;
	color: #111827;
	margin: 0 0 0.5rem;
}

.completion-screen p { color: #6b7280; margin-bottom: 1.5rem; }

.score-box {
	display: inline-block;
	background: #dcfce7;
	color: #166534;
	padding: 0.5rem 1.25rem;
	border-radius: 999px;
	font-weight: 600;
	font-size: 0.9rem;
	margin-bottom: 1.5rem;
}

.btn-primary-lg {
	padding: 0.65rem 2rem;
	background: #3b82f6;
	color: #ffffff;
	border: none;
	border-radius: 6px;
	font-size: 0.95rem;
	font-weight: 600;
	cursor: pointer;
	transition: background 0.15s;
}

.btn-primary-lg:hover { background: #2563eb; }

/* Player card */
.player-card {
	background: #ffffff;
	border-radius: 12px;
	border: 1px solid #e5e7eb;
	box-shadow: 0 4px 12px rgba(0,0,0,0.06);
	overflow: hidden;
}

/* Header */
.card-header {
	background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%);
	color: #ffffff;
	padding: 1.25rem 1.5rem 1rem;
}

.review-banner {
	background: rgba(255,255,255,0.18);
	border: 1px solid rgba(255,255,255,0.35);
	border-radius: 4px;
	font-size: 0.72rem;
	font-weight: 700;
	letter-spacing: 0.04em;
	text-transform: uppercase;
	padding: 0.2rem 0.65rem;
	display: inline-block;
	margin-bottom: 0.6rem;
}

.header-top {
	display: flex;
	justify-content: space-between;
	align-items: center;
	margin-bottom: 0.75rem;
}

.back-link {
	background: rgba(255,255,255,0.15);
	border: none;
	color: #ffffff;
	font-size: 0.78rem;
	font-weight: 600;
	cursor: pointer;
	padding: 0.25rem 0.6rem;
	border-radius: 4px;
	transition: background 0.15s;
}

.back-link:hover { background: rgba(255,255,255,0.25); }

.step-counter {
	font-size: 0.78rem;
	opacity: 0.85;
	font-weight: 600;
}

.course-title {
	font-size: 1.3rem;
	font-weight: 700;
	margin: 0 0 0.3rem;
	line-height: 1.3;
}

.step-label {
	font-size: 0.82rem;
	opacity: 0.85;
	margin-bottom: 0.75rem;
}

.header-progress {
	height: 4px;
	background: rgba(255,255,255,0.25);
	border-radius: 999px;
	overflow: hidden;
}

.hprog-fill {
	height: 100%;
	background: #ffffff;
	border-radius: 999px;
	transition: width 0.4s ease;
}

/* Body */
.card-body {
	padding: 1.75rem 1.5rem;
	min-height: 220px;
}

.content-intro {
	color: #4b5563;
	font-size: 0.9rem;
	margin-bottom: 1rem;
	line-height: 1.5;
}

.content-iframe {
	width: 100%;
	height: 480px;
	border: none;
	border-radius: 6px;
}

.content-actions {
	margin-top: 0.75rem;
	text-align: right;
}

.action-link {
	font-size: 0.82rem;
	color: #3b82f6;
	font-weight: 600;
	text-decoration: none;
}

.action-link:hover { text-decoration: underline; }

.empty-content {
	text-align: center;
	color: #9ca3af;
	padding: 2rem;
	font-style: italic;
}

/* Video */
.video-wrapper {
	position: relative;
	padding-bottom: 56.25%;
	height: 0;
	background: #000;
	border-radius: 8px;
	overflow: hidden;
}

.video-wrapper iframe {
	position: absolute;
	inset: 0;
	width: 100%;
	height: 100%;
}

/* Presentation */
.presentation-area {
	text-align: center;
	padding: 2rem;
}

.pres-icon { font-size: 3rem; margin-bottom: 0.75rem; }

/* Quiz */
.quiz-form {
	display: flex;
	flex-direction: column;
	gap: 1.25rem;
}

.quiz-q {
	background: #f9fafb;
	border: 1px solid #e5e7eb;
	border-radius: 6px;
	padding: 1rem;
}

.q-text {
	font-weight: 600;
	color: #111827;
	margin-bottom: 0.75rem;
	font-size: 0.9rem;
}

.q-options {
	display: flex;
	flex-direction: column;
	gap: 0.4rem;
}

.q-option {
	display: flex;
	align-items: center;
	gap: 0.5rem;
	font-size: 0.875rem;
	color: #374151;
	cursor: pointer;
	padding: 0.25rem 0;
}

.q-option input[type="radio"] {
	accent-color: #3b82f6;
	cursor: pointer;
}

.btn-submit-quiz {
	padding: 0.55rem 1.5rem;
	background: #3b82f6;
	color: #ffffff;
	border: none;
	border-radius: 6px;
	font-size: 0.875rem;
	font-weight: 600;
	cursor: pointer;
	transition: background 0.15s;
	align-self: flex-end;
}

.btn-submit-quiz:hover:not(:disabled) { background: #2563eb; }
.btn-submit-quiz:disabled { opacity: 0.5; cursor: not-allowed; }

.btn-retry-quiz {
	padding: 0.45rem 1.25rem;
	background: transparent;
	color: #6b7280;
	border: 1px solid #d1d5db;
	border-radius: 6px;
	font-size: 0.8rem;
	font-weight: 600;
	cursor: pointer;
	transition: all 0.15s;
	align-self: center;
}

.btn-retry-quiz:hover { background: #f3f4f6; color: #374151; border-color: #9ca3af; }

/* Quiz results */
.quiz-result-panel {
	display: flex;
	flex-direction: column;
	align-items: center;
	gap: 0.75rem;
}

.result-badge {
	padding: 0.4rem 1.25rem;
	border-radius: 999px;
	font-weight: 700;
	font-size: 0.9rem;
}

.result-badge.pass { background: #dcfce7; color: #166534; }
.result-badge.retry { background: #fef3c7; color: #92400e; }

.result-score {
	font-size: 1rem;
	font-weight: 600;
	color: #374151;
}

.result-answers {
	width: 100%;
	display: flex;
	flex-direction: column;
	gap: 0.5rem;
}

.result-row {
	display: flex;
	align-items: flex-start;
	gap: 0.75rem;
	padding: 0.6rem 0.75rem;
	border-radius: 6px;
	font-size: 0.85rem;
}

.result-row.correct { background: #f0fdf4; }
.result-row.wrong { background: #fff7ed; }

.result-icon { font-size: 1rem; flex-shrink: 0; }
.result-row.correct .result-icon { color: #22c55e; }
.result-row.wrong .result-icon { color: #ef4444; }

.result-q { font-weight: 600; color: #374151; }
.result-answer { font-size: 0.8rem; color: #6b7280; margin-top: 0.1rem; }
.correct-answer { color: #22c55e; font-weight: 600; }

/* Task */
.task-card {
	background: #f9fafb;
	border: 1px solid #e5e7eb;
	border-radius: 8px;
	padding: 1.25rem;
}

.task-instructions {
	color: #374151;
	line-height: 1.6;
	margin-bottom: 0.75rem;
	font-size: 0.9rem;
	white-space: pre-line;
}

.task-criteria {
	font-size: 0.82rem;
	color: #6b7280;
	margin-bottom: 1rem;
}

.task-done-check {
	display: flex;
	align-items: center;
	gap: 0.5rem;
	font-weight: 600;
	font-size: 0.875rem;
	color: #374151;
	cursor: pointer;
}

.task-done-check input[type="checkbox"] {
	accent-color: #3b82f6;
	width: 16px;
	height: 16px;
	cursor: pointer;
}

/* Survey */
.survey-form {
	display: flex;
	flex-direction: column;
	gap: 1.25rem;
}

.survey-q {
	background: #f9fafb;
	border: 1px solid #e5e7eb;
	border-radius: 6px;
	padding: 1rem;
}

.survey-text {
	width: 100%;
	min-height: 80px;
	resize: vertical;
	padding: 0.5rem 0.75rem;
	border: 1px solid #d1d5db;
	border-radius: 5px;
	font-size: 0.875rem;
	margin-top: 0.5rem;
	box-sizing: border-box;
}

.survey-text:focus {
	outline: none;
	border-color: #3b82f6;
	box-shadow: 0 0 0 2px rgba(59,130,246,0.12);
}

.scale-row {
	display: flex;
	gap: 0.5rem;
	margin-top: 0.5rem;
}

.scale-btn {
	width: 36px;
	height: 36px;
	display: flex;
	align-items: center;
	justify-content: center;
	border: 2px solid #e5e7eb;
	border-radius: 50%;
	font-weight: 700;
	font-size: 0.85rem;
	cursor: pointer;
	transition: all 0.15s;
}

.scale-btn:hover { border-color: #93c5fd; background: #eff6ff; }
.scale-btn.active { border-color: #3b82f6; background: #3b82f6; color: #ffffff; }

/* Agent */
.agent-embed { display: flex; flex-direction: column; }
.agent-iframe { height: 560px; }

/* Placeholder */
.placeholder-content {
	text-align: center;
	padding: 3rem 1rem;
	color: #9ca3af;
}

.placeholder-icon { font-size: 2.5rem; margin-bottom: 0.75rem; }

/* Footer */
.card-footer {
	background: #f9fafb;
	border-top: 1px solid #e5e7eb;
	padding: 0.85rem 1.5rem;
	display: flex;
	align-items: center;
	justify-content: space-between;
}

.step-label-small {
	font-size: 0.75rem;
	color: #9ca3af;
	font-weight: 500;
}

.nav-btns {
	display: flex;
	gap: 0.5rem;
}

.nav-btn {
	padding: 0.45rem 1.25rem;
	border-radius: 6px;
	font-size: 0.875rem;
	font-weight: 600;
	cursor: pointer;
	border: none;
	transition: all 0.15s;
}

.nav-btn.primary {
	background: #3b82f6;
	color: #ffffff;
}

.nav-btn.primary:hover:not(:disabled) { background: #2563eb; }
.nav-btn.primary:disabled { background: #93c5fd; cursor: not-allowed; }

.nav-btn.secondary {
	background: #f3f4f6;
	color: #374151;
}

.nav-btn.secondary:hover:not(:disabled) { background: #e5e7eb; }
.nav-btn.secondary:disabled { opacity: 0.4; cursor: not-allowed; }
</style>
