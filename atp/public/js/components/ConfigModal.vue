<script setup>
import { ref, watch, computed } from 'vue';

const props = defineProps({
	modelValue: Boolean,
	node: Object,
});

const emit = defineEmits(['update:modelValue', 'save', 'delete']);

const localConfig = ref({});
const uploading = ref(false);
const showAdaptive = ref(false);
const componentType = computed(() => props.node?.data?.componentType || '');

const availableScenarios = ref([]);
const loadingScenarios = ref(false);

const SENSOR_NODES = ['Microphone', 'Camera', 'External Sensor', 'Learner Model'];

watch(
	() => props.node,
	(newNode) => {
		if (newNode) {
			localConfig.value = { ...newNode.data.config, label: newNode.label };
			if (!localConfig.value.questions) localConfig.value.questions = [];
			if (!localConfig.value.sensors) localConfig.value.sensors = {};
			if (!localConfig.value.learnerModel) localConfig.value.learnerModel = { type: 'inherit' };
		}
		showAdaptive.value = false;
		// Lazy-load scenarios when a Scenario node is opened
		if (newNode?.data?.componentType === 'Scenario' && availableScenarios.value.length === 0 && !loadingScenarios.value) {
			loadingScenarios.value = true;
			frappe.call({ method: 'atp.atp.api_v2.get_scenario_list' })
				.then((r) => { availableScenarios.value = r.message || []; loadingScenarios.value = false; })
				.catch(() => { loadingScenarios.value = false; });
		}
	},
	{ immediate: true },
);

// ── Helpers ───────────────────────────────────────────────────────────────

const save = () => {
	if (props.node) {
		props.node.label = localConfig.value.label || componentType.value;
		props.node.data.config = { ...localConfig.value };
		emit('save', props.node);
	}
	emit('update:modelValue', false);
};

const deleteNode = () => {
	if (confirm('Delete this component?')) emit('delete', props.node);
};

const close = () => emit('update:modelValue', false);

const handleFileUpload = (event, field) => {
	const file = event.target.files[0];
	if (!file) return;
	uploading.value = true;
	const formData = new FormData();
	formData.append('file', file, file.name);
	formData.append('is_private', 0);
	formData.append('folder', 'Home');
	fetch('/api/method/upload_file', {
		method: 'POST',
		headers: { 'X-Frappe-CSRF-Token': frappe.csrf_token },
		body: formData,
	})
		.then((r) => r.json())
		.then((data) => {
			uploading.value = false;
			if (data.message?.file_url) {
				localConfig.value[field] = data.message.file_url;
				frappe.show_alert({ message: 'File uploaded', indicator: 'green' });
			} else {
				frappe.msgprint('Upload failed: ' + (data.exc || 'Unknown error'));
			}
		})
		.catch(() => {
			uploading.value = false;
			frappe.msgprint('Upload failed');
		});
};

// ── Quiz / Survey question builders ──────────────────────────────────────

const addQuestion = () => {
	if (!localConfig.value.questions) localConfig.value.questions = [];
	localConfig.value.questions.push({
		text: '',
		type: componentType.value === 'Quiz' ? 'mcq' : 'text',
		options: componentType.value === 'Quiz' ? ['', '', '', ''] : [],
		correct: 0,
	});
};

const removeQuestion = (idx) => {
	localConfig.value.questions.splice(idx, 1);
};

const addOption = (qIdx) => {
	localConfig.value.questions[qIdx].options.push('');
};

const removeOption = (qIdx, oIdx) => {
	localConfig.value.questions[qIdx].options.splice(oIdx, 1);
	if (localConfig.value.questions[qIdx].correct >= localConfig.value.questions[qIdx].options.length) {
		localConfig.value.questions[qIdx].correct = 0;
	}
};
</script>

<template>
	<div v-if="modelValue" class="modal-overlay" @click.self="close">
		<div class="modal-container">
			<!-- Header -->
			<div class="modal-header">
				<h3 class="modal-title">Configure {{ componentType }}</h3>
				<button @click="close" class="close-btn" aria-label="Close">
					<svg width="18" height="18" viewBox="0 0 18 18" fill="none">
						<path d="M2 2l14 14M16 2L2 16" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
					</svg>
				</button>
			</div>

			<!-- Body -->
			<div class="modal-body">
				<!-- Label (all types) -->
				<div class="field-group">
					<label>Label</label>
					<input v-model="localConfig.label" type="text" class="mc-input" placeholder="Node label" />
				</div>

				<!-- PDF -->
				<template v-if="componentType === 'PDF'">
					<div class="field-group">
						<label>PDF File</label>
						<div class="upload-row">
							<input v-model="localConfig.fileUrl" type="text" class="mc-input" placeholder="Paste URL or upload" />
							<label class="upload-btn">
								{{ uploading ? '…' : 'Upload' }}
								<input type="file" accept=".pdf" @change="handleFileUpload($event, 'fileUrl')" hidden />
							</label>
						</div>
					</div>
					<div class="field-group">
						<label>Description (optional)</label>
						<textarea v-model="localConfig.description" class="mc-input mc-textarea" placeholder="Brief description shown to student"></textarea>
					</div>
				</template>

				<!-- Video -->
				<template v-else-if="componentType === 'Video'">
					<div class="field-group">
						<label>Video URL or File</label>
						<div class="upload-row">
							<input v-model="localConfig.videoUrl" type="text" class="mc-input" placeholder="YouTube URL, Vimeo, or file URL" />
							<label class="upload-btn">
								{{ uploading ? '…' : 'Upload' }}
								<input type="file" accept="video/*" @change="handleFileUpload($event, 'videoUrl')" hidden />
							</label>
						</div>
					</div>
					<div class="field-group">
						<label>Description (optional)</label>
						<textarea v-model="localConfig.description" class="mc-input mc-textarea" placeholder="Context for this video"></textarea>
					</div>
				</template>

				<!-- Presentation -->
				<template v-else-if="componentType === 'Presentation'">
					<div class="field-group">
						<label>Presentation File</label>
						<div class="upload-row">
							<input v-model="localConfig.presentationUrl" type="text" class="mc-input" placeholder="URL or upload .pptx / .pdf" />
							<label class="upload-btn">
								{{ uploading ? '…' : 'Upload' }}
								<input type="file" accept=".pptx,.pdf" @change="handleFileUpload($event, 'presentationUrl')" hidden />
							</label>
						</div>
					</div>
				</template>

				<!-- Scenario -->
				<template v-else-if="componentType === 'Scenario'">
					<div class="field-group">
						<label>Training Scenario</label>
						<div v-if="loadingScenarios" class="mc-loading">Loading scenarios…</div>
						<select v-else v-model="localConfig.scenarioId" class="mc-input mc-select">
							<option value="">— Select a scenario —</option>
							<option v-for="s in availableScenarios" :key="s.name" :value="s.name">{{ s.title }}</option>
						</select>
						<p class="field-hint">Students will complete this AI-driven conversational scenario as a step in the course. After the debrief, they continue to the next node.</p>
					</div>
				</template>

				<!-- Virtual Agent -->
				<template v-else-if="componentType === 'Virtual Agent'">
					<div class="field-group">
						<label>Agent URL</label>
						<input v-model="localConfig.agentUrl" type="text" class="mc-input" placeholder="https://…" />
					</div>
					<div class="field-group">
						<label>Display Name</label>
						<input v-model="localConfig.displayName" type="text" class="mc-input" placeholder="AI Negotiation Partner" />
					</div>
					<div class="field-group">
						<label>Description (optional)</label>
						<textarea v-model="localConfig.description" class="mc-input mc-textarea" placeholder="Instructions for the student"></textarea>
					</div>
				</template>

				<!-- Task -->
				<template v-else-if="componentType === 'Task'">
					<div class="field-group">
						<label>Instructions</label>
						<textarea v-model="localConfig.instructions" class="mc-input mc-textarea mc-textarea-lg" placeholder="What should the student do?"></textarea>
					</div>
					<div class="field-group">
						<label>Completion Criteria</label>
						<input v-model="localConfig.completionCriteria" type="text" class="mc-input" placeholder="e.g. Complete the role-play exercise" />
					</div>
				</template>

				<!-- Quiz -->
				<template v-else-if="componentType === 'Quiz'">
					<div class="question-builder">
						<div
							v-for="(q, qIdx) in localConfig.questions"
							:key="qIdx"
							class="question-card"
						>
							<div class="q-header">
								<span class="q-num">Q{{ qIdx + 1 }}</span>
								<button class="remove-q-btn" @click="removeQuestion(qIdx)" title="Remove question">✕</button>
							</div>
							<div class="field-group">
								<label>Question</label>
								<input v-model="q.text" type="text" class="mc-input" placeholder="Enter question text" />
							</div>
							<div class="field-group">
								<label>Answer Options</label>
								<div v-for="(opt, oIdx) in q.options" :key="oIdx" class="option-row">
									<input
										type="radio"
										:name="`q${qIdx}-correct`"
										:value="oIdx"
										v-model="q.correct"
										title="Mark as correct answer"
									/>
									<input v-model="q.options[oIdx]" type="text" class="mc-input opt-input" :placeholder="`Option ${oIdx + 1}`" />
									<button class="remove-opt-btn" @click="removeOption(qIdx, oIdx)" title="Remove option" v-if="q.options.length > 2">✕</button>
								</div>
								<button class="add-opt-btn" @click="addOption(qIdx)" v-if="q.options.length < 6">+ Option</button>
							</div>
							<div class="correct-hint">
								<svg width="12" height="12" viewBox="0 0 12 12" fill="none">
									<circle cx="6" cy="6" r="5" stroke="#22c55e" stroke-width="1.5"/>
									<path d="M3.5 6l1.5 1.5 3-3" stroke="#22c55e" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
								</svg>
								Correct: option {{ q.correct + 1 }}
							</div>
						</div>

						<button class="add-question-btn" @click="addQuestion">+ Add Question</button>
					</div>
				</template>

				<!-- Survey -->
				<template v-else-if="componentType === 'Survey'">
					<div class="question-builder">
						<div
							v-for="(q, qIdx) in localConfig.questions"
							:key="qIdx"
							class="question-card"
						>
							<div class="q-header">
								<span class="q-num">Q{{ qIdx + 1 }}</span>
								<button class="remove-q-btn" @click="removeQuestion(qIdx)" title="Remove">✕</button>
							</div>
							<div class="field-group">
								<label>Question</label>
								<input v-model="q.text" type="text" class="mc-input" placeholder="Enter question text" />
							</div>
							<div class="field-group">
								<label>Response Type</label>
								<select v-model="q.type" class="mc-input mc-select">
									<option value="text">Free text</option>
									<option value="scale">Rating scale (1–5)</option>
									<option value="mcq">Multiple choice</option>
								</select>
							</div>
							<div v-if="q.type === 'mcq'" class="field-group">
								<label>Options</label>
								<div v-for="(opt, oIdx) in (q.options || [])" :key="oIdx" class="option-row">
									<input v-model="q.options[oIdx]" type="text" class="mc-input opt-input" :placeholder="`Option ${oIdx + 1}`" />
									<button class="remove-opt-btn" @click="removeOption(qIdx, oIdx)" v-if="(q.options || []).length > 2">✕</button>
								</div>
								<button class="add-opt-btn" @click="addOption(qIdx)">+ Option</button>
							</div>
						</div>
						<button class="add-question-btn" @click="addQuestion">+ Add Question</button>
					</div>
				</template>

				<!-- Microphone -->
				<template v-else-if="componentType === 'Microphone'">
					<div class="sensor-notice">🎤 Voice / Audio Input</div>
					<div class="field-group">
						<label>Instructions for student</label>
						<textarea v-model="localConfig.instructions" class="mc-input mc-textarea" placeholder="e.g. Record yourself presenting your argument."></textarea>
					</div>
					<div class="field-group">
						<label>Max recording length (seconds)</label>
						<input v-model.number="localConfig.maxDuration" type="number" class="mc-input" placeholder="120" min="5" max="600" />
					</div>
					<div class="field-group">
						<label>Auto-transcribe to text</label>
						<select v-model="localConfig.transcribe" class="mc-input mc-select">
							<option value="off">Off</option>
							<option value="on">On (when available)</option>
						</select>
					</div>
					<p class="sensor-hint">Full microphone runtime will be enabled in a future release. This node stores configuration for when audio capture is active.</p>
				</template>

				<!-- Camera -->
				<template v-else-if="componentType === 'Camera'">
					<div class="sensor-notice">📷 Camera / Video Input</div>
					<div class="field-group">
						<label>Instructions for student</label>
						<textarea v-model="localConfig.instructions" class="mc-input mc-textarea" placeholder="e.g. Record yourself performing the skill."></textarea>
					</div>
					<div class="field-group">
						<label>Input mode</label>
						<select v-model="localConfig.mode" class="mc-input mc-select">
							<option value="video">Video recording</option>
							<option value="photo">Single photo</option>
							<option value="live">Live webcam feed</option>
						</select>
					</div>
					<div class="field-group">
						<label>Max recording length (seconds)</label>
						<input v-model.number="localConfig.maxDuration" type="number" class="mc-input" placeholder="60" min="5" max="300" />
					</div>
					<p class="sensor-hint">Full camera runtime will be enabled in a future release. This node stores configuration for when video capture is active.</p>
				</template>

				<!-- External Sensor -->
				<template v-else-if="componentType === 'External Sensor'">
					<div class="sensor-notice">📡 External Hardware Sensor</div>
					<div class="field-group">
						<label>Sensor type</label>
						<select v-model="localConfig.sensorType" class="mc-input mc-select">
							<option value="biometric">Biometric (heart rate, GSR, etc.)</option>
							<option value="motion">Motion / IMU</option>
							<option value="vex">VEX Robotics</option>
							<option value="arduino">Arduino / microcontroller</option>
							<option value="custom">Custom / other</option>
						</select>
					</div>
					<div class="field-group">
						<label>Connection method</label>
						<select v-model="localConfig.connectionMethod" class="mc-input mc-select">
							<option value="bluetooth">Bluetooth</option>
							<option value="usb">USB / Serial</option>
							<option value="websocket">WebSocket</option>
							<option value="api">External API</option>
						</select>
					</div>
					<div v-if="localConfig.connectionMethod === 'api' || localConfig.connectionMethod === 'websocket'" class="field-group">
						<label>Endpoint URL</label>
						<input v-model="localConfig.endpointUrl" type="text" class="mc-input" placeholder="ws:// or https://" />
					</div>
					<div class="field-group">
						<label>Data fields to capture (comma-separated)</label>
						<input v-model="localConfig.dataFields" type="text" class="mc-input" placeholder="e.g. heartRate, skinConductance" />
					</div>
					<div class="field-group">
						<label>Student instructions</label>
						<textarea v-model="localConfig.instructions" class="mc-input mc-textarea" placeholder="How should the student set up and use the sensor?"></textarea>
					</div>
					<p class="sensor-hint">Full sensor integration requires the ATP sensor bridge runtime. This node stores the configuration.</p>
				</template>

				<!-- Learner Model -->
				<template v-else-if="componentType === 'Learner Model'">
					<div class="sensor-notice">🧠 Adaptive Learner Model</div>
					<div class="field-group">
						<label>Model type</label>
						<select v-model="localConfig.modelType" class="mc-input mc-select">
							<option value="bkt">Bayesian Knowledge Tracing (BKT)</option>
							<option value="irt">Item Response Theory (IRT)</option>
							<option value="pfa">Performance Factor Analysis (PFA)</option>
							<option value="custom">Custom model</option>
						</select>
					</div>
					<div class="field-group">
						<label>Competency / skill being tracked</label>
						<input v-model="localConfig.skillName" type="text" class="mc-input" placeholder="e.g. Negotiation Fundamentals" />
					</div>
					<div class="field-group">
						<label>Mastery threshold (%)</label>
						<input v-model.number="localConfig.masteryThreshold" type="number" class="mc-input" placeholder="80" min="50" max="100" />
					</div>
					<div class="field-group">
						<label>Adaptive branching</label>
						<select v-model="localConfig.adaptiveBranching" class="mc-input mc-select">
							<option value="off">Off — follow fixed path</option>
							<option value="remediation">On — offer remediation if below threshold</option>
							<option value="skip">On — skip if mastered</option>
						</select>
					</div>
					<div class="field-group">
						<label>Notes (for course designer)</label>
						<textarea v-model="localConfig.notes" class="mc-input mc-textarea" placeholder="Describe the adaptive logic intent…"></textarea>
					</div>
					<p class="sensor-hint">The learner model engine requires the ATP Pedagogical Engine backend. This node captures the configuration that will be passed to it.</p>
				</template>

				<!-- Sensors & Learner Model override — for all content nodes -->
				<template v-if="!SENSOR_NODES.includes(componentType)">
					<div class="adaptive-divider"></div>
					<div class="adaptive-toggle-row" @click="showAdaptive = !showAdaptive">
						<span class="adaptive-toggle-label">🔬 Sensors &amp; Learner Model</span>
						<span class="adaptive-toggle-caret">{{ showAdaptive ? '▲' : '▼' }}</span>
					</div>
					<div v-if="showAdaptive" class="adaptive-body">
						<div class="field-group">
							<label>Active sensors for this activity</label>
							<label class="check-row"><input type="checkbox" v-model="localConfig.sensors.timeOnTask" /><span>Time on Task</span></label>
							<label class="check-row"><input type="checkbox" v-model="localConfig.sensors.quizPerformance" /><span>Quiz Performance</span></label>
							<label class="check-row"><input type="checkbox" v-model="localConfig.sensors.microphone" /><span>Microphone Recording</span></label>
							<label class="check-row"><input type="checkbox" v-model="localConfig.sensors.camera" /><span>Camera Recording</span></label>
							<label class="check-row"><input type="checkbox" v-model="localConfig.sensors.externalSensor" /><span>External Sensor</span></label>
						</div>
						<div class="field-group">
							<label>Learner model for this activity</label>
							<select v-model="localConfig.learnerModel.type" class="mc-input mc-select">
								<option value="inherit">Inherit from course default</option>
								<option value="none">None</option>
								<option value="bkt">Bayesian Knowledge Tracing (BKT)</option>
								<option value="irt">Item Response Theory (IRT)</option>
								<option value="pfa">Performance Factor Analysis (PFA)</option>
							</select>
						</div>
						<template v-if="localConfig.learnerModel.type && localConfig.learnerModel.type !== 'inherit' && localConfig.learnerModel.type !== 'none'">
							<div class="field-group">
								<label>Skill / competency tracked</label>
								<input v-model="localConfig.learnerModel.skillName" type="text" class="mc-input" placeholder="e.g. Negotiation Fundamentals" />
							</div>
							<div class="field-group">
								<label>Mastery threshold (%)</label>
								<input v-model.number="localConfig.learnerModel.masteryThreshold" type="number" class="mc-input" placeholder="80" min="50" max="100" />
							</div>
						</template>
					</div>
				</template>
			</div>

			<!-- Footer -->
			<div class="modal-footer">
				<button @click="deleteNode" class="btn btn-danger">Delete</button>
				<div class="footer-right">
					<button @click="close" class="btn btn-secondary">Cancel</button>
					<button @click="save" class="btn btn-primary" :disabled="uploading">
						{{ uploading ? 'Uploading…' : 'Save' }}
					</button>
				</div>
			</div>
		</div>
	</div>
</template>

<style scoped>
.modal-overlay {
	position: fixed;
	inset: 0;
	background: rgba(0, 0, 0, 0.45);
	display: flex;
	align-items: center;
	justify-content: center;
	z-index: 1000;
}

.modal-container {
	background: #ffffff;
	border-radius: 8px;
	box-shadow: 0 20px 25px -5px rgba(0,0,0,0.12), 0 10px 10px -5px rgba(0,0,0,0.05);
	width: 480px;
	max-width: 96vw;
	max-height: 88vh;
	display: flex;
	flex-direction: column;
}

.modal-header {
	padding: 1rem 1.25rem;
	border-bottom: 1px solid #e5e7eb;
	display: flex;
	justify-content: space-between;
	align-items: center;
	flex-shrink: 0;
}

.modal-title {
	font-size: 1rem;
	font-weight: 700;
	color: #111827;
	margin: 0;
}

.close-btn {
	background: none;
	border: none;
	cursor: pointer;
	color: #9ca3af;
	padding: 0;
	display: flex;
}

.close-btn:hover { color: #4b5563; }

.modal-body {
	padding: 1.25rem;
	display: flex;
	flex-direction: column;
	gap: 0.85rem;
	overflow-y: auto;
	flex: 1;
}

.field-group {
	display: flex;
	flex-direction: column;
	gap: 0.3rem;
}

.field-group label {
	font-size: 0.72rem;
	font-weight: 700;
	text-transform: uppercase;
	letter-spacing: 0.04em;
	color: #6b7280;
}

.mc-input {
	width: 100%;
	border: 1px solid #d1d5db;
	border-radius: 5px;
	padding: 0.45rem 0.7rem;
	font-size: 0.875rem;
	background: #ffffff;
	color: #111827;
	box-sizing: border-box;
	transition: border-color 0.15s, box-shadow 0.15s;
}

.mc-input:focus {
	outline: none;
	border-color: #3b82f6;
	box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.12);
}

.mc-textarea {
	height: 72px;
	resize: vertical;
}

.mc-textarea-lg {
	height: 100px;
}

.mc-select {
	appearance: none;
	background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='10' height='10' viewBox='0 0 10 10'%3E%3Cpath fill='%236b7280' d='M5 7L0 2h10z'/%3E%3C/svg%3E");
	background-repeat: no-repeat;
	background-position: right 0.6rem center;
	padding-right: 2rem;
}

/* Upload row */
.upload-row {
	display: flex;
	gap: 0.5rem;
	align-items: center;
}

.upload-row .mc-input {
	flex: 1;
}

.upload-btn {
	padding: 0.4rem 0.75rem;
	background: #f3f4f6;
	border: 1px solid #e5e7eb;
	border-radius: 5px;
	font-size: 0.8rem;
	font-weight: 600;
	color: #374151;
	cursor: pointer;
	white-space: nowrap;
	transition: background 0.15s;
}

.upload-btn:hover {
	background: #e5e7eb;
}

/* Question builder */
.question-builder {
	display: flex;
	flex-direction: column;
	gap: 0.75rem;
}

.question-card {
	background: #f9fafb;
	border: 1px solid #e5e7eb;
	border-radius: 6px;
	padding: 0.75rem;
}

.q-header {
	display: flex;
	justify-content: space-between;
	align-items: center;
	margin-bottom: 0.5rem;
}

.q-num {
	font-size: 0.72rem;
	font-weight: 700;
	text-transform: uppercase;
	letter-spacing: 0.05em;
	color: #6b7280;
}

.remove-q-btn {
	background: none;
	border: none;
	color: #9ca3af;
	cursor: pointer;
	font-size: 0.85rem;
	padding: 0;
	line-height: 1;
}

.remove-q-btn:hover { color: #ef4444; }

.option-row {
	display: flex;
	align-items: center;
	gap: 0.5rem;
	margin-bottom: 0.35rem;
}

.option-row input[type="radio"] {
	accent-color: #22c55e;
	flex-shrink: 0;
	cursor: pointer;
}

.opt-input {
	flex: 1;
}

.remove-opt-btn {
	background: none;
	border: none;
	color: #d1d5db;
	cursor: pointer;
	font-size: 0.8rem;
	padding: 0;
	flex-shrink: 0;
}

.remove-opt-btn:hover { color: #ef4444; }

.add-opt-btn {
	margin-top: 0.25rem;
	background: transparent;
	border: none;
	color: #3b82f6;
	font-size: 0.78rem;
	font-weight: 600;
	cursor: pointer;
	padding: 0;
}

.add-opt-btn:hover { text-decoration: underline; }

.correct-hint {
	display: flex;
	align-items: center;
	gap: 0.3rem;
	margin-top: 0.4rem;
	font-size: 0.72rem;
	color: #22c55e;
	font-weight: 500;
}

.add-question-btn {
	padding: 0.45rem;
	background: transparent;
	border: 1px dashed #d1d5db;
	border-radius: 5px;
	color: #3b82f6;
	font-size: 0.8rem;
	font-weight: 600;
	cursor: pointer;
	transition: background 0.15s, border-color 0.15s;
	text-align: center;
}

.add-question-btn:hover {
	background: #eff6ff;
	border-color: #dbeafe;
}

/* Footer */
.modal-footer {
	padding: 0.85rem 1.25rem;
	border-top: 1px solid #e5e7eb;
	display: flex;
	justify-content: space-between;
	align-items: center;
	flex-shrink: 0;
}

.footer-right {
	display: flex;
	gap: 0.5rem;
}

.btn {
	padding: 0.4rem 0.9rem;
	border-radius: 5px;
	font-size: 0.82rem;
	font-weight: 600;
	cursor: pointer;
	border: none;
	transition: background 0.15s;
}

.btn-primary { background: #3b82f6; color: #ffffff; }
.btn-primary:hover:not(:disabled) { background: #2563eb; }
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-secondary { background: #f3f4f6; color: #374151; }
.btn-secondary:hover { background: #e5e7eb; }
.btn-danger { background: #fee2e2; color: #ef4444; }
.btn-danger:hover { background: #fecaca; }

/* Sensor / learner model nodes */
.sensor-notice {
	font-size: 0.9rem;
	font-weight: 700;
	color: #374151;
	padding: 0.5rem 0.75rem;
	background: #f0fdf4;
	border: 1px solid #bbf7d0;
	border-radius: 6px;
	margin-bottom: 0.25rem;
}

.sensor-hint {
	font-size: 0.74rem;
	color: #6b7280;
	padding: 0.5rem 0.75rem;
	background: #f9fafb;
	border: 1px solid #e5e7eb;
	border-radius: 5px;
	margin: 0;
}

/* Adaptive learning section */
.adaptive-divider {
	height: 1px;
	background: #e5e7eb;
	margin: 0.25rem 0;
}

.adaptive-toggle-row {
	display: flex;
	justify-content: space-between;
	align-items: center;
	cursor: pointer;
	padding: 0.35rem 0;
	user-select: none;
}

.adaptive-toggle-label {
	font-size: 0.78rem;
	font-weight: 700;
	color: #374151;
}

.adaptive-toggle-caret {
	font-size: 0.65rem;
	color: #9ca3af;
}

.adaptive-body {
	display: flex;
	flex-direction: column;
	gap: 0.75rem;
	padding-top: 0.25rem;
}

.check-row {
	display: flex;
	align-items: center;
	gap: 0.5rem;
	font-size: 0.82rem;
	color: #374151;
	cursor: pointer;
	padding: 0.15rem 0;
}

.check-row input[type="checkbox"] {
	accent-color: #3b82f6;
	cursor: pointer;
}

.field-hint {
	font-size: 0.75rem;
	color: #6b7280;
	margin: 0.25rem 0 0;
	line-height: 1.5;
}

.mc-loading {
	font-size: 0.82rem;
	color: #9ca3af;
	padding: 0.35rem 0;
}
</style>
