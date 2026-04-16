<script setup>
import { ref, onMounted } from 'vue';

const selectedTheme = ref('light');

// ── Change Password ───────────────────────────────────────────────────────

const showPasswordModal = ref(false);
const oldPassword = ref('');
const newPassword = ref('');
const confirmPassword = ref('');
const pwSaving = ref(false);

function closePasswordModal() {
	showPasswordModal.value = false;
	oldPassword.value = '';
	newPassword.value = '';
	confirmPassword.value = '';
}

const changePassword = async () => {
	const old_pw = oldPassword.value.trim();
	const new_pw = newPassword.value;
	const confirm_pw = confirmPassword.value;

	if (!old_pw || !new_pw || !confirm_pw) {
		frappe.show_alert({ message: 'Please fill in all password fields.', indicator: 'orange' });
		return;
	}
	if (new_pw.length < 8) {
		frappe.show_alert({ message: 'New password must be at least 8 characters.', indicator: 'orange' });
		return;
	}
	if (new_pw !== confirm_pw) {
		frappe.show_alert({ message: 'New passwords do not match.', indicator: 'orange' });
		return;
	}
	if (old_pw === new_pw) {
		frappe.show_alert({ message: 'New password must differ from current password.', indicator: 'orange' });
		return;
	}

	pwSaving.value = true;
	try {
		await frappe.call({
			method: 'frappe.core.doctype.user.user.update_password',
			args: { old_password: old_pw, new_password: new_pw },
		});
		frappe.show_alert({ message: 'Password updated successfully.', indicator: 'green' }, 3);
		closePasswordModal();
	} catch (e) {
		const msg = e?.message || e?.exc_type || 'Failed to update password.';
		frappe.show_alert({ message: msg, indicator: 'red' }, 5);
	} finally {
		pwSaving.value = false;
	}
};

const THEME_OPTIONS = [
	{
		value: 'light',
		label: 'Light',
		description: 'Always use light mode',
	},
	{
		value: 'dark',
		label: 'Dark',
		description: 'Always use dark mode',
	},
	{
		value: 'automatic',
		label: 'Auto',
		description: 'Follow system preference',
	},
];

const normalize = (v) => (v || 'light').toLowerCase();
const toTitle = (v) => v.charAt(0).toUpperCase() + v.slice(1);

onMounted(() => {
	const bootTheme = frappe.boot?.user?.desk_theme;
	selectedTheme.value = normalize(bootTheme);
});

const applyTheme = (value) => {
	if (selectedTheme.value === value) return;
	selectedTheme.value = value;

	// Set data-theme-mode — triggers Frappe's MutationObserver in desk.js
	document.documentElement.setAttribute('data-theme-mode', value);

	// Immediately resolve data-theme
	frappe.ui.set_theme();

	// Persist to User.desk_theme via the same API Frappe's ThemeSwitcher uses
	frappe.xcall('frappe.core.doctype.user.user.switch_theme', {
		theme: toTitle(value),
	}).then(() => {
		frappe.show_alert({ message: 'Theme updated.', indicator: 'green' }, 2);
	});
};
</script>

<template>
	<div class="atp-settings-page">
		<div class="settings-header">
			<span class="settings-title">ATP SETTINGS</span>
		</div>

		<div class="settings-body">
			<div class="settings-section">
				<div class="atp-section-label" style="margin-bottom: 1rem;">Appearance</div>

				<div class="theme-options">
					<label
						v-for="opt in THEME_OPTIONS"
						:key="opt.value"
						class="theme-option"
						:class="{ selected: selectedTheme === opt.value }"
						@click="applyTheme(opt.value)"
					>
						<div class="theme-preview" :data-theme-preview="opt.value">
							<div class="preview-navbar"></div>
							<div class="preview-body">
								<div class="preview-bar"></div>
								<div class="preview-bar short"></div>
							</div>
						</div>
						<div class="theme-option-footer">
							<input
								type="radio"
								:value="opt.value"
								:checked="selectedTheme === opt.value"
								name="desk_theme"
								@change="applyTheme(opt.value)"
							/>
							<div class="theme-option-label">
								<span class="theme-name">{{ opt.label }}</span>
								<span class="theme-desc">{{ opt.description }}</span>
							</div>
						</div>
					</label>
				</div>
			</div>

			<!-- Security section -->
			<div class="settings-section" style="margin-top: 1.5rem;">
				<div class="atp-section-label" style="margin-bottom: 0.75rem;">Security</div>
				<button class="atp-btn atp-btn-outline" @click="showPasswordModal = true">
					Change Password
				</button>
			</div>
		</div>
	</div>

	<!-- Change Password Modal -->
	<div v-if="showPasswordModal" class="atp-modal-overlay" @click.self="closePasswordModal">
		<div class="atp-modal">
			<div class="atp-modal-header">
				<span>Change Password</span>
				<button class="atp-modal-close" @click="closePasswordModal">&times;</button>
			</div>
			<div class="atp-modal-body">
				<div class="atp-form-field">
					<label>Current Password</label>
					<input
						v-model="oldPassword"
						type="password"
						class="atp-input"
						placeholder="Enter current password"
						autocomplete="current-password"
						:disabled="pwSaving"
					/>
				</div>
				<div class="atp-form-field">
					<label>New Password</label>
					<input
						v-model="newPassword"
						type="password"
						class="atp-input"
						placeholder="At least 8 characters"
						autocomplete="new-password"
						:disabled="pwSaving"
					/>
				</div>
				<div class="atp-form-field">
					<label>Confirm New Password</label>
					<input
						v-model="confirmPassword"
						type="password"
						class="atp-input"
						placeholder="Repeat new password"
						autocomplete="new-password"
						:disabled="pwSaving"
						@keydown.enter="changePassword"
					/>
				</div>
			</div>
			<div class="atp-modal-footer">
				<button class="atp-btn atp-btn-outline" @click="closePasswordModal">Cancel</button>
				<button
					class="atp-btn atp-btn-primary"
					:disabled="!oldPassword.trim() || !newPassword || !confirmPassword || pwSaving"
					@click="changePassword"
				>{{ pwSaving ? 'Saving…' : 'Change Password' }}</button>
			</div>
		</div>
	</div>
</template>

<style scoped>
.atp-settings-page {
	font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
	background: var(--atp-bg, var(--atp-gray-50));
	min-height: 100%;
}

.settings-header {
	display: flex;
	align-items: center;
	height: 48px;
	padding: 0 1.5rem;
	background: var(--atp-card-bg, #ffffff);
	border-bottom: 1px solid var(--atp-gray-200, #e5e7eb);
}

.settings-title {
	font-size: 0.85rem;
	font-weight: 700;
	letter-spacing: 0.08em;
	text-transform: uppercase;
	color: var(--atp-gray-900, #111827);
}

.settings-body {
	padding: 2rem 1.5rem;
	max-width: 600px;
}

.settings-section {
	background: var(--atp-card-bg, #ffffff);
	border: 1px solid var(--atp-gray-200, #e5e7eb);
	border-radius: var(--atp-radius, 6px);
	padding: 1.5rem;
}

.theme-options {
	display: flex;
	gap: 1rem;
	flex-wrap: wrap;
}

.theme-option {
	display: flex;
	flex-direction: column;
	gap: 0.75rem;
	padding: 0.75rem;
	border: 2px solid var(--atp-gray-200, #e5e7eb);
	border-radius: var(--atp-radius, 6px);
	cursor: pointer;
	width: 148px;
	transition: border-color 0.15s, box-shadow 0.15s;
	user-select: none;
}

.theme-option:hover {
	border-color: var(--atp-blue-muted, #dbeafe);
}

.theme-option.selected {
	border-color: var(--atp-blue, #3b82f6);
	box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.12);
}

/* Preview swatch */
.theme-preview {
	width: 100%;
	height: 80px;
	border-radius: 4px;
	overflow: hidden;
	border: 1px solid var(--atp-gray-200, #e5e7eb);
	display: flex;
	flex-direction: column;
}

/* Light swatch */
.theme-preview[data-theme-preview="light"] { background: #ffffff; }
.theme-preview[data-theme-preview="light"] .preview-navbar { background: #f3f4f6; }
.theme-preview[data-theme-preview="light"] .preview-body   { background: #ffffff; }
.theme-preview[data-theme-preview="light"] .preview-bar    { background: #e5e7eb; }

/* Dark swatch */
.theme-preview[data-theme-preview="dark"] { background: #0f172a; }
.theme-preview[data-theme-preview="dark"] .preview-navbar { background: #1e2433; }
.theme-preview[data-theme-preview="dark"] .preview-body   { background: #0f172a; }
.theme-preview[data-theme-preview="dark"] .preview-bar    { background: #1e2433; }

/* Auto swatch — split half-and-half */
.theme-preview[data-theme-preview="automatic"] {
	background: linear-gradient(to right, #f9fafb 50%, #0f172a 50%);
}
.theme-preview[data-theme-preview="automatic"] .preview-navbar,
.theme-preview[data-theme-preview="automatic"] .preview-body { display: none; }

.preview-navbar {
	height: 18px;
	flex-shrink: 0;
}

.preview-body {
	flex: 1;
	padding: 6px 8px;
	display: flex;
	flex-direction: column;
	gap: 5px;
}

.preview-bar {
	height: 7px;
	border-radius: 3px;
	width: 80%;
}

.preview-bar.short {
	width: 50%;
}

.theme-option-footer {
	display: flex;
	align-items: flex-start;
	gap: 0.5rem;
}

.theme-option-footer input[type="radio"] {
	accent-color: var(--atp-blue, #3b82f6);
	width: 14px;
	height: 14px;
	cursor: pointer;
	margin-top: 2px;
	flex-shrink: 0;
}

.theme-option-label {
	display: flex;
	flex-direction: column;
}

.theme-name {
	font-size: 0.82rem;
	font-weight: 600;
	color: var(--atp-gray-900, #111827);
	line-height: 1.2;
}

.theme-desc {
	font-size: 0.68rem;
	color: var(--atp-gray-500, #6b7280);
	margin-top: 0.2rem;
	line-height: 1.3;
}
</style>
