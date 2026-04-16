<script setup>
import { ref, onMounted, computed } from 'vue';
import StudentDrawer from './StudentDrawer.vue';

// ── State ─────────────────────────────────────────────────────────────────

const activeTab = ref('students'); // 'students' | 'enrollments'

// Students tab
const students = ref([]);
const studentsLoading = ref(false);
const studentSearch = ref('');
const studentStatusFilter = ref('all'); // 'all' | 'active' | 'disabled'
const singleEmail = ref('');
const singleName = ref('');
const singlePass = ref('');
const bulkText = ref('');
const bulkDefaultPass = ref('Student@123');
const creating = ref(false);
const creationMode = ref('single'); // 'single' | 'bulk'
const togglingAccess = ref('');

// Student drawer
const drawerStudent = ref(null);
const showDrawer = ref(false);

// Enrollments tab
const courses = ref([]);
const selectedCourse = ref('');
const enrollmentOverview = ref([]);
const enrollmentLoading = ref(false);
const selectedStudents = ref([]);
const enrolling = ref(false);
const unenrolledSearch = ref('');
const enrolledSearch = ref('');
const enrolledStatusFilter = ref('all'); // 'all' | 'Completed' | 'In Progress'

// ── Lifecycle ─────────────────────────────────────────────────────────────

onMounted(async () => {
	await Promise.all([loadStudents(), loadCourses()]);
});

// ── Data loaders ──────────────────────────────────────────────────────────

const loadStudents = async () => {
	studentsLoading.value = true;
	try {
		const res = await frappe.call({ method: 'atp.atp.api.get_students' });
		students.value = res.message || [];
	} catch (e) {
		console.error('load students error', e);
	} finally {
		studentsLoading.value = false;
	}
};

const loadCourses = async () => {
	const res = await frappe.db.get_list('Course', {
		fields: ['name', 'title', 'is_published'],
		order_by: 'title asc',
		limit: 100,
	});
	courses.value = res;
};

const loadEnrollmentOverview = async (course) => {
	if (!course) return;
	enrollmentLoading.value = true;
	try {
		const res = await frappe.call({
			method: 'atp.atp.api.get_enrollment_overview',
			args: { course },
		});
		enrollmentOverview.value = res.message || [];
	} catch (e) {
		console.error('enrollment overview error', e);
	} finally {
		enrollmentLoading.value = false;
	}
};

// ── Student creation ──────────────────────────────────────────────────────

const createSingleStudent = async () => {
	if (!singleEmail.value || !singleName.value || !singlePass.value) {
		frappe.show_alert({ message: 'Please fill in all fields.', indicator: 'orange' });
		return;
	}
	creating.value = true;
	try {
		const res = await frappe.call({
			method: 'atp.atp.api.create_student',
			args: {
				email: singleEmail.value,
				full_name: singleName.value,
				password: singlePass.value,
			},
		});
		frappe.show_alert({ message: `Created ${res.message.email}`, indicator: 'green' });
		singleEmail.value = '';
		singleName.value = '';
		singlePass.value = '';
		await loadStudents();
	} catch (e) {
		console.error(e);
	} finally {
		creating.value = false;
	}
};

const createBulkStudents = async () => {
	const lines = bulkText.value.split('\n').map(l => l.trim()).filter(Boolean);
	if (!lines.length) {
		frappe.show_alert({ message: 'No entries found.', indicator: 'orange' });
		return;
	}
	const studentsList = lines.map(line => {
		const [email, ...rest] = line.split(',');
		return {
			email: email.trim(),
			full_name: rest.join(',').trim() || email.trim().split('@')[0],
			password: bulkDefaultPass.value,
		};
	});
	creating.value = true;
	try {
		const res = await frappe.call({
			method: 'atp.atp.api.bulk_create_students',
			args: { students_json: JSON.stringify(studentsList) },
		});
		const { created, skipped } = res.message;
		frappe.show_alert({
			message: `Created ${created.length} student(s)${skipped.length ? `, skipped ${skipped.length}` : ''}.`,
			indicator: 'green',
		});
		bulkText.value = '';
		await loadStudents();
	} catch (e) {
		console.error(e);
	} finally {
		creating.value = false;
	}
};

// ── Enrollments ───────────────────────────────────────────────────────────

const onCourseSelect = async () => {
	selectedStudents.value = [];
	unenrolledSearch.value = '';
	enrolledSearch.value = '';
	await loadEnrollmentOverview(selectedCourse.value);
};

const enrolledEmails = computed(() =>
	new Set(enrollmentOverview.value.map(e => e.student)),
);

const unenrolledStudents = computed(() =>
	students.value.filter(s => !enrolledEmails.value.has(s.email)),
);

const enrollSelected = async () => {
	if (!selectedCourse.value || !selectedStudents.value.length) {
		frappe.show_alert({ message: 'Select a course and at least one student.', indicator: 'orange' });
		return;
	}
	enrolling.value = true;
	let count = 0;
	for (const email of selectedStudents.value) {
		try {
			await frappe.call({
				method: 'atp.atp.api.enroll_student',
				args: { course: selectedCourse.value, student: email },
			});
			count++;
		} catch (e) {
			console.error(`enroll ${email}`, e);
		}
	}
	enrolling.value = false;
	selectedStudents.value = [];
	frappe.show_alert({ message: `Enrolled ${count} student(s).`, indicator: 'green' });
	await loadEnrollmentOverview(selectedCourse.value);
};

const toggleStudent = (email) => {
	const idx = selectedStudents.value.indexOf(email);
	if (idx >= 0) selectedStudents.value.splice(idx, 1);
	else selectedStudents.value.push(email);
};

// ── Computed filters ──────────────────────────────────────────────────────

const filteredStudents = computed(() => {
	let result = students.value;
	const q = studentSearch.value.toLowerCase().trim();
	if (q) result = result.filter(s =>
		(s.full_name || '').toLowerCase().includes(q) || s.email.toLowerCase().includes(q),
	);
	if (studentStatusFilter.value === 'active') result = result.filter(s => s.enabled);
	if (studentStatusFilter.value === 'disabled') result = result.filter(s => !s.enabled);
	return result;
});

const filteredUnenrolled = computed(() => {
	const q = unenrolledSearch.value.toLowerCase().trim();
	if (!q) return unenrolledStudents.value;
	return unenrolledStudents.value.filter(s =>
		(s.full_name || '').toLowerCase().includes(q) || s.email.toLowerCase().includes(q),
	);
});

const filteredEnrolled = computed(() => {
	let result = enrollmentOverview.value;
	const q = enrolledSearch.value.toLowerCase().trim();
	if (q) result = result.filter(e =>
		(e.full_name || '').toLowerCase().includes(q) || (e.email || '').toLowerCase().includes(q),
	);
	if (enrolledStatusFilter.value !== 'all') {
		result = result.filter(e => e.status === enrolledStatusFilter.value);
	}
	return result;
});

// ── Student drawer ────────────────────────────────────────────────────────

const openDrawer = (student) => {
	drawerStudent.value = student;
	showDrawer.value = true;
};

const closeDrawer = () => {
	showDrawer.value = false;
	drawerStudent.value = null;
};

const onAccessToggled = (updatedStudent) => {
	const s = students.value.find(x => x.email === updatedStudent.email);
	if (s) s.enabled = updatedStudent.enabled;
	if (drawerStudent.value?.email === updatedStudent.email) {
		drawerStudent.value = { ...drawerStudent.value, enabled: updatedStudent.enabled };
	}
};

// ── Enable/Disable (inline in row) ────────────────────────────────────────

const toggleAccess = async (student) => {
	togglingAccess.value = student.email;
	const newEnabled = student.enabled ? 0 : 1;
	try {
		await frappe.call({
			method: 'atp.atp.api.toggle_student_access',
			args: { student_email: student.email, enabled: newEnabled },
		});
		student.enabled = newEnabled;
		frappe.show_alert({
			message: `${student.full_name || student.email} ${newEnabled ? 'enabled' : 'disabled'}.`,
			indicator: newEnabled ? 'green' : 'orange',
		}, 2);
	} catch (e) {
		frappe.show_alert({ message: e?.message || 'Failed to update access.', indicator: 'red' }, 5);
	} finally {
		togglingAccess.value = '';
	}
};

// ── Bulk credential copy ──────────────────────────────────────────────────

const copyAllStudentCredentials = () => {
	const list = filteredStudents.value;
	if (!list.length) return;
	const header = `ATP Login Details\n${'─'.repeat(50)}`;
	const rows = list.map(s => `${s.full_name || s.email}\n  Email: ${s.email}`).join('\n\n');
	const footer = `\nLogin at: ${window.location.origin}/app/login`;
	navigator.clipboard.writeText([header, rows, footer].join('\n')).then(() => {
		frappe.show_alert({ message: `Copied ${list.length} student(s) to clipboard.`, indicator: 'green' });
	});
};
</script>

<template>
	<div class="em-root">
		<div class="em-header">
			<span class="em-title">ENROLLMENT MANAGER</span>
		</div>

		<div class="em-body">
			<!-- Tabs -->
			<div class="atp-tabs">
				<div class="atp-tab" :class="{ active: activeTab === 'students' }" @click="activeTab = 'students'">
					Students
				</div>
				<div class="atp-tab" :class="{ active: activeTab === 'enrollments' }" @click="activeTab = 'enrollments'">
					Enrollments
				</div>
			</div>

			<!-- ── STUDENTS TAB ─────────────────────────────────────────── -->
			<div v-if="activeTab === 'students'">
				<div class="two-col">
					<!-- Create form -->
					<div class="panel">
						<div class="atp-section-label">Create Student Account</div>
						<div class="mode-toggle">
							<button :class="['mode-btn', { active: creationMode === 'single' }]" @click="creationMode = 'single'">Single</button>
							<button :class="['mode-btn', { active: creationMode === 'bulk' }]" @click="creationMode = 'bulk'">Bulk</button>
						</div>

						<div v-if="creationMode === 'single'" class="form-section">
							<div class="atp-form-field">
								<label>Email</label>
								<input v-model="singleEmail" class="atp-input" type="email" placeholder="student@example.com" />
							</div>
							<div class="atp-form-field" style="margin-top: 0.5rem;">
								<label>Full Name</label>
								<input v-model="singleName" class="atp-input" type="text" placeholder="First Last" />
							</div>
							<div class="atp-form-field" style="margin-top: 0.5rem;">
								<label>Temporary Password</label>
								<input v-model="singlePass" class="atp-input" type="text" placeholder="Password" />
							</div>
							<button class="atp-btn atp-btn-primary" style="margin-top: 0.75rem; width: 100%;" :disabled="creating" @click="createSingleStudent">
								{{ creating ? 'Creating…' : '+ Create Student' }}
							</button>
						</div>

						<div v-if="creationMode === 'bulk'" class="form-section">
							<div class="atp-form-field">
								<label>One per line: email, full name</label>
								<textarea
									v-model="bulkText"
									class="atp-input atp-textarea"
									placeholder="jane.doe@school.edu, Jane Doe&#10;john.smith@school.edu, John Smith"
								></textarea>
							</div>
							<div class="atp-form-field" style="margin-top: 0.5rem;">
								<label>Default Password for all</label>
								<input v-model="bulkDefaultPass" class="atp-input" type="text" />
							</div>
							<button class="atp-btn atp-btn-primary" style="margin-top: 0.75rem; width: 100%;" :disabled="creating" @click="createBulkStudents">
								{{ creating ? 'Creating…' : 'Create All' }}
							</button>
						</div>
					</div>

					<!-- Student list -->
					<div class="panel">
						<div class="student-toolbar">
							<div class="atp-section-label" style="margin-bottom:0">
								All Students ({{ filteredStudents.length }}{{ filteredStudents.length !== students.length ? ` of ${students.length}` : '' }})
							</div>
							<button
								class="atp-btn atp-btn-outline"
								style="font-size:0.75rem;padding:0.28rem 0.7rem;"
								:disabled="filteredStudents.length === 0"
								title="Copy name + email + login URL for all visible students"
								@click="copyAllStudentCredentials"
							>Copy All</button>
						</div>

						<div class="student-filters">
							<input
								v-model="studentSearch"
								class="atp-input search-input"
								type="search"
								placeholder="Search name or email…"
							/>
							<div class="filter-group">
								<button :class="['filter-btn', { active: studentStatusFilter === 'all' }]" @click="studentStatusFilter = 'all'">All</button>
								<button :class="['filter-btn', { active: studentStatusFilter === 'active' }]" @click="studentStatusFilter = 'active'">Active</button>
								<button :class="['filter-btn', { active: studentStatusFilter === 'disabled' }]" @click="studentStatusFilter = 'disabled'">Disabled</button>
							</div>
						</div>

						<div v-if="studentsLoading" class="loading-hint">Loading…</div>
						<div v-else-if="students.length === 0" class="empty-hint">No students yet.</div>
						<div v-else-if="filteredStudents.length === 0" class="empty-hint">No students match your search.</div>
						<table v-else class="atp-table">
							<thead>
								<tr>
									<th>Name</th>
									<th>Email</th>
									<th>Access</th>
									<th>Actions</th>
								</tr>
							</thead>
							<tbody>
								<tr
									v-for="s in filteredStudents"
									:key="s.email"
									class="student-row"
									@click="openDrawer(s)"
								>
									<td>{{ s.full_name || '—' }}</td>
									<td class="em-email">{{ s.email }}</td>
									<td>
										<span :class="['em-badge', s.enabled ? 'em-badge-active' : 'em-badge-disabled']">
											{{ s.enabled ? 'Active' : 'Disabled' }}
										</span>
									</td>
									<td @click.stop>
										<button
											class="em-action-btn"
											:class="s.enabled ? 'em-action-disable' : 'em-action-enable'"
											:disabled="togglingAccess === s.email"
											@click="toggleAccess(s)"
										>{{ togglingAccess === s.email ? '…' : (s.enabled ? 'Disable' : 'Enable') }}</button>
									</td>
								</tr>
							</tbody>
						</table>
					</div>
				</div>
			</div>

			<!-- ── ENROLLMENTS TAB ──────────────────────────────────────── -->
			<div v-if="activeTab === 'enrollments'">
				<div class="two-col">
					<!-- Enroll form -->
					<div class="panel">
						<div class="atp-section-label">Enroll Students in Course</div>
						<div class="atp-form-field">
							<label>Select Course</label>
							<select v-model="selectedCourse" class="atp-input atp-select" @change="onCourseSelect">
								<option value="">— Choose a course —</option>
								<option v-for="c in courses" :key="c.name" :value="c.name">{{ c.title }}</option>
							</select>
						</div>

						<div v-if="selectedCourse" style="margin-top: 1rem;">
							<div class="atp-section-label">Unenrolled Students</div>
							<input
								v-model="unenrolledSearch"
								class="atp-input search-input"
								type="search"
								placeholder="Search…"
								style="margin-bottom:0.5rem"
							/>
							<div v-if="unenrolledStudents.length === 0" class="empty-hint">All students are already enrolled.</div>
							<div v-else-if="filteredUnenrolled.length === 0" class="empty-hint">No students match your search.</div>
							<div v-else>
								<div
									v-for="s in filteredUnenrolled"
									:key="s.email"
									class="student-check-row"
									@click="toggleStudent(s.email)"
								>
									<input type="checkbox" :checked="selectedStudents.includes(s.email)" readonly />
									<span>{{ s.full_name || s.email }}</span>
									<span class="email-hint">{{ s.email }}</span>
								</div>
								<button
									class="atp-btn atp-btn-primary"
									style="margin-top: 0.75rem; width: 100%;"
									:disabled="enrolling || selectedStudents.length === 0"
									@click="enrollSelected"
								>
									{{ enrolling ? 'Enrolling…' : `Enroll Selected (${selectedStudents.length})` }}
								</button>
							</div>
						</div>
					</div>

					<!-- Enrollment list -->
					<div class="panel">
						<div class="atp-section-label">Current Enrollments</div>
						<div v-if="!selectedCourse" class="empty-hint">Select a course to see enrollments.</div>
						<div v-else-if="enrollmentLoading" class="loading-hint">Loading…</div>
						<div v-else-if="enrollmentOverview.length === 0" class="empty-hint">No enrollments yet.</div>
						<template v-else>
							<div class="enrolled-filters">
								<input
									v-model="enrolledSearch"
									class="atp-input search-input"
									type="search"
									placeholder="Search…"
								/>
								<div class="filter-group">
									<button :class="['filter-btn', { active: enrolledStatusFilter === 'all' }]" @click="enrolledStatusFilter = 'all'">All</button>
									<button :class="['filter-btn', { active: enrolledStatusFilter === 'Completed' }]" @click="enrolledStatusFilter = 'Completed'">Completed</button>
									<button :class="['filter-btn', { active: enrolledStatusFilter === 'In Progress' }]" @click="enrolledStatusFilter = 'In Progress'">In Progress</button>
								</div>
							</div>
							<div v-if="filteredEnrolled.length === 0" class="empty-hint">No students match your filter.</div>
							<table v-else class="atp-table">
								<thead>
									<tr>
										<th>Student</th>
										<th>Status</th>
									</tr>
								</thead>
								<tbody>
									<tr v-for="e in filteredEnrolled" :key="e.name">
										<td>
											<div>{{ e.full_name }}</div>
											<div class="email-hint">{{ e.email }}</div>
										</td>
										<td>
											<span :class="['em-badge', e.status === 'Completed' ? 'em-badge-completed' : 'em-badge-inprogress']">
												{{ e.status }}
											</span>
										</td>
									</tr>
								</tbody>
							</table>
						</template>
					</div>
				</div>
			</div>
		</div>
	</div>

	<!-- Student Drawer -->
	<StudentDrawer
		:student="drawerStudent"
		:show="showDrawer"
		@close="closeDrawer"
		@access-toggled="onAccessToggled"
	/>
</template>

<style scoped>
.em-root {
	font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
	background: var(--atp-bg, #f9fafb);
	min-height: 100%;
}

.em-header {
	height: 48px;
	display: flex;
	align-items: center;
	padding: 0 1.5rem;
	background: var(--atp-card-bg, #ffffff);
	border-bottom: 1px solid var(--atp-gray-200, #e5e7eb);
}

.em-title {
	font-size: 0.85rem;
	font-weight: 700;
	letter-spacing: 0.08em;
	text-transform: uppercase;
	color: var(--atp-gray-900, #111827);
}

.em-body {
	padding: 1.5rem;
}

/* Tabs */
.atp-tabs {
	display: flex;
	border-bottom: 2px solid var(--atp-gray-200, #e5e7eb);
	margin-bottom: 1.5rem;
}

.atp-tab {
	padding: 0.5rem 1.25rem;
	font-size: 0.82rem;
	font-weight: 600;
	color: var(--atp-gray-500, #6b7280);
	cursor: pointer;
	border-bottom: 2px solid transparent;
	margin-bottom: -2px;
	transition: color 0.15s;
	user-select: none;
}

.atp-tab.active {
	color: var(--atp-blue, #3b82f6);
	border-bottom-color: var(--atp-blue, #3b82f6);
}

/* Two-column layout */
.two-col {
	display: grid;
	grid-template-columns: 1fr 1fr;
	gap: 1.5rem;
}

.panel {
	background: var(--atp-card-bg, #ffffff);
	border: 1px solid var(--atp-gray-200, #e5e7eb);
	border-radius: 6px;
	padding: 1.25rem;
}

.atp-section-label {
	font-size: 0.72rem;
	font-weight: 700;
	letter-spacing: 0.07em;
	text-transform: uppercase;
	color: var(--atp-gray-500, #6b7280);
	margin-bottom: 0.75rem;
}

/* Mode toggle */
.mode-toggle {
	display: flex;
	border: 1px solid var(--atp-gray-200, #e5e7eb);
	border-radius: 6px;
	overflow: hidden;
	margin-bottom: 0.75rem;
	width: fit-content;
}

.mode-btn {
	padding: 0.3rem 0.85rem;
	font-size: 0.8rem;
	font-weight: 600;
	color: var(--atp-gray-500, #6b7280);
	background: var(--atp-card-bg, #ffffff);
	border: none;
	cursor: pointer;
	transition: background 0.15s, color 0.15s;
}

.mode-btn.active {
	background: var(--atp-blue, #3b82f6);
	color: #ffffff;
}

.form-section {
	display: flex;
	flex-direction: column;
}

/* Form fields */
.atp-form-field {
	display: flex;
	flex-direction: column;
	gap: 0.25rem;
}

.atp-form-field label {
	font-size: 0.72rem;
	font-weight: 600;
	text-transform: uppercase;
	letter-spacing: 0.04em;
	color: var(--atp-gray-500, #6b7280);
}

.atp-input {
	padding: 0.45rem 0.7rem;
	border: 1px solid var(--atp-gray-300, #d1d5db);
	border-radius: 5px;
	font-size: 0.875rem;
	color: var(--atp-gray-900, #111827);
	background: var(--atp-card-bg, #ffffff);
	width: 100%;
	box-sizing: border-box;
	transition: border-color 0.15s, box-shadow 0.15s;
}

.atp-input:focus {
	outline: none;
	border-color: #3b82f6;
	box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.12);
}

.atp-textarea {
	resize: vertical;
	min-height: 90px;
}

.atp-select {
	appearance: none;
	background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='10' height='10' viewBox='0 0 10 10'%3E%3Cpath fill='%236b7280' d='M5 7L0 2h10z'/%3E%3C/svg%3E");
	background-repeat: no-repeat;
	background-position: right 0.6rem center;
	padding-right: 2rem;
}

/* Buttons */
.atp-btn {
	display: inline-flex;
	align-items: center;
	justify-content: center;
	padding: 0.45rem 0.9rem;
	border-radius: 5px;
	font-size: 0.82rem;
	font-weight: 600;
	cursor: pointer;
	border: none;
	transition: background 0.15s;
}

.atp-btn:disabled {
	opacity: 0.5;
	cursor: not-allowed;
}

.atp-btn-primary {
	background: #3b82f6;
	color: #ffffff;
}

.atp-btn-primary:hover:not(:disabled) {
	background: #2563eb;
}

.atp-btn-outline {
	background: transparent;
	color: #3b82f6;
	border: 1px solid #dbeafe;
}

.atp-btn-outline:hover:not(:disabled) {
	background: #eff6ff;
}

/* Table */
.atp-table {
	width: 100%;
	border-collapse: collapse;
	font-size: 0.82rem;
}

.atp-table th {
	text-align: left;
	font-size: 0.68rem;
	font-weight: 700;
	letter-spacing: 0.07em;
	text-transform: uppercase;
	color: var(--atp-gray-500, #6b7280);
	padding: 0.4rem 0.5rem;
	border-bottom: 1px solid var(--atp-gray-200, #e5e7eb);
}

.atp-table td {
	padding: 0.55rem 0.5rem;
	border-bottom: 1px solid var(--atp-gray-100, #f3f4f6);
	color: var(--atp-gray-700, #374151);
}

/* Badges */
.em-badge {
	display: inline-block;
	padding: 0.15rem 0.5rem;
	border-radius: 999px;
	font-size: 0.68rem;
	font-weight: 600;
}

.em-badge-active     { background: var(--atp-badge-completed-bg, #dcfce7); color: var(--atp-badge-completed-fg, #166534); }
.em-badge-disabled   { background: var(--atp-gray-100, #f3f4f6); color: var(--atp-gray-600, #4b5563); }
.em-badge-completed  { background: var(--atp-badge-completed-bg, #dcfce7); color: var(--atp-badge-completed-fg, #166534); }
.em-badge-inprogress { background: var(--atp-badge-inprogress-bg, #fef9c3); color: var(--atp-badge-inprogress-fg, #854d0e); }

/* Student toolbar + filters */
.student-toolbar {
	display: flex;
	align-items: center;
	justify-content: space-between;
	margin-bottom: 0.6rem;
}

.student-filters {
	display: flex;
	gap: 0.5rem;
	align-items: center;
	margin-bottom: 0.75rem;
	flex-wrap: wrap;
}

.enrolled-filters {
	display: flex;
	gap: 0.5rem;
	align-items: center;
	margin-bottom: 0.75rem;
	flex-wrap: wrap;
}

.search-input {
	flex: 1;
	min-width: 140px;
}

.filter-group {
	display: flex;
	border: 1px solid var(--atp-gray-200, #e5e7eb);
	border-radius: 5px;
	overflow: hidden;
	flex-shrink: 0;
}

.filter-btn {
	padding: 0.28rem 0.65rem;
	font-size: 0.72rem;
	font-weight: 600;
	color: var(--atp-gray-500, #6b7280);
	background: var(--atp-card-bg, #ffffff);
	border: none;
	border-right: 1px solid var(--atp-gray-200, #e5e7eb);
	cursor: pointer;
	transition: background 0.15s, color 0.15s;
	white-space: nowrap;
}

.filter-btn:last-child {
	border-right: none;
}

.filter-btn.active {
	background: var(--atp-blue, #3b82f6);
	color: #ffffff;
}

/* Clickable student rows */
.student-row {
	cursor: pointer;
}

.student-row:hover td {
	background: var(--atp-bg, #f9fafb);
}

/* Student checkbox rows */
.student-check-row {
	display: flex;
	align-items: center;
	gap: 0.5rem;
	padding: 0.4rem 0;
	cursor: pointer;
	font-size: 0.85rem;
	color: var(--atp-gray-700, #374151);
	border-bottom: 1px solid var(--atp-gray-100, #f3f4f6);
}

.student-check-row:hover {
	background: var(--atp-bg, #f9fafb);
}

.email-hint {
	font-size: 0.72rem;
	color: var(--atp-gray-500, #9ca3af);
	margin-left: auto;
}

.loading-hint, .empty-hint {
	font-size: 0.82rem;
	color: var(--atp-gray-500, #9ca3af);
	padding: 0.75rem 0;
}

.em-email {
	font-size: 0.78rem;
	color: var(--atp-gray-500, #6b7280);
}

.em-action-btn {
	padding: 0.22rem 0.6rem;
	font-size: 0.72rem;
	font-weight: 600;
	border: 1px solid var(--atp-gray-200, #e5e7eb);
	border-radius: 4px;
	background: var(--atp-card-bg, #ffffff);
	color: var(--atp-gray-700, #374151);
	cursor: pointer;
	transition: background 0.15s, border-color 0.15s;
	white-space: nowrap;
}

.em-action-btn:hover:not(:disabled) {
	background: var(--atp-gray-100, #f3f4f6);
	border-color: var(--atp-gray-300, #d1d5db);
}

.em-action-btn:disabled {
	opacity: 0.5;
	cursor: not-allowed;
}

.em-action-disable { color: #ef4444; border-color: #fecaca; }
.em-action-disable:hover:not(:disabled) { background: #fee2e2; border-color: #fca5a5; }

.em-action-enable { color: #16a34a; border-color: #bbf7d0; }
.em-action-enable:hover:not(:disabled) { background: #dcfce7; border-color: #86efac; }

@media (max-width: 768px) {
	.two-col {
		grid-template-columns: 1fr;
	}
}
</style>
