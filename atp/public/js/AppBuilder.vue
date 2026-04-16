<script setup>
import { ref, onMounted } from 'vue';
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
</style>
