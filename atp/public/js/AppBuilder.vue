<script setup>
import { ref, onMounted, computed } from 'vue';
import { VueFlow, useVueFlow, MarkerType } from '@vue-flow/core';
import { Background } from '@vue-flow/background';
import { Controls } from '@vue-flow/controls';
import { MiniMap } from '@vue-flow/minimap';
import Sidebar from './components/Sidebar.vue';
import ConfigModal from './components/ConfigModal.vue';

import '@vue-flow/core/dist/style.css';
import '@vue-flow/core/dist/theme-default.css';
import '@vue-flow/controls/dist/style.css';
import '@vue-flow/minimap/dist/style.css';

const vf = useVueFlow();
const { onConnect, addEdges, addNodes, project, toObject, fromObject, removeNodes } = vf;
const vfNodes = vf.nodes; // reactive internal node list — updates when addNodes() is called

const nodes = ref([]);
const edges = ref([]);
const showModal = ref(false);
const selectedNode = ref(null);
const courseName = ref('');
const isPublished = ref(false);
const saving = ref(false);
const previewing = ref(false);
const flowLoaded = ref(false);

// Course settings state
const showSettings = ref(false);
const settingsSaving = ref(false);
const settingsLoading = ref(false);
const prereqSearch = ref('');
const availableCourses = ref([]);

const defaultSceneConfig = () => ({
	prerequisites: [],
	sensors: { timeOnTask: true, quizPerformance: true, microphone: false, camera: false, externalSensor: false },
	learnerModel: { type: 'none', skillName: '', masteryThreshold: 80 },
});
const sceneConfig = ref(defaultSceneConfig());

const props = defineProps(['courseName']);

// ── Load ─────────────────────────────────────────────────────────────────

const loadFlow = async () => {
	if (props.courseName) courseName.value = props.courseName;
	else if (window.cur_course) courseName.value = window.cur_course;
	else {
		const route = frappe.get_route();
		if (route[0] === 'course_builder' && route[1]) {
			courseName.value = route[1];
			window.cur_course = route[1];
		} else {
			const params = new URLSearchParams(window.location.search);
			const q = params.get('course');
			if (q) { courseName.value = q; window.cur_course = q; }
		}
	}

	if (!courseName.value) return;

	try {
		const doc = await frappe.db.get_doc('Course', courseName.value);
		isPublished.value = !!doc.is_published;

		if (doc.flow_data) {
			const flow = JSON.parse(doc.flow_data);
			if (flow) fromObject(flow);
		}

		if (doc.scene_config) {
			try {
				const sc = JSON.parse(doc.scene_config);
				const defaults = defaultSceneConfig();
				sceneConfig.value = {
					prerequisites: sc.prerequisites || [],
					sensors: { ...defaults.sensors, ...(sc.sensors || {}) },
					learnerModel: { ...defaults.learnerModel, ...(sc.learnerModel || {}) },
				};
			} catch {}
		}
	} catch (e) {
		frappe.show_alert({ message: `Error loading course: ${e.message}`, indicator: 'red' });
	} finally {
		flowLoaded.value = true;
	}
};

onMounted(() => loadFlow());

// ── Drag & drop ───────────────────────────────────────────────────────────

const onDragOver = (event) => {
	event.preventDefault();
	if (event.dataTransfer) event.dataTransfer.dropEffect = 'move';
};

const onDrop = (event) => {
	const type = event.dataTransfer?.getData('application/vueflow');
	if (!type) return;

	const wrapper = document.querySelector('.canvas-wrapper');
	if (!wrapper) return;

	const { left, top } = wrapper.getBoundingClientRect();
	const position = project({ x: event.clientX - left - 40, y: event.clientY - top - 20 });

	addNodes([{
		id: `node_${Math.random().toString(36).substr(2, 9)}`,
		type: 'default',
		label: type,
		position,
		data: { componentType: type, config: {} },
	}]);
};

const onNodeClick = (event) => {
	selectedNode.value = event.node;
	showModal.value = true;
};

const onDeleteNode = (node) => {
	removeNodes([node.id]);
	showModal.value = false;
	selectedNode.value = null;
};

onConnect((params) => {
	params.markerEnd = MarkerType.ArrowClosed;
	addEdges(params);
});

// ── Save ──────────────────────────────────────────────────────────────────

const recoverCourseName = () => {
	if (courseName.value) return true;
	const route = frappe.get_route();
	if (route[0] === 'course_builder' && route[1]) { courseName.value = route[1]; return true; }
	const params = new URLSearchParams(window.location.search);
	const q = params.get('course');
	if (q) { courseName.value = q; return true; }
	return false;
};

const onSave = async () => {
	if (!recoverCourseName()) {
		frappe.msgprint('Course not identified. Please open from a Course document.');
		return;
	}

	saving.value = true;
	try {
		await frappe.call({
			method: 'atp.atp.doctype.course.course.save_flow',
			args: { course_name: courseName.value, flow_data: JSON.stringify(toObject()) },
		});
		await frappe.db.set_value('Course', courseName.value, 'is_published', isPublished.value ? 1 : 0);
		frappe.show_alert({ message: 'Course saved', indicator: 'green' });
	} catch (e) {
		frappe.msgprint('Failed to save course.');
		console.error(e);
	} finally {
		saving.value = false;
	}
};

// ── Preview ───────────────────────────────────────────────────────────────

const onPreview = async () => {
	if (!recoverCourseName()) {
		frappe.msgprint('Course not identified. Please open from a Course document.');
		return;
	}
	previewing.value = true;
	try {
		const result = await frappe.call({
			method: 'atp.atp.api.preview_course',
			args: { course_name: courseName.value },
		});
		const enrollmentName = result?.message?.name;
		if (!enrollmentName) throw new Error('No enrollment returned');
		window.open('/app/course_player/' + encodeURIComponent(enrollmentName), '_blank');
	} catch (e) {
		frappe.show_alert({ message: 'Could not open preview: ' + (e.message || 'unknown error'), indicator: 'red' });
		console.error(e);
	} finally {
		previewing.value = false;
	}
};

// ── Course Settings ───────────────────────────────────────────────────────

const openSettings = async () => {
	if (!courseName.value) {
		frappe.show_alert({ message: 'Open a course first.', indicator: 'orange' });
		return;
	}
	if (!availableCourses.value.length && !settingsLoading.value) {
		settingsLoading.value = true;
		try {
			const r = await frappe.call({ method: 'atp.atp.api.get_courses_list' });
			availableCourses.value = (r.message || []).filter((c) => c.name !== courseName.value);
		} catch {
			frappe.show_alert({ message: 'Could not load course list.', indicator: 'red' });
		} finally {
			settingsLoading.value = false;
		}
	}
	prereqSearch.value = '';
	showSettings.value = true;
};

const saveSettings = async () => {
	if (!recoverCourseName()) return;
	settingsSaving.value = true;
	try {
		await frappe.call({
			method: 'atp.atp.doctype.course.course.save_config',
			args: { course_name: courseName.value, scene_config: JSON.stringify(sceneConfig.value) },
		});
		frappe.show_alert({ message: 'Course settings saved', indicator: 'green' });
		showSettings.value = false;
	} catch {
		frappe.show_alert({ message: 'Failed to save settings.', indicator: 'red' });
	} finally {
		settingsSaving.value = false;
	}
};

const togglePrereq = (cname) => {
	const idx = sceneConfig.value.prerequisites.indexOf(cname);
	if (idx >= 0) sceneConfig.value.prerequisites.splice(idx, 1);
	else sceneConfig.value.prerequisites.push(cname);
};

const isPrereq = (cname) => sceneConfig.value.prerequisites.includes(cname);

const filteredCourses = computed(() => {
	const q = prereqSearch.value.toLowerCase().trim();
	if (!q) return availableCourses.value;
	return availableCourses.value.filter((c) => c.title.toLowerCase().includes(q));
});
</script>

<template>
	<div class="builder-root">
		<!-- Toolbar -->
		<div class="builder-toolbar">
			<div class="toolbar-left">
				<span class="course-name-label" v-if="courseName">{{ courseName }}</span>
			</div>
			<div class="toolbar-right">
				<label class="publish-toggle">
					<input type="checkbox" v-model="isPublished" />
					<span>{{ isPublished ? 'Published' : 'Draft' }}</span>
				</label>
				<button @click="openSettings" class="settings-btn" :disabled="!courseName">
					⚙ Settings
				</button>
				<button @click="onPreview" class="preview-btn" :disabled="previewing || !courseName">
					{{ previewing ? 'Opening…' : 'Preview ↗' }}
				</button>
				<button @click="onSave" class="save-btn" :disabled="saving">
					{{ saving ? 'Saving…' : 'Save' }}
				</button>
			</div>
		</div>

		<div class="builder-workspace">
			<!-- Left: component palette -->
			<Sidebar />

			<!-- Canvas -->
			<div class="canvas-wrapper" @drop="onDrop" @dragover="onDragOver">
				<VueFlow
					:nodes="nodes"
					:edges="edges"
					@node-click="onNodeClick"
					fit-view-on-init
				>
					<Background />
					<Controls />
					<MiniMap />
				</VueFlow>
				<div v-if="flowLoaded && vfNodes.length === 0" class="canvas-empty-hint">
					<div class="canvas-empty-icon">🧩</div>
					<p class="canvas-empty-title">Start building your course</p>
					<p class="canvas-empty-sub">Drag a component from the left panel onto the canvas.</p>
				</div>
			</div>
		</div>

		<ConfigModal
			v-model="showModal"
			:node="selectedNode"
			@save="() => {}"
			@delete="onDeleteNode"
		/>

		<!-- Course Settings Modal -->
		<div v-if="showSettings" class="cs-overlay" @click.self="showSettings = false">
			<div class="cs-modal">
				<div class="cs-header">
					<span class="cs-title">Course Settings</span>
					<button class="cs-close" @click="showSettings = false">✕</button>
				</div>
				<div class="cs-body">

					<!-- Prerequisites -->
					<div class="cs-section">
						<div class="cs-section-label">Prerequisites</div>
						<p class="cs-section-hint">Students must complete all checked courses before accessing this one.</p>
						<div v-if="settingsLoading" class="cs-loading">Loading courses…</div>
						<template v-else>
							<input v-model="prereqSearch" type="search" class="cs-search" placeholder="Filter courses…" />
							<div v-if="filteredCourses.length === 0" class="cs-empty">No other courses available.</div>
							<div v-else class="cs-course-list">
								<label v-for="c in filteredCourses" :key="c.name" class="cs-course-row">
									<input type="checkbox" :checked="isPrereq(c.name)" @change="togglePrereq(c.name)" />
									<span class="cs-course-title">{{ c.title }}</span>
									<span v-if="!c.is_published" class="cs-draft-badge">Draft</span>
								</label>
							</div>
						</template>
					</div>

					<!-- Default Sensors -->
					<div class="cs-section">
						<div class="cs-section-label">Default Sensors</div>
						<p class="cs-section-hint">Applied to all activities unless overridden per-node.</p>
						<label class="cs-check-row"><input type="checkbox" v-model="sceneConfig.sensors.timeOnTask" /><span>Time on Task</span></label>
						<label class="cs-check-row"><input type="checkbox" v-model="sceneConfig.sensors.quizPerformance" /><span>Quiz Performance</span></label>
						<label class="cs-check-row"><input type="checkbox" v-model="sceneConfig.sensors.microphone" /><span>Microphone Recording</span></label>
						<label class="cs-check-row"><input type="checkbox" v-model="sceneConfig.sensors.camera" /><span>Camera Recording</span></label>
						<label class="cs-check-row"><input type="checkbox" v-model="sceneConfig.sensors.externalSensor" /><span>External Sensor</span></label>
					</div>

					<!-- Default Learner Model -->
					<div class="cs-section">
						<div class="cs-section-label">Default Learner Model</div>
						<p class="cs-section-hint">Adaptive algorithm applied across the course by default.</p>
						<select v-model="sceneConfig.learnerModel.type" class="cs-select">
							<option value="none">None — simple progress tracking</option>
							<option value="bkt">Bayesian Knowledge Tracing (BKT)</option>
							<option value="irt">Item Response Theory (IRT)</option>
							<option value="pfa">Performance Factor Analysis (PFA)</option>
						</select>
						<template v-if="sceneConfig.learnerModel.type && sceneConfig.learnerModel.type !== 'none'">
							<input v-model="sceneConfig.learnerModel.skillName" type="text" class="cs-input" style="margin-top:0.5rem" placeholder="Skill / competency name" />
							<div style="display:flex;align-items:center;gap:0.5rem;margin-top:0.5rem">
								<span style="font-size:0.78rem;color:#6b7280;white-space:nowrap">Mastery threshold:</span>
								<input v-model.number="sceneConfig.learnerModel.masteryThreshold" type="number" class="cs-input" style="width:80px" min="50" max="100" placeholder="80" />
								<span style="font-size:0.78rem;color:#6b7280">%</span>
							</div>
						</template>
					</div>

				</div>
				<div class="cs-footer">
					<button class="cs-btn cs-btn-outline" @click="showSettings = false">Cancel</button>
					<button class="cs-btn cs-btn-primary" @click="saveSettings" :disabled="settingsSaving">
						{{ settingsSaving ? 'Saving…' : 'Save Settings' }}
					</button>
				</div>
			</div>
		</div>
	</div>
</template>

<style scoped>
.builder-root {
	display: flex;
	flex-direction: column;
	height: 85vh;
	background: #ffffff;
	border: 1px solid #e5e7eb;
	border-radius: 8px;
	overflow: hidden;
	font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
}

/* Toolbar */
.builder-toolbar {
	display: flex;
	align-items: center;
	justify-content: space-between;
	padding: 0 1rem;
	height: 46px;
	border-bottom: 1px solid #e5e7eb;
	background: #fafafa;
	flex-shrink: 0;
}

.toolbar-left {
	display: flex;
	align-items: center;
	gap: 0.75rem;
}

.toolbar-right {
	display: flex;
	align-items: center;
	gap: 0.75rem;
}

.course-name-label {
	font-size: 0.82rem;
	font-weight: 600;
	color: #374151;
}

.publish-toggle {
	display: flex;
	align-items: center;
	gap: 0.4rem;
	font-size: 0.8rem;
	font-weight: 600;
	color: #6b7280;
	cursor: pointer;
	user-select: none;
}

.publish-toggle input[type="checkbox"] {
	accent-color: #3b82f6;
}

.settings-btn {
	padding: 0.35rem 0.85rem;
	background: transparent;
	color: #6b7280;
	border: 1px solid #e5e7eb;
	border-radius: 5px;
	font-size: 0.82rem;
	font-weight: 600;
	cursor: pointer;
	transition: background 0.15s, border-color 0.15s;
}

.settings-btn:hover:not(:disabled) {
	background: #f3f4f6;
	border-color: #d1d5db;
}

.settings-btn:disabled {
	opacity: 0.5;
	cursor: not-allowed;
}

.preview-btn {
	padding: 0.35rem 1rem;
	background: transparent;
	color: #3b82f6;
	border: 1px solid #bfdbfe;
	border-radius: 5px;
	font-size: 0.82rem;
	font-weight: 600;
	cursor: pointer;
	transition: background 0.15s, border-color 0.15s;
}

.preview-btn:hover:not(:disabled) {
	background: #eff6ff;
	border-color: #93c5fd;
}

.preview-btn:disabled {
	opacity: 0.5;
	cursor: not-allowed;
}

.save-btn {
	padding: 0.35rem 1rem;
	background: #3b82f6;
	color: #ffffff;
	border: none;
	border-radius: 5px;
	font-size: 0.82rem;
	font-weight: 600;
	cursor: pointer;
	transition: background 0.15s;
}

.save-btn:hover:not(:disabled) {
	background: #2563eb;
}

.save-btn:disabled {
	opacity: 0.6;
	cursor: not-allowed;
}

/* Workspace */
.builder-workspace {
	display: flex;
	flex: 1;
	overflow: hidden;
}

/* Canvas */
.canvas-wrapper {
	flex: 1;
	height: 100%;
	position: relative;
	background: #f3f4f6;
}

.canvas-empty-hint {
	position: absolute;
	inset: 0;
	display: flex;
	flex-direction: column;
	align-items: center;
	justify-content: center;
	pointer-events: none;
	user-select: none;
}

.canvas-empty-icon {
	font-size: 2.5rem;
	margin-bottom: 0.75rem;
	opacity: 0.5;
}

.canvas-empty-title {
	font-size: 0.95rem;
	font-weight: 600;
	color: #6b7280;
	margin: 0 0 0.35rem 0;
}

.canvas-empty-sub {
	font-size: 0.8rem;
	color: #9ca3af;
	margin: 0;
}

/* Course Settings Modal */
.cs-overlay {
	position: fixed;
	inset: 0;
	background: rgba(0,0,0,0.45);
	display: flex;
	align-items: center;
	justify-content: center;
	z-index: 1000;
}

.cs-modal {
	background: #ffffff;
	border-radius: 8px;
	box-shadow: 0 20px 25px -5px rgba(0,0,0,0.12), 0 10px 10px -5px rgba(0,0,0,0.05);
	width: 480px;
	max-width: 96vw;
	max-height: 88vh;
	display: flex;
	flex-direction: column;
}

.cs-header {
	padding: 1rem 1.25rem;
	border-bottom: 1px solid #e5e7eb;
	display: flex;
	justify-content: space-between;
	align-items: center;
	flex-shrink: 0;
}

.cs-title {
	font-size: 1rem;
	font-weight: 700;
	color: #111827;
}

.cs-close {
	background: none;
	border: none;
	cursor: pointer;
	color: #9ca3af;
	font-size: 1rem;
	padding: 0;
	display: flex;
	align-items: center;
}

.cs-close:hover { color: #4b5563; }

.cs-body {
	padding: 1.25rem;
	overflow-y: auto;
	flex: 1;
	display: flex;
	flex-direction: column;
	gap: 1.25rem;
}

.cs-section {
	display: flex;
	flex-direction: column;
	gap: 0.45rem;
}

.cs-section-label {
	font-size: 0.72rem;
	font-weight: 700;
	text-transform: uppercase;
	letter-spacing: 0.04em;
	color: #374151;
}

.cs-section-hint {
	font-size: 0.78rem;
	color: #6b7280;
	margin: 0 0 0.25rem;
}

.cs-loading {
	font-size: 0.82rem;
	color: #9ca3af;
	padding: 0.5rem 0;
}

.cs-empty {
	font-size: 0.82rem;
	color: #9ca3af;
	font-style: italic;
}

.cs-search {
	width: 100%;
	padding: 0.4rem 0.7rem;
	border: 1px solid #d1d5db;
	border-radius: 5px;
	font-size: 0.875rem;
	background: #ffffff;
	box-sizing: border-box;
	margin-bottom: 0.4rem;
}

.cs-search:focus {
	outline: none;
	border-color: #3b82f6;
	box-shadow: 0 0 0 3px rgba(59,130,246,0.12);
}

.cs-course-list {
	max-height: 160px;
	overflow-y: auto;
	border: 1px solid #e5e7eb;
	border-radius: 5px;
	padding: 0.25rem 0;
}

.cs-course-row {
	display: flex;
	align-items: center;
	gap: 0.5rem;
	padding: 0.4rem 0.75rem;
	cursor: pointer;
	font-size: 0.82rem;
	color: #374151;
	transition: background 0.1s;
}

.cs-course-row:hover { background: #f9fafb; }

.cs-course-row input[type="checkbox"] {
	accent-color: #3b82f6;
	cursor: pointer;
	flex-shrink: 0;
}

.cs-course-title {
	flex: 1;
}

.cs-draft-badge {
	font-size: 0.65rem;
	font-weight: 600;
	color: #9ca3af;
	background: #f3f4f6;
	border-radius: 3px;
	padding: 0.1rem 0.35rem;
}

.cs-check-row {
	display: flex;
	align-items: center;
	gap: 0.5rem;
	font-size: 0.82rem;
	color: #374151;
	cursor: pointer;
	padding: 0.15rem 0;
}

.cs-check-row input[type="checkbox"] {
	accent-color: #3b82f6;
	cursor: pointer;
}

.cs-select {
	width: 100%;
	padding: 0.4rem 0.7rem;
	border: 1px solid #d1d5db;
	border-radius: 5px;
	font-size: 0.875rem;
	background: #ffffff;
	box-sizing: border-box;
	appearance: none;
	background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='10' height='10' viewBox='0 0 10 10'%3E%3Cpath fill='%236b7280' d='M5 7L0 2h10z'/%3E%3C/svg%3E");
	background-repeat: no-repeat;
	background-position: right 0.6rem center;
	padding-right: 2rem;
}

.cs-select:focus {
	outline: none;
	border-color: #3b82f6;
	box-shadow: 0 0 0 3px rgba(59,130,246,0.12);
}

.cs-input {
	width: 100%;
	padding: 0.4rem 0.7rem;
	border: 1px solid #d1d5db;
	border-radius: 5px;
	font-size: 0.875rem;
	background: #ffffff;
	box-sizing: border-box;
}

.cs-input:focus {
	outline: none;
	border-color: #3b82f6;
	box-shadow: 0 0 0 3px rgba(59,130,246,0.12);
}

.cs-footer {
	padding: 0.85rem 1.25rem;
	border-top: 1px solid #e5e7eb;
	display: flex;
	justify-content: flex-end;
	gap: 0.5rem;
	flex-shrink: 0;
}

.cs-btn {
	padding: 0.4rem 0.9rem;
	border-radius: 5px;
	font-size: 0.82rem;
	font-weight: 600;
	cursor: pointer;
	border: none;
	transition: background 0.15s;
}

.cs-btn-primary { background: #3b82f6; color: #ffffff; }
.cs-btn-primary:hover:not(:disabled) { background: #2563eb; }
.cs-btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
.cs-btn-outline { background: #f3f4f6; color: #374151; border: 1px solid #e5e7eb; }
.cs-btn-outline:hover { background: #e5e7eb; }
</style>
