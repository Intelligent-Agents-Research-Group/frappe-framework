
<script setup>
import { ref, onMounted, computed } from 'vue';

const enrollmentName = ref('');
const course = ref(null);
const flow = ref(null);
const currentNodeId = ref(null);
const loading = ref(true);
const routeDebugInfo = ref([]);

const currentNode = computed(() => {
    if (!flow.value || !currentNodeId.value) return null;
    return flow.value.nodes.find(n => n.id === currentNodeId.value);
});

const nextNode = computed(() => {
    if (!flow.value || !currentNodeId.value) return null;
    const edge = flow.value.edges.find(e => e.source === currentNodeId.value);
    if (edge) {
        return flow.value.nodes.find(n => n.id === edge.target);
    }
    return null;
});

const previousNode = computed(() => {
    if (!flow.value || !currentNodeId.value) return null;
    const edge = flow.value.edges.find(e => e.target === currentNodeId.value);
    if (edge) {
        return flow.value.nodes.find(n => n.id === edge.source);
    }
    return null;
});

const props = defineProps(['enrollmentName']);

const init = async () => {
    // Strategy 0: Prop passed from mount
    if (props.enrollmentName) {
        enrollmentName.value = props.enrollmentName;
    }
    // Strategy 1: Window global
    else if (window.cur_enrollment) {
        enrollmentName.value = window.cur_enrollment;
    }
    // Strategy 2: URL Fallback
    else {
        console.log("AppPlayer: window.cur_enrollment missing, parsing URL...");
        const route = frappe.get_route();
        if (route[0] === 'course_player' && route[1]) {
            enrollmentName.value = decodeURIComponent(route[1]);
            window.cur_enrollment = enrollmentName.value;
        } else {
             const params = new URLSearchParams(window.location.search);
             const queryEnrollment = params.get('enrollment');
             if (queryEnrollment) {
                 enrollmentName.value = decodeURIComponent(queryEnrollment);
                 window.cur_enrollment = enrollmentName.value;
             }
        }
    }

    if (!enrollmentName.value) {
        loading.value = false;
        return;
    }

    try {
        const enrollment = await frappe.db.get_doc('Course Enrollment', enrollmentName.value);
        const courseDoc = await frappe.db.get_doc('Course', enrollment.course);
        course.value = courseDoc;

        if (courseDoc.flow_data) {
            flow.value = JSON.parse(courseDoc.flow_data);
            const startNodeId = findStartNode(flow.value);

            if (enrollment.progress) {
                const progress = JSON.parse(enrollment.progress);
                const savedNodeId = progress.currentNodeId;
                
                // Validate if saved node still exists (Zombie Check)
                const nodeExists = flow.value.nodes.find(n => n.id === savedNodeId);
                
                if (nodeExists) {
                    currentNodeId.value = savedNodeId;
                } else {
                    console.warn(`AppPlayer: Saved node ${savedNodeId} not found. Resetting to start.`);
                    currentNodeId.value = startNodeId;
                    updateProgress(); // Save the fix
                }
            } else {
                currentNodeId.value = startNodeId;
            }
        }
    } catch (e) {
        console.error(e);
        frappe.msgprint('Error loading course data');
    } finally {
        loading.value = false;
    }
};

const findStartNode = (flowData) => {
    if (!flowData || !flowData.nodes.length) return null;
    const targets = new Set(flowData.edges.map(e => e.target));
    const startNode = flowData.nodes.find(n => !targets.has(n.id));
    return startNode ? startNode.id : flowData.nodes[0]?.id;
};

const next = async () => {
    if (nextNode.value) {
        currentNodeId.value = nextNode.value.id;
        await updateProgress();
    } else {
        // Finish Course
        frappe.show_alert({ message: 'Course Completed! Redirecting...', indicator: 'green' });
        setTimeout(() => {
            if (enrollmentName.value) {
                frappe.set_route('Form', 'Course Enrollment', enrollmentName.value);
            } else {
                window.history.back();
            }
        }, 1000);
    }
};

const prev = async () => {
    if (previousNode.value) {
        currentNodeId.value = previousNode.value.id;
        await updateProgress();
    }
};

const getVideoEmbed = (url) => {
    if (!url) return null;
    
    // YouTube (Robust Regex)
    const ytMatch = url.match(/^.*(youtu.be\/|v\/|u\/\w\/|embed\/|watch\?v=|&v=)([^#&?]*).*/);
    if (ytMatch && ytMatch[2].length === 11) {
        const embedUrl = `https://www.youtube.com/embed/${ytMatch[2]}`;
        console.log("AppPlayer: Generated YouTube Embed:", embedUrl);
        return embedUrl;
    }
    
    // Vimeo
    const vimeoMatch = url.match(/(?:https?:\/\/)?(?:www\.)?vimeo\.com\/(.+)/);
    if (vimeoMatch && vimeoMatch[1]) {
        return `https://player.vimeo.com/video/${vimeoMatch[1]}`;
    }

    return null;
};


const updateProgress = async () => {
    try {
        await frappe.call({
            method: 'frappe.client.set_value',
            args: {
                doctype: 'Course Enrollment',
                name: enrollmentName.value,
                fieldname: 'progress',
                value: JSON.stringify({ currentNodeId: currentNodeId.value })
            }
        });
    } catch (e) {
        console.error('Failed to save progress', e);
    }
};

onMounted(() => {
    routeDebugInfo.value = frappe.get_route();
    init();
});
</script>

<template>
    <div class="player-container">
        <div v-if="loading" class="loading-state">Loading Course...</div>
        <div v-else-if="!currentNode" class="error-state">
            <p>No active step found. Please check course configuration.</p>
            <div style="margin-top: 1rem; padding: 1rem; background: #fef2f2; border: 1px solid #fecaca; border-radius: 4px; text-align: left; font-size: 0.85rem; color: #b91c1c; font-family: monospace;">
                <strong>Debug Diagnostics:</strong><br>
                Enrollment Name: "{{ enrollmentName }}"<br>
                Prop Name: "{{ $props.enrollmentName }}"<br>
                Current Node ID: {{ currentNodeId || 'null' }}<br>
                Course Loaded: {{ !!course }}<br>
                Flow Nodes: {{ flow?.nodes?.length || 0 }}<br>
                Route: {{ routeDebugInfo }}
            </div>
        </div>
        <div v-else class="course-card">
            <div class="card-header">
                <h1 class="course-title">{{ course?.title }}</h1>
                <div class="step-info">{{ currentNode.label }} ({{ currentNode.data?.componentType }})</div>
            </div>

            <div class="card-body">
                <!-- Dynamic Component Rendering -->
                <div v-if="currentNode.data?.componentType === 'PDF'" class="component-view">
                    <h3>Read this PDF</h3>
                    <div v-if="currentNode.data.config.fileUrl" class="pdf-container">
                         <iframe :src="currentNode.data.config.fileUrl" width="100%" height="600px" style="border: none;"></iframe>
                         <div class="pdf-actions">
                            <a :href="currentNode.data.config.fileUrl" target="_blank" class="link-btn small-btn">Open in New Tab</a>
                         </div>
                    </div>
                    <div v-else class="empty-state">No PDF configured.</div>
                </div>

                <div v-if="currentNode.data?.componentType === 'Video'" class="component-view">
                    <h3>Watch this Video</h3>
                     <div v-if="currentNode.data.config.videoUrl">
                         <div v-if="getVideoEmbed(currentNode.data.config.videoUrl)" class="video-wrapper">
                             <iframe 
                                :src="getVideoEmbed(currentNode.data.config.videoUrl)" 
                                frameborder="0" 
                                allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" 
                                referrerpolicy="strict-origin-when-cross-origin"
                                allowfullscreen
                             ></iframe>
                         </div>
                         <div style="text-align: right; padding: 0.5rem;">
                             <a :href="currentNode.data.config.videoUrl" target="_blank" class="link-btn small-btn">
                                {{ getVideoEmbed(currentNode.data.config.videoUrl) ? 'Open on YouTube/Vimeo' : 'Open Video File' }}
                             </a>
                         </div>
                    </div>
                    <div v-else class="empty-state">No Video configured.</div>
                </div>

                <div v-if="currentNode.data?.componentType === 'Presentation'" class="component-view">
                    <h3>Review Presentation</h3>
                    <div v-if="currentNode.data.config.presentationUrl">
                         <a :href="currentNode.data.config.presentationUrl" target="_blank" class="link-btn">Download / View Presentation</a>
                    </div>
                    <div v-else class="empty-state">No Presentation configured.</div>
                </div>

                <div v-if="currentNode.data?.componentType === 'Quiz'" class="component-view">
                    <h3>Quiz Time</h3>
                    <pre class="quiz-content">{{ currentNode.data.config.questions }}</pre>
                </div>

                <div v-if="currentNode.data?.componentType === 'Virtual Agent'" class="component-view">
                    <h3>Virtual Agent Interaction</h3>
                    <div v-if="currentNode.data.config.agentUrl" class="agent-wrapper">
                         <iframe :src="currentNode.data.config.agentUrl" width="100%" height="600px" style="border: none; border-radius: 8px;"></iframe>
                         <div style="text-align: right; padding: 0.5rem;">
                             <a :href="currentNode.data.config.agentUrl" target="_blank" class="link-btn small-btn">Open Agent in New Tab</a>
                         </div>
                    </div>
                    <div v-else class="empty-state">
                        No Agent URL configured. <br>
                        <small>Debug: {{ JSON.stringify(currentNode.data) }}</small>
                    </div>
                </div>
                 
                <div v-if="['Start', 'End', 'Task', 'Survey'].includes(currentNode.data?.componentType)" class="component-view">
                     <div class="placeholder-box">
                        {{ currentNode.data?.componentType }} Component Placeholder
                     </div>
                </div>

            </div>

            <div class="card-footer">
                <div class="step-id">Step: {{ currentNode.label }}</div>
                <div class="nav-buttons">
                    <button 
                        @click="prev"
                        :disabled="!previousNode" 
                        class="btn btn-secondary mr-2"
                    >
                        &lt; Previous
                    </button>
                    <button 
                        @click="next"
                        class="btn btn-primary"
                    >
                        {{ nextNode ? 'Next Step >' : 'Finish Course' }}
                    </button>
                </div>
            </div>
        </div>
    </div>
</template>

<style scoped>
.player-container {
    max-width: 900px;
    margin: 2rem auto;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
}

.loading-state, .error-state {
    text-align: center;
    padding: 2rem;
    font-size: 1.2rem;
}

.error-state {
    color: #ef4444;
}

.course-card {
    background: white;
    border-radius: 12px;
    box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
    overflow: hidden;
    border: 1px solid #e5e7eb;
}

.card-header {
    background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%);
    color: white;
    padding: 1.5rem 2rem;
}

.course-title {
    font-size: 1.5rem;
    font-weight: 700;
    margin: 0 0 0.5rem 0;
}

.step-info {
    font-size: 0.875rem;
    opacity: 0.9;
}

.card-body {
    padding: 2rem;
    min-height: 200px;
}

.component-view {
    text-align: center;
}

.component-view h3 {
    margin-bottom: 2rem;
    font-size: 1.25rem;
    color: #374151;
}

.link-btn {
    display: inline-block;
    padding: 0.75rem 1.5rem;
    background-color: #e0f2fe;
    color: #0369a1;
    text-decoration: none;
    border-radius: 6px;
    font-weight: 600;
    transition: background-color 0.2s;
}

.link-btn:hover {
    background-color: #bae6fd;
}

.empty-state {
    color: #9ca3af;
    font-style: italic;
}

.quiz-content {
    background: #f3f4f6;
    padding: 1rem;
    border-radius: 6px;
    text-align: left;
    white-space: pre-wrap;
    font-family: monospace;
}

.placeholder-box {
    padding: 3rem;
    border: 2px dashed #d1d5db;
    border-radius: 8px;
    color: #6b7280;
    background-color: #f9fafb;
}

.card-footer {
    background-color: #f9fafb;
    padding: 1rem 2rem;
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-top: 1px solid #e5e7eb;
}

.mr-2 {
    margin-right: 0.5rem;
}

.pdf-actions {
    margin-top: 0.5rem;
    text-align: right;
}

.small-btn {
    padding: 0.25rem 0.75rem;
    font-size: 0.75rem;
}


.video-wrapper {
    position: relative;
    padding-bottom: 56.25%; /* 16:9 */
    height: 0;
    background: #000;
    margin-bottom: 1rem;
    border-radius: 8px;
    overflow: hidden;
}

.video-wrapper iframe {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
}

.agent-wrapper {
    background: #f9fafb;
    border: 1px solid #e5e7eb;
    border-radius: 8px;
    overflow: hidden;
}

.step-id {
    font-size: 0.75rem;
    color: #6b7280;
}

.btn {
    padding: 0.5rem 1.5rem;
    border-radius: 6px;
    font-weight: 500;
    cursor: pointer;
    border: none;
    font-size: 1rem;
    transition: all 0.2s;
}

.btn-primary {
    background-color: #2563eb;
    color: white;
}

.btn-primary:hover {
    background-color: #1d4ed8;
}

.btn-primary:disabled {
    background-color: #93c5fd;
    cursor: not-allowed;
}
</style>
