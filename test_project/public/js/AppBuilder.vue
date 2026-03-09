
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

const { onConnect, addEdges, addNodes, project, toObject, fromObject, removeNodes } = useVueFlow();
const nodes = ref([]);
const edges = ref([]);

const showModal = ref(false);
const selectedNode = ref(null);
const courseName = ref('');

const props = defineProps(['courseName']);

// Function to load existing flow
const loadFlow = async () => {
    // Strategy 0: Prop passed from mount
    if (props.courseName) {
        courseName.value = props.courseName;
    }
    // Strategy 1: Window global set by entry script
    else if (window.cur_course) {
        courseName.value = window.cur_course;
    } 
    // Strategy 2: Parse URL Hash directly (Fallback)
    else {
        console.log("AppBuilder: window.cur_course missing, parsing URL...");
        const route = frappe.get_route();
        console.log("AppBuilder: Route:", route);
        
        if (route[0] === 'course_builder' && route[1]) {
            courseName.value = route[1];
            window.cur_course = route[1]; // Set it for future use
        }
        else {
             // Strategy 3: Query Params
             const params = new URLSearchParams(window.location.search);
             const queryCourse = params.get('course');
             if (queryCourse) {
                 courseName.value = queryCourse;
                 window.cur_course = queryCourse;
             }
        }
    }

    if (courseName.value) {
        console.log("AppBuilder: Loading flow for:", courseName.value);
        try {
            const doc = await frappe.db.get_doc('Course', courseName.value);
            if (doc.flow_data) {
                const flow = JSON.parse(doc.flow_data);
                if (flow) {
                    fromObject(flow);
                }
            }
        } catch (e) {
            console.error("AppBuilder: Error loading course doc", e);
            frappe.show_alert({message: `Error loading course: ${e.message}`, indicator: 'red'});
        }
    } else {
        console.warn("AppBuilder: Could not identify course.");
    }
};

onMounted(() => {
    loadFlow();
});

// Drag and Drop Logic
const onDragOver = (event) => {
    event.preventDefault();
    if (event.dataTransfer) {
        event.dataTransfer.dropEffect = 'move';
    }
};

const onDrop = (event) => {
    const type = event.dataTransfer?.getData('application/vueflow');
    if (!type) {
        console.warn("DnD: No type found in dataTransfer");
        return;
    }

    console.log("DnD: Dropped type:", type);

    // Use the wrapper div we control instead of relying on internal Vue Flow classes
    const wrapper = document.querySelector('.canvas-wrapper');
    if (!wrapper) {
        console.error("DnD: Wrapper not found");
        return;
    }

    const { left, top } = wrapper.getBoundingClientRect();
    console.log("DnD: Wrapper Rect:", left, top);
    console.log("DnD: Event Client:", event.clientX, event.clientY);

    const position = project({
        x: event.clientX - left - 40,
        y: event.clientY - top - 20,
    });
    
    console.log("DnD: Projected Position:", position);

    const newNode = {
        id: `node_${Math.random().toString(36).substr(2, 9)}`,
        type: 'default',
        label: type,
        position,
        data: { componentType: type, config: {} },
    };

    console.log("DnD: Adding Node:", newNode);
    addNodes([newNode]);
};

const onNodeClick = (event) => {
    selectedNode.value = event.node;
    showModal.value = true;
};

const onSaveNode = (node) => {
    // Node is updated by reference in modal
};

const onDeleteNode = (node) => {
    removeNodes([node.id]);
    showModal.value = false;
    selectedNode.value = null;
};

const onSaveFlow = async () => {
    // Emergency Recovery: If name is missing, try to find it one last time
    if (!courseName.value) {
        console.warn("AppBuilder: Course Name missing on save. Attempting recovery...");
        const route = frappe.get_route();
        if (route[0] === 'course_builder' && route[1]) {
            courseName.value = route[1];
        } else {
             const params = new URLSearchParams(window.location.search);
             const queryCourse = params.get('course');
             if (queryCourse) courseName.value = queryCourse;
        }
    }

    if (!courseName.value) {
        frappe.msgprint('Course not identified. Please open via Course document.');
        console.error("AppBuilder: Failed to identify course even after recovery attempt.");
        return;
    }

    const flow = toObject();
    try {
        await frappe.call({
            method: 'test_project.test_project.doctype.course.course.save_flow',
            args: {
                course_name: courseName.value,
                flow_data: JSON.stringify(flow)
            }
        });
        frappe.show_alert({ message: 'Course Saved Successfully', indicator: 'green' });
    } catch (e) {
        frappe.msgprint('Failed to save course.');
        console.error(e);
    }
};

onConnect((params) => {
    params.markerEnd = MarkerType.ArrowClosed;
    addEdges(params);
});
</script>

<template>
    <div class="builder-container">
        <div class="toolbar">
            <button @click="onSaveFlow" class="btn btn-primary">Save Course</button>
        </div>
        <div class="workspace">
            <Sidebar />
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
            </div>
        </div>
        <ConfigModal v-model="showModal" :node="selectedNode" @save="onSaveNode" @delete="onDeleteNode" />
    </div>
</template>

<style scoped>
.builder-container {
    display: flex;
    flex-direction: column;
    height: 85vh; /* Fit within Frappe page */
    background: white;
    border: 1px solid #e5e7eb;
    border-radius: 8px;
    overflow: hidden;
}

.toolbar {
    padding: 10px 20px;
    border-bottom: 1px solid #e5e7eb;
    background: #fdfdfd;
    display: flex;
    justify-content: flex-end;
}

.workspace {
    display: flex;
    flex-grow: 1;
    overflow: hidden;
}

.canvas-wrapper {
    flex-grow: 1;
    height: 100%;
    position: relative;
    background-color: #f3f4f6;
}

.btn {
    padding: 6px 16px;
    border-radius: 4px;
    cursor: pointer;
    border: none;
    font-weight: 500;
}

.btn-primary {
    background-color: #2563eb;
    color: white;
}

.btn-primary:hover {
    background-color: #1d4ed8;
}
</style>
