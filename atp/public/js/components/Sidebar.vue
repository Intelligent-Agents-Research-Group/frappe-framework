<script setup>
const COMPONENT_GROUPS = [
	{
		label: 'Content',
		items: [
			{ type: 'PDF',           icon: '📄', desc: 'Document' },
			{ type: 'Video',         icon: '🎬', desc: 'Media' },
			{ type: 'Presentation',  icon: '📊', desc: 'Slides' },
		],
	},
	{
		label: 'Assessment',
		items: [
			{ type: 'Quiz',   icon: '✅', desc: 'Graded quiz' },
			{ type: 'Survey', icon: '📝', desc: 'Feedback' },
			{ type: 'Task',   icon: '🎯', desc: 'Activity' },
		],
	},
	{
		label: 'AI & Agents',
		items: [
			{ type: 'Virtual Agent', icon: '🤖', desc: 'AI Agent' },
			{ type: 'Learner Model', icon: '🧠', desc: 'Adaptive' },
		],
	},
	{
		label: 'Sensors',
		items: [
			{ type: 'Microphone',       icon: '🎤', desc: 'Voice input' },
			{ type: 'Camera',           icon: '📷', desc: 'Video input' },
			{ type: 'External Sensor',  icon: '📡', desc: 'Hardware' },
		],
	},
];

const onDragStart = (event, nodeType) => {
	if (event.dataTransfer) {
		event.dataTransfer.setData('application/vueflow', nodeType);
		event.dataTransfer.effectAllowed = 'move';
	}
};

const allItems = COMPONENT_GROUPS.flatMap(g => g.items);
</script>

<template>
	<aside class="sidebar">
		<div class="sidebar-header">
			<span class="sidebar-title">Components</span>
			<span class="sidebar-hint">Drag to canvas</span>
		</div>

		<div class="node-list">
			<template v-for="group in COMPONENT_GROUPS" :key="group.label">
				<div class="node-group-label">{{ group.label }}</div>
				<div
					v-for="c in group.items"
					:key="c.type"
					class="node-item"
					:draggable="true"
					@dragstart="onDragStart($event, c.type)"
				>
					<span class="node-icon">{{ c.icon }}</span>
					<div class="node-info">
						<span class="node-type">{{ c.type }}</span>
						<span class="node-desc">{{ c.desc }}</span>
					</div>
					<span class="drag-handle">⠿</span>
				</div>
			</template>
		</div>
	</aside>
</template>

<style scoped>
.sidebar {
	width: 200px;
	background: #ffffff;
	border-right: 1px solid #e5e7eb;
	display: flex;
	flex-direction: column;
	overflow-y: auto;
	flex-shrink: 0;
}

.sidebar-header {
	padding: 0.85rem 1rem 0.5rem;
	border-bottom: 1px solid #f3f4f6;
}

.sidebar-title {
	display: block;
	font-size: 0.7rem;
	font-weight: 700;
	letter-spacing: 0.06em;
	text-transform: uppercase;
	color: #374151;
	margin-bottom: 0.4rem;
}

.sidebar-hint {
	font-size: 0.68rem;
	color: #9ca3af;
}

.node-list {
	padding: 0.5rem;
	display: flex;
	flex-direction: column;
	gap: 0.3rem;
}

.node-item {
	display: flex;
	align-items: center;
	gap: 0.5rem;
	padding: 0.45rem 0.6rem;
	border: 1px solid #e5e7eb;
	border-radius: 5px;
	background: #ffffff;
	cursor: grab;
	transition: border-color 0.15s, background 0.15s, box-shadow 0.15s;
	user-select: none;
}

.node-item:hover {
	border-color: #dbeafe;
	background: #eff6ff;
	box-shadow: 0 2px 4px rgba(0,0,0,0.06);
}

.node-item:active {
	cursor: grabbing;
}

.node-icon {
	font-size: 1.1rem;
	flex-shrink: 0;
}

.node-info {
	flex: 1;
	display: flex;
	flex-direction: column;
	gap: 0.05rem;
	min-width: 0;
}

.node-type {
	font-size: 0.78rem;
	font-weight: 600;
	color: #374151;
	line-height: 1.2;
}

.node-desc {
	font-size: 0.65rem;
	color: #9ca3af;
	line-height: 1.2;
}

.drag-handle {
	font-size: 1rem;
	color: #d1d5db;
	flex-shrink: 0;
}

.node-group-label {
	font-size: 0.62rem;
	font-weight: 700;
	text-transform: uppercase;
	letter-spacing: 0.07em;
	color: #9ca3af;
	padding: 0.5rem 0.6rem 0.2rem;
}
</style>
