
<script setup>
const onDragStart = (event, nodeType) => {
  if (event.dataTransfer) {
    event.dataTransfer.setData('application/vueflow', nodeType);
    event.dataTransfer.effectAllowed = 'move';
  }
};
</script>

<template>
  <aside class="sidebar">
    <h3 class="sidebar-title">Components</h3>
    <div class="description">Drag to canvas</div>
    
    <div class="vue-flow__node-input" :draggable="true" @dragstart="onDragStart($event, 'PDF')">
      PDF
    </div>
    <div class="vue-flow__node-default" :draggable="true" @dragstart="onDragStart($event, 'Video')">
      Video
    </div>
    <div class="vue-flow__node-output" :draggable="true" @dragstart="onDragStart($event, 'Quiz')">
      Quiz
    </div>
    <div class="vue-flow__node-default" :draggable="true" @dragstart="onDragStart($event, 'Survey')">
      Survey
    </div>
    <div class="vue-flow__node-default" :draggable="true" @dragstart="onDragStart($event, 'Task')">
      Task
    </div>
    <div class="vue-flow__node-default" :draggable="true" @dragstart="onDragStart($event, 'Presentation')">
      Presentation
    </div>
    <div class="vue-flow__node-default" :draggable="true" @dragstart="onDragStart($event, 'Virtual Agent')">
      Virtual Agent
    </div>
  </aside>
</template>

<style scoped>
.sidebar {
    width: 250px;
    background-color: #f9fafb;
    border-right: 1px solid #e5e7eb;
    padding: 1rem;
    display: flex;
    flex-direction: column;
    gap: 1rem;
    overflow-y: auto;
}

.sidebar-title {
    font-weight: 700;
    color: #374151;
    margin-bottom: 0.5rem;
    font-size: 1.1rem;
}

.description {
    font-size: 0.75rem;
    color: #6b7280;
    margin-bottom: 1rem;
}

.vue-flow__node-input, .vue-flow__node-default, .vue-flow__node-output {
    padding: 10px;
    border: 1px solid #e5e7eb;
    border-radius: 6px;
    background: white;
    cursor: grab;
    display: flex;
    justify-content: center;
    align-items: center;
    font-size: 14px;
    font-weight: 500;
    box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
    transition: all 0.2s;
}

.vue-flow__node-input:hover, .vue-flow__node-default:hover, .vue-flow__node-output:hover {
    border-color: #3b82f6;
    color: #3b82f6;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
}
</style>
