
<script setup>
import { ref, watch, computed } from 'vue';

const props = defineProps({
  modelValue: Boolean,
  node: Object,
});

const emit = defineEmits(['update:modelValue', 'save', 'delete']);

const localConfig = ref({});
const uploading = ref(false);

watch(() => props.node, (newNode) => {
  if (newNode) {
    localConfig.value = { ...newNode.data.config, label: newNode.label };
  }
}, { immediate: true });

const save = () => {
    if (props.node) {
        props.node.label = localConfig.value.label;
        props.node.data.config = { ...localConfig.value };
        emit('save', props.node);
    }
    emit('update:modelValue', false);
};

const deleteNode = () => {
    if (confirm('Are you sure you want to delete this component?')) {
        emit('delete', props.node);
    }
};

const close = () => {
  emit('update:modelValue', false);
};

const handleFileUpload = (event, field) => {
    const file = event.target.files[0];
    if (!file) return;

    uploading.value = true;
    
    let formData = new FormData();
    formData.append('file', file, file.name);
    formData.append('is_private', 0);
    formData.append('folder', 'Home');

    fetch('/api/method/upload_file', {
        method: 'POST',
        headers: {
            'X-Frappe-CSRF-Token': frappe.csrf_token
        },
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        uploading.value = false;
        if (data.message && data.message.file_url) {
            localConfig.value[field] = data.message.file_url;
            frappe.show_alert({message: 'File uploaded', indicator: 'green'});
        } else {
            console.error('Upload failed', data);
            frappe.msgprint('Upload failed: ' + (data.exc || 'Unknown error'));
        }
    })
    .catch(error => {
        uploading.value = false;
        console.error('Upload Error', error);
        frappe.msgprint('Upload failed');
    });
};
</script>

<template>
  <div v-if="modelValue" class="modal-overlay">
    <div class="modal-container">
      <div class="modal-header">
        <h3 class="modal-title">Configure {{ node?.data?.componentType }}</h3>
        <button @click="close" class="close-btn">
          <svg class="icon" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>
      
      <div class="modal-body">
        <div class="form-group">
            <label>Label</label>
            <input v-model="localConfig.label" type="text" class="form-control">
        </div>

        <div v-if="node?.data?.componentType === 'PDF'" class="form-group">
            <label>File URL</label>
            <div class="input-group">
                 <input v-model="localConfig.fileUrl" type="text" class="form-control" placeholder="Upload or paste URL">
                 <input type="file" @change="handleFileUpload($event, 'fileUrl')" accept=".pdf" class="file-control">
            </div>
        </div>

        <div v-if="node?.data?.componentType === 'Video'" class="form-group">
            <label>Video Source</label>
             <div class="input-group">
                <input v-model="localConfig.videoUrl" type="text" class="form-control" placeholder="YouTube or File URL">
                <input type="file" @change="handleFileUpload($event, 'videoUrl')" accept="video/*" class="file-control">
             </div>
        </div>

        <div v-if="node?.data?.componentType === 'Presentation'" class="form-group">
            <label>Presentation File</label>
             <div class="input-group">
                <input v-model="localConfig.presentationUrl" type="text" class="form-control" placeholder="File URL">
                <input type="file" @change="handleFileUpload($event, 'presentationUrl')" accept=".pptx,.pdf" class="file-control">
             </div>
        </div>

        <div v-if="node?.data?.componentType === 'Quiz'" class="form-group">
            <label>Questions (JSON)</label>
            <textarea v-model="localConfig.questions" class="form-control is-textarea" placeholder='[{"q": "...", "a": ["..."]}]'></textarea>
        </div>

        <div v-if="node?.data?.componentType === 'Virtual Agent'" class="form-group">
            <label>Agent URL</label>
            <input v-model="localConfig.agentUrl" type="text" class="form-control" placeholder="https://...">
        </div>
      </div>

      <div class="modal-footer">
        <button @click="deleteNode" class="btn btn-danger mr-auto">Delete</button>
        <button @click="close" class="btn btn-secondary">Cancel</button>
        <button @click="save" class="btn btn-primary" :disabled="uploading">{{ uploading ? 'Uploading...' : 'Save' }}</button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.modal-overlay {
    position: fixed;
    inset: 0;
    background-color: rgba(0, 0, 0, 0.5);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 1000;
}

.modal-container {
    background: white;
    border-radius: 8px;
    box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
    width: 400px;
    max-width: 95%;
    display: flex;
    flex-direction: column;
}

.modal-header {
    padding: 1rem 1.5rem;
    border-bottom: 1px solid #e5e7eb;
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.modal-title {
    font-size: 1.125rem;
    font-weight: 600;
    color: #111827;
    margin: 0;
}

.close-btn {
    background: none;
    border: none;
    cursor: pointer;
    color: #9ca3af;
    padding: 0;
}

.close-btn:hover {
    color: #4b5563;
}

.icon {
    height: 1.5rem;
    width: 1.5rem;
}

.modal-body {
    padding: 1.5rem;
    display: flex;
    flex-direction: column;
    gap: 1rem;
}

.form-group {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
}

.form-group label {
    font-size: 0.875rem;
    font-weight: 500;
    color: #374151;
}

.form-control {
    width: 100%;
    border: 1px solid #cae3fc; /* Frappe default border colorish */
    border-radius: 4px;
    padding: 0.5rem 0.75rem;
    font-size: 0.875rem;
    background-color: #f6f8f8;
}

.form-control:focus {
    outline: none;
    border-color: #3b82f6;
    box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.2);
    background-color: #fff;
}

.is-textarea {
    height: 6rem;
    resize: vertical;
}

.modal-footer {
    padding: 1rem 1.5rem;
    border-top: 1px solid #e5e7eb;
    display: flex;
    justify-content: flex-end;
    gap: 0.75rem;
}

.btn {
    padding: 0.5rem 1rem;
    border-radius: 4px;
    font-weight: 500;
    cursor: pointer;
    border: none;
    font-size: 0.875rem;
}

.btn-secondary {
    background-color: #f3f4f6;
    color: #374151;
}

.btn-secondary:hover {
    background-color: #e5e7eb;
}

.btn-primary {
    background-color: #2563eb;
    color: white;
}

.btn-primary:hover {
    background-color: #1d4ed8;
}
</style>
