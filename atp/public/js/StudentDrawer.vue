<script setup>
import { ref, watch } from 'vue';

const props = defineProps({
	student: { type: Object, default: null },
	show: { type: Boolean, default: false },
});

const emit = defineEmits(['close', 'access-toggled']);

const enrollments = ref([]);
const loadingEnrollments = ref(false);
const showPasswordReset = ref(false);
const generatedPassword = ref('');
const passwordCopied = ref(false);
const applyingReset = ref(false);
const passwordApplied = ref(false);
const togglingAccess = ref(false);
const credCopied = ref(false);

const getInitials = (name) => {
	if (!name) return 'U';
	return name.split(' ').map(w => w[0]).join('').toUpperCase().slice(0, 2);
};

function generatePassword() {
	const chars = 'ABCDEFGHJKLMNPQRSTUVWXYZabcdefghjkmnpqrstuvwxyz23456789!@#$';
	return Array.from(crypto.getRandomValues(new Uint8Array(12)))
		.map(b => chars[b % chars.length])
		.join('');
}

const loadEnrollments = async (email) => {
	if (!email) return;
	loadingEnrollments.value = true;
	enrollments.value = [];
	try {
		const res = await frappe.call({
			method: 'atp.atp.api.get_student_enrollments',
			args: { student_email: email },
		});
		enrollments.value = res.message || [];
	} catch (e) {
		console.error('StudentDrawer: load error', e);
	} finally {
		loadingEnrollments.value = false;
	}
};

watch(() => props.student, (s) => {
	if (s) {
		loadEnrollments(s.email);
		showPasswordReset.value = false;
		generatedPassword.value = '';
		passwordCopied.value = false;
		passwordApplied.value = false;
		credCopied.value = false;
	}
}, { immediate: true });

const openPasswordReset = () => {
	showPasswordReset.value = true;
	passwordApplied.value = false;
	passwordCopied.value = false;
	generatedPassword.value = generatePassword();
};

const cancelPasswordReset = () => {
	showPasswordReset.value = false;
	generatedPassword.value = '';
	passwordCopied.value = false;
};

const regeneratePassword = () => {
	generatedPassword.value = generatePassword();
	passwordCopied.value = false;
};

const copyGeneratedPassword = async () => {
	await navigator.clipboard.writeText(generatedPassword.value);
	passwordCopied.value = true;
	setTimeout(() => { passwordCopied.value = false; }, 2000);
};

const applyPasswordReset = async () => {
	applyingReset.value = true;
	try {
		await frappe.call({
			method: 'atp.atp.api.reset_student_password',
			args: { student_email: props.student.email, new_password: generatedPassword.value },
		});
		passwordApplied.value = true;
		frappe.show_alert({ message: "Password reset. Copy it now — it won't be shown again.", indicator: 'green' }, 6);
	} catch (e) {
		frappe.show_alert({ message: e?.message || 'Failed to reset password.', indicator: 'red' }, 5);
	} finally {
		applyingReset.value = false;
	}
};

const toggleAccess = async () => {
	if (!props.student) return;
	togglingAccess.value = true;
	const newEnabled = props.student.enabled ? 0 : 1;
	try {
		await frappe.call({
			method: 'atp.atp.api.toggle_student_access',
			args: { student_email: props.student.email, enabled: newEnabled },
		});
		emit('access-toggled', { ...props.student, enabled: newEnabled });
		frappe.show_alert({
			message: `${props.student.full_name || props.student.email} ${newEnabled ? 'enabled' : 'disabled'}.`,
			indicator: newEnabled ? 'green' : 'orange',
		}, 2);
	} catch (e) {
		frappe.show_alert({ message: e?.message || 'Failed to update access.', indicator: 'red' }, 5);
	} finally {
		togglingAccess.value = false;
	}
};

const copyLoginCredentials = async () => {
	const s = props.student;
	const text = `ATP Login Details\nName: ${s.full_name || ''}\nEmail: ${s.email}\nLogin at: ${window.location.origin}/app/login`;
	await navigator.clipboard.writeText(text);
	credCopied.value = true;
	setTimeout(() => { credCopied.value = false; }, 2000);
};

const getStatusBadgeClass = (status, progressPct) => {
	if (status === 'Completed') return 'sd-badge-completed';
	if (progressPct > 0) return 'sd-badge-inprogress';
	return 'sd-badge-notstarted';
};

const getStatusLabel = (status, progressPct) => {
	if (status === 'Completed') return 'Completed';
	if (progressPct > 0) return 'In Progress';
	return 'Not Started';
};

const savingSeq = ref({});

const saveSequence = async (enrollment) => {
	savingSeq.value[enrollment.name] = true;
	try {
		await frappe.call({
			method: 'atp.atp.api.set_enrollment_sequence',
			args: { enrollment_name: enrollment.name, sequence_order: enrollment.sequence_order },
		});
	} catch (e) {
		frappe.show_alert({ message: e?.message || 'Failed to save order.', indicator: 'red' }, 3);
	} finally {
		savingSeq.value[enrollment.name] = false;
	}
};
</script>

<template>
	<Teleport to="body">
		<div v-if="show" class="sd-backdrop" @click="emit('close')" />

		<div class="sd-drawer" :class="{ open: show }">
			<template v-if="student">
				<!-- Header -->
				<div class="sd-header">
					<div class="sd-avatar">{{ getInitials(student.full_name) }}</div>
					<div class="sd-header-info">
						<div class="sd-name">{{ student.full_name || student.email }}</div>
						<div class="sd-email">{{ student.email }}</div>
					</div>
					<button class="sd-close" @click="emit('close')">&times;</button>
				</div>

				<!-- Status -->
				<div class="sd-section">
					<div class="sd-section-row">
						<span :class="['sd-badge', student.enabled ? 'sd-badge-active' : 'sd-badge-disabled']">
							{{ student.enabled ? '● Active' : '○ Disabled' }}
						</span>
						<button
							class="sd-action-btn"
							:class="student.enabled ? 'sd-action-disable' : 'sd-action-enable'"
							:disabled="togglingAccess"
							@click="toggleAccess"
						>{{ togglingAccess ? '…' : (student.enabled ? 'Disable' : 'Enable') }}</button>
					</div>
				</div>

				<!-- Courses -->
				<div class="sd-section">
					<div class="sd-section-label">Courses</div>
					<div v-if="loadingEnrollments" class="sd-loading">Loading…</div>
					<div v-else-if="enrollments.length === 0" class="sd-empty">Not enrolled in any courses yet.</div>
					<div v-else class="sd-course-list">
						<div v-for="e in enrollments" :key="e.name" class="sd-course-item">
							<div class="sd-course-header">
								<div class="sd-course-title">{{ e.course_title }}</div>
								<div class="sd-seq-control" title="Step order (0 = unordered)">
									<span class="sd-seq-label">#</span>
									<input
										v-model.number="e.sequence_order"
										type="number"
										min="0"
										max="99"
										class="sd-seq-input"
										@change="saveSequence(e)"
										:disabled="savingSeq[e.name]"
									/>
								</div>
							</div>
							<div class="sd-course-meta">
								<span :class="['sd-badge', getStatusBadgeClass(e.status, e.progress_pct)]">
									{{ getStatusLabel(e.status, e.progress_pct) }}
								</span>
								<span class="sd-progress-pct">{{ e.progress_pct }}%</span>
							</div>
							<div class="sd-progress-bar">
								<div class="sd-progress-fill" :style="{ width: e.progress_pct + '%' }" />
							</div>
						</div>
					</div>
				</div>

				<!-- Credentials -->
				<div class="sd-section">
					<div class="sd-section-label">Credentials</div>
					<div class="sd-cred-actions">
						<button
							class="sd-action-btn sd-action-copy"
							:class="{ copied: credCopied }"
							@click="copyLoginCredentials"
						>{{ credCopied ? '✓ Copied' : 'Copy Login Credentials' }}</button>
						<button
							v-if="!showPasswordReset"
							class="sd-action-btn"
							@click="openPasswordReset"
						>Reset Password</button>
					</div>

					<div v-if="showPasswordReset" class="sd-reset-section">
						<div class="sd-reset-label">Generated password:</div>
						<div class="sd-reset-row">
							<input class="sd-reset-input" type="text" :value="generatedPassword" readonly />
							<button
								class="sd-action-btn sd-action-copy"
								:class="{ copied: passwordCopied }"
								@click="copyGeneratedPassword"
							>{{ passwordCopied ? '✓' : '📋' }}</button>
						</div>
						<div v-if="passwordApplied" class="sd-reset-applied">
							Password applied. Share it with the student now.
						</div>
						<div class="sd-reset-buttons">
							<button class="sd-action-btn" :disabled="applyingReset" @click="regeneratePassword">Regenerate</button>
							<button class="sd-action-btn" :disabled="applyingReset" @click="cancelPasswordReset">Cancel</button>
							<button
								class="sd-action-btn sd-action-primary"
								:disabled="applyingReset || passwordApplied"
								@click="applyPasswordReset"
							>{{ applyingReset ? 'Applying…' : (passwordApplied ? 'Applied ✓' : 'Apply') }}</button>
						</div>
					</div>
				</div>
			</template>
		</div>
	</Teleport>
</template>

<style scoped>
.sd-backdrop {
	position: fixed;
	inset: 0;
	background: rgba(0, 0, 0, 0.3);
	z-index: 8000;
}

.sd-drawer {
	position: fixed;
	top: 0;
	right: 0;
	height: 100%;
	width: 380px;
	max-width: 95vw;
	background: #ffffff;
	border-left: 1px solid #e5e7eb;
	box-shadow: -4px 0 24px rgba(0, 0, 0, 0.1);
	z-index: 8001;
	display: flex;
	flex-direction: column;
	overflow-y: auto;
	transform: translateX(100%);
	transition: transform 0.25s ease;
}

.sd-drawer.open {
	transform: translateX(0);
}

.sd-header {
	display: flex;
	align-items: center;
	gap: 0.75rem;
	padding: 1rem 1.25rem;
	border-bottom: 1px solid #e5e7eb;
	flex-shrink: 0;
}

.sd-avatar {
	width: 44px;
	height: 44px;
	border-radius: 50%;
	background: #e5e7eb;
	display: flex;
	align-items: center;
	justify-content: center;
	font-size: 1rem;
	font-weight: 700;
	color: #4b5563;
	flex-shrink: 0;
}

.sd-header-info {
	flex: 1;
	min-width: 0;
}

.sd-name {
	font-size: 0.92rem;
	font-weight: 700;
	color: #111827;
	white-space: nowrap;
	overflow: hidden;
	text-overflow: ellipsis;
}

.sd-email {
	font-size: 0.75rem;
	color: #6b7280;
	white-space: nowrap;
	overflow: hidden;
	text-overflow: ellipsis;
}

.sd-close {
	background: none;
	border: none;
	font-size: 1.3rem;
	cursor: pointer;
	color: #9ca3af;
	line-height: 1;
	padding: 0;
	flex-shrink: 0;
}

.sd-close:hover { color: #374151; }

.sd-section {
	padding: 1rem 1.25rem;
	border-bottom: 1px solid #f3f4f6;
}

.sd-section:last-child { border-bottom: none; }

.sd-section-label {
	font-size: 0.65rem;
	font-weight: 700;
	letter-spacing: 0.07em;
	text-transform: uppercase;
	color: #9ca3af;
	margin-bottom: 0.6rem;
}

.sd-section-row {
	display: flex;
	align-items: center;
	gap: 0.75rem;
}

.sd-badge {
	display: inline-block;
	padding: 0.2rem 0.6rem;
	border-radius: 999px;
	font-size: 0.72rem;
	font-weight: 600;
}

.sd-badge-active     { background: #dcfce7; color: #166534; }
.sd-badge-disabled   { background: #f3f4f6; color: #4b5563; }
.sd-badge-completed  { background: #dcfce7; color: #166534; }
.sd-badge-inprogress { background: #fef9c3; color: #854d0e; }
.sd-badge-notstarted { background: #f3f4f6; color: #4b5563; }

.sd-action-btn {
	padding: 0.28rem 0.7rem;
	font-size: 0.75rem;
	font-weight: 600;
	border: 1px solid #e5e7eb;
	border-radius: 4px;
	background: #ffffff;
	color: #374151;
	cursor: pointer;
	transition: background 0.15s, border-color 0.15s;
	white-space: nowrap;
}

.sd-action-btn:hover:not(:disabled) { background: #f3f4f6; }
.sd-action-btn:disabled { opacity: 0.5; cursor: not-allowed; }

.sd-action-primary {
	background: #3b82f6;
	color: #ffffff;
	border-color: #3b82f6;
}

.sd-action-primary:hover:not(:disabled) { background: #2563eb; }

.sd-action-copy { color: #3b82f6; border-color: #dbeafe; }
.sd-action-copy:hover:not(:disabled) { background: #eff6ff; }
.sd-action-copy.copied { background: #dcfce7; color: #166534; border-color: #bbf7d0; }

.sd-action-disable { color: #ef4444; border-color: #fecaca; }
.sd-action-disable:hover:not(:disabled) { background: #fee2e2; }

.sd-action-enable { color: #16a34a; border-color: #bbf7d0; }
.sd-action-enable:hover:not(:disabled) { background: #dcfce7; }

.sd-course-list {
	display: flex;
	flex-direction: column;
	gap: 0.75rem;
}

.sd-course-header {
	display: flex;
	align-items: flex-start;
	justify-content: space-between;
	gap: 0.5rem;
	margin-bottom: 0.35rem;
}

.sd-course-title {
	font-size: 0.82rem;
	font-weight: 600;
	color: #111827;
	flex: 1;
	min-width: 0;
}

.sd-seq-control {
	display: flex;
	align-items: center;
	gap: 0.2rem;
	flex-shrink: 0;
}

.sd-seq-label {
	font-size: 0.68rem;
	font-weight: 700;
	color: #9ca3af;
}

.sd-seq-input {
	width: 36px;
	padding: 0.15rem 0.25rem;
	border: 1px solid #e5e7eb;
	border-radius: 4px;
	font-size: 0.75rem;
	text-align: center;
	color: #374151;
	background: #f9fafb;
}

.sd-seq-input:focus {
	outline: none;
	border-color: #3b82f6;
	background: #ffffff;
}

.sd-seq-input:disabled {
	opacity: 0.5;
}

.sd-course-meta {
	display: flex;
	align-items: center;
	justify-content: space-between;
	margin-bottom: 0.3rem;
}

.sd-progress-pct {
	font-size: 0.7rem;
	color: #6b7280;
	font-weight: 600;
}

.sd-progress-bar {
	height: 4px;
	background: #e5e7eb;
	border-radius: 999px;
	overflow: hidden;
}

.sd-progress-fill {
	height: 100%;
	background: #3b82f6;
	border-radius: 999px;
	transition: width 0.3s ease;
}

.sd-cred-actions {
	display: flex;
	gap: 0.5rem;
	flex-wrap: wrap;
}

.sd-reset-section {
	margin-top: 0.75rem;
	padding: 0.75rem;
	background: #f9fafb;
	border: 1px solid #e5e7eb;
	border-radius: 6px;
}

.sd-reset-label {
	font-size: 0.72rem;
	font-weight: 600;
	color: #6b7280;
	margin-bottom: 0.4rem;
}

.sd-reset-row {
	display: flex;
	gap: 0.4rem;
	align-items: center;
	margin-bottom: 0.5rem;
}

.sd-reset-input {
	flex: 1;
	padding: 0.35rem 0.6rem;
	border: 1px solid #d1d5db;
	border-radius: 4px;
	font-family: monospace;
	font-size: 0.82rem;
	background: #ffffff;
	color: #111827;
	min-width: 0;
}

.sd-reset-applied {
	font-size: 0.75rem;
	color: #166534;
	background: #dcfce7;
	border-radius: 4px;
	padding: 0.3rem 0.5rem;
	margin-bottom: 0.5rem;
}

.sd-reset-buttons {
	display: flex;
	gap: 0.4rem;
	justify-content: flex-end;
}

.sd-loading, .sd-empty {
	font-size: 0.82rem;
	color: #9ca3af;
	padding: 0.3rem 0;
}
</style>
