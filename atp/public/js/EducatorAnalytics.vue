<script setup>
import { ref, computed, onMounted } from 'vue';

// ── State ─────────────────────────────────────────────────────────────────

const courses = ref([]);
const selectedCourse = ref('');
const analytics = ref(null);
const loading = ref(false);
const loadError = ref(false);
const searchQuery = ref('');
const sortBy = ref('progress_pct');
const sortDir = ref('asc');

// ── Lifecycle ─────────────────────────────────────────────────────────────

onMounted(async () => {
	await loadCourses();
	// Auto-select first course if only one
	if (courses.value.length === 1) {
		selectedCourse.value = courses.value[0].name;
		await loadAnalytics();
	}
});

// ── Loaders ───────────────────────────────────────────────────────────────

async function loadCourses() {
	try {
		const r = await frappe.call({ method: 'atp.atp.api.get_analytics_courses' });
		courses.value = r.message || [];
	} catch {
		courses.value = [];
	}
}

async function loadAnalytics() {
	if (!selectedCourse.value) return;
	loading.value = true;
	loadError.value = false;
	analytics.value = null;
	try {
		const r = await frappe.call({
			method: 'atp.atp.api.get_educator_analytics',
			args: { course: selectedCourse.value },
		});
		analytics.value = r.message;
	} catch {
		loadError.value = true;
	} finally {
		loading.value = false;
	}
}

// ── Computed ──────────────────────────────────────────────────────────────

const selectedCourseTitle = computed(() => {
	const c = courses.value.find(c => c.name === selectedCourse.value);
	return c ? c.title : '';
});

const filteredStudents = computed(() => {
	if (!analytics.value) return [];
	let list = [...analytics.value.students];

	if (searchQuery.value.trim()) {
		const q = searchQuery.value.toLowerCase();
		list = list.filter(s =>
			s.full_name.toLowerCase().includes(q) ||
			s.email.toLowerCase().includes(q)
		);
	}

	list.sort((a, b) => {
		let va = a[sortBy.value];
		let vb = b[sortBy.value];
		if (typeof va === 'string') va = va.toLowerCase();
		if (typeof vb === 'string') vb = vb.toLowerCase();
		if (va < vb) return sortDir.value === 'asc' ? -1 : 1;
		if (va > vb) return sortDir.value === 'asc' ? 1 : -1;
		return 0;
	});

	return list;
});

const attentionStudents = computed(() => {
	if (!analytics.value) return [];
	const now = new Date();
	return analytics.value.students.filter(s => {
		if (s.status === 'Completed') return false;
		// Not started
		if (s.progress_pct === 0) return true;
		// Stalled — last active more than 7 days ago
		const lastActive = new Date(s.last_active);
		const daysDiff = (now - lastActive) / (1000 * 60 * 60 * 24);
		return daysDiff > 7;
	});
});

const maxNodeCount = computed(() => {
	if (!analytics.value) return 1;
	return Math.max(...analytics.value.node_distribution, 1);
});

// ── Sorting ───────────────────────────────────────────────────────────────

function setSort(field) {
	if (sortBy.value === field) {
		sortDir.value = sortDir.value === 'asc' ? 'desc' : 'asc';
	} else {
		sortBy.value = field;
		sortDir.value = field === 'progress_pct' ? 'asc' : 'asc';
	}
}

function sortIcon(field) {
	if (sortBy.value !== field) return '↕';
	return sortDir.value === 'asc' ? '↑' : '↓';
}

// ── Helpers ───────────────────────────────────────────────────────────────

function statusClass(status, pct) {
	if (status === 'Completed') return 'badge-completed';
	if (pct > 0) return 'badge-inprogress';
	return 'badge-notstarted';
}

function statusLabel(status, pct) {
	if (status === 'Completed') return 'Completed';
	if (pct > 0) return 'In Progress';
	return 'Not Started';
}

function formatDate(dateStr) {
	if (!dateStr) return '—';
	const d = new Date(dateStr);
	if (isNaN(d)) return dateStr;
	const now = new Date();
	const diff = Math.floor((now - d) / (1000 * 60 * 60 * 24));
	if (diff === 0) return 'Today';
	if (diff === 1) return 'Yesterday';
	if (diff < 7) return `${diff}d ago`;
	if (diff < 30) return `${Math.floor(diff / 7)}w ago`;
	return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
}

function progressBarColor(pct, status) {
	if (status === 'Completed') return '#22c55e';
	if (pct >= 66) return '#3b82f6';
	if (pct >= 33) return '#f59e0b';
	return '#e5e7eb';
}

function getInitials(name) {
	if (!name) return '?';
	return name.split(' ').map(w => w[0]).join('').toUpperCase().slice(0, 2);
}

function goToDashboard() {
	frappe.set_route('educator_dashboard');
}
</script>

<template>
	<div class="ea-root">
		<!-- Header -->
		<div class="ea-header">
			<button class="ea-back-btn" @click="goToDashboard">← Dashboard</button>
			<span class="ea-title">CLASS ANALYTICS</span>
		</div>

		<div class="ea-body">
			<!-- Course Picker -->
			<div class="ea-course-picker">
				<select
					v-model="selectedCourse"
					class="ea-select"
					@change="loadAnalytics"
				>
					<option value="">— Select a course to view analytics —</option>
					<option v-for="c in courses" :key="c.name" :value="c.name">
						{{ c.title }}
						<template v-if="c.enrollment_count > 0"> ({{ c.enrollment_count }})</template>
					</option>
				</select>
			</div>

			<!-- No course selected -->
			<div v-if="!selectedCourse" class="ea-empty-state">
				<div class="ea-empty-icon">📊</div>
				<p class="ea-empty-title">Select a course to view analytics</p>
				<p class="ea-empty-sub">Choose a course above to see student progress, completion rates, and insights.</p>
			</div>

			<!-- Loading -->
			<div v-else-if="loading" class="ea-loading">
				<div class="ea-loading-spinner"></div>
				<span>Loading analytics…</span>
			</div>

			<!-- Error -->
			<div v-else-if="loadError" class="ea-error">
				<div>⚠️ Could not load analytics.</div>
				<button class="ea-btn ea-btn-outline" style="margin-top:0.75rem" @click="loadAnalytics">Retry</button>
			</div>

			<!-- Analytics content -->
			<template v-else-if="analytics">

				<!-- Course title -->
				<h2 class="ea-course-title">{{ selectedCourseTitle }}</h2>

				<!-- ── Summary Stats ───────────────────────────────────── -->
				<div class="ea-stats-row">
					<div class="ea-stat-card">
						<div class="ea-stat-value">{{ analytics.total }}</div>
						<div class="ea-stat-label">Total Students</div>
					</div>
					<div class="ea-stat-card ea-stat-completed">
						<div class="ea-stat-value">{{ analytics.completed }}</div>
						<div class="ea-stat-label">Completed</div>
					</div>
					<div class="ea-stat-card ea-stat-inprogress">
						<div class="ea-stat-value">{{ analytics.in_progress }}</div>
						<div class="ea-stat-label">In Progress</div>
					</div>
					<div class="ea-stat-card ea-stat-notstarted">
						<div class="ea-stat-value">{{ analytics.not_started }}</div>
						<div class="ea-stat-label">Not Started</div>
					</div>
					<div class="ea-stat-card">
						<div class="ea-stat-value">{{ analytics.avg_progress }}%</div>
						<div class="ea-stat-label">Avg Progress</div>
					</div>
					<div class="ea-stat-card">
						<div class="ea-stat-value">{{ analytics.completion_rate }}%</div>
						<div class="ea-stat-label">Completion Rate</div>
					</div>
				</div>

				<!-- Empty class -->
				<div v-if="analytics.total === 0" class="ea-empty-state" style="margin-top:1.5rem">
					<div class="ea-empty-icon">👥</div>
					<p class="ea-empty-title">No students enrolled yet</p>
					<p class="ea-empty-sub">Enroll students via the Enrollment Manager to see their progress here.</p>
				</div>

				<template v-else>

					<!-- ── Needs Attention ─────────────────────────────── -->
					<div v-if="attentionStudents.length > 0" class="ea-section">
						<div class="ea-section-label">
							⚠️ Needs Attention
							<span class="ea-attention-count">{{ attentionStudents.length }}</span>
						</div>
						<div class="ea-attention-list">
							<div
								v-for="s in attentionStudents"
								:key="s.enrollment_name"
								class="ea-attention-row"
							>
								<div class="ea-student-avatar">{{ getInitials(s.full_name) }}</div>
								<div class="ea-attention-info">
									<span class="ea-student-name">{{ s.full_name }}</span>
									<span class="ea-student-email">{{ s.email }}</span>
								</div>
								<div class="ea-attention-reason">
									<span v-if="s.progress_pct === 0" class="ea-badge ea-badge-notstarted">Not started</span>
									<span v-else class="ea-badge ea-badge-stalled">Stalled</span>
									<span class="ea-last-active">Last active: {{ formatDate(s.last_active) }}</span>
								</div>
							</div>
						</div>
					</div>

					<!-- ── Course Node Distribution ───────────────────── -->
					<div v-if="analytics.total_nodes > 0" class="ea-section">
						<div class="ea-section-label">Progress Distribution</div>
						<div class="ea-distribution-hint">Where students are in the course right now</div>
						<div class="ea-dist-chart">
							<div
								v-for="(count, idx) in analytics.node_distribution"
								:key="idx"
								class="ea-dist-col"
								:title="`${analytics.node_labels[idx] || 'Node ' + (idx+1)}: ${count} student${count !== 1 ? 's' : ''}`"
							>
								<div class="ea-dist-bar-wrap">
									<div
										class="ea-dist-bar"
										:style="{
											height: maxNodeCount > 0 ? Math.max(4, (count / maxNodeCount) * 80) + 'px' : '4px',
										}"
									></div>
									<span class="ea-dist-count">{{ count }}</span>
								</div>
								<div class="ea-dist-label">{{ analytics.node_labels[idx] || `Step ${idx + 1}` }}</div>
							</div>
						</div>
					</div>

					<!-- ── Student Progress Table ─────────────────────── -->
					<div class="ea-section">
						<div class="ea-section-head">
							<div class="ea-section-label">Student Progress</div>
							<input
								v-model="searchQuery"
								class="ea-search"
								placeholder="Search by name or email…"
							/>
						</div>

						<div v-if="filteredStudents.length === 0" class="ea-empty-state" style="padding:2rem 0">
							<p>No students match your search.</p>
						</div>

						<div v-else class="ea-table-wrap">
							<table class="ea-table">
								<thead>
									<tr>
										<th class="ea-th-sortable" @click="setSort('full_name')">
											Student {{ sortIcon('full_name') }}
										</th>
										<th>Status</th>
										<th class="ea-th-sortable" @click="setSort('progress_pct')">
											Progress {{ sortIcon('progress_pct') }}
										</th>
										<th>Current Step</th>
										<th class="ea-th-sortable" @click="setSort('last_active')">
											Last Active {{ sortIcon('last_active') }}
										</th>
									</tr>
								</thead>
								<tbody>
									<tr v-for="s in filteredStudents" :key="s.enrollment_name">
										<td>
											<div class="ea-student-cell">
												<div class="ea-avatar-sm">{{ getInitials(s.full_name) }}</div>
												<div>
													<div class="ea-student-name">{{ s.full_name }}</div>
													<div class="ea-student-email">{{ s.email }}</div>
												</div>
											</div>
										</td>
										<td>
											<span :class="['ea-badge', statusClass(s.status, s.progress_pct)]">
												{{ statusLabel(s.status, s.progress_pct) }}
											</span>
										</td>
										<td>
											<div class="ea-prog-cell">
												<div class="ea-prog-bar-wrap">
													<div
														class="ea-prog-bar-fill"
														:style="{
															width: s.progress_pct + '%',
															background: progressBarColor(s.progress_pct, s.status),
														}"
													></div>
												</div>
												<span class="ea-prog-pct">{{ s.progress_pct }}%</span>
											</div>
										</td>
										<td>
											<span class="ea-node-label">{{ s.current_node_label }}</span>
										</td>
										<td>
											<span class="ea-date">{{ formatDate(s.last_active) }}</span>
										</td>
									</tr>
								</tbody>
							</table>
						</div>
					</div>

				</template>
			</template>
		</div>
	</div>
</template>

<style scoped>
.ea-root {
	font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
	background: var(--atp-bg, #f9fafb);
	min-height: 100%;
}

/* Header */
.ea-header {
	height: 48px;
	display: flex;
	align-items: center;
	gap: 1rem;
	padding: 0 1.5rem;
	background: var(--atp-card-bg, #ffffff);
	border-bottom: 1px solid var(--atp-gray-200, #e5e7eb);
}

.ea-back-btn {
	background: none;
	border: none;
	color: #3b82f6;
	font-size: 0.82rem;
	font-weight: 600;
	cursor: pointer;
	padding: 0;
}

.ea-back-btn:hover { text-decoration: underline; }

.ea-title {
	font-size: 0.85rem;
	font-weight: 700;
	letter-spacing: 0.08em;
	text-transform: uppercase;
	color: var(--atp-gray-900, #111827);
}

/* Body */
.ea-body {
	padding: 1.75rem 1.5rem;
	max-width: 1100px;
}

/* Course picker */
.ea-course-picker {
	margin-bottom: 1.5rem;
}

.ea-select {
	padding: 0.5rem 0.85rem;
	border: 1px solid var(--atp-gray-300, #d1d5db);
	border-radius: 6px;
	font-size: 0.875rem;
	color: var(--atp-gray-900, #111827);
	background: var(--atp-card-bg, #ffffff);
	min-width: 320px;
	max-width: 480px;
	appearance: none;
	background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='10' height='10' viewBox='0 0 10 10'%3E%3Cpath fill='%236b7280' d='M5 7L0 2h10z'/%3E%3C/svg%3E");
	background-repeat: no-repeat;
	background-position: right 0.75rem center;
	padding-right: 2rem;
}

.ea-select:focus {
	outline: none;
	border-color: #3b82f6;
	box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.12);
}

/* Course title */
.ea-course-title {
	font-size: 1.15rem;
	font-weight: 700;
	color: var(--atp-gray-900, #111827);
	margin: 0 0 1.25rem 0;
}

/* Stats row */
.ea-stats-row {
	display: flex;
	gap: 1rem;
	flex-wrap: wrap;
	margin-bottom: 1.75rem;
}

.ea-stat-card {
	flex: 1;
	min-width: 100px;
	background: var(--atp-card-bg, #ffffff);
	border: 1px solid var(--atp-gray-200, #e5e7eb);
	border-radius: 8px;
	padding: 1.1rem 1.25rem;
	text-align: center;
}

.ea-stat-completed { border-top: 3px solid #22c55e; }
.ea-stat-inprogress { border-top: 3px solid #f59e0b; }
.ea-stat-notstarted { border-top: 3px solid #e5e7eb; }

.ea-stat-value {
	font-size: 1.75rem;
	font-weight: 700;
	color: var(--atp-blue, #3b82f6);
	line-height: 1;
	margin-bottom: 0.3rem;
}

.ea-stat-label {
	font-size: 0.68rem;
	font-weight: 700;
	text-transform: uppercase;
	letter-spacing: 0.06em;
	color: var(--atp-gray-500, #6b7280);
}

/* Section */
.ea-section {
	background: var(--atp-card-bg, #ffffff);
	border: 1px solid var(--atp-gray-200, #e5e7eb);
	border-radius: 8px;
	padding: 1.25rem;
	margin-bottom: 1.25rem;
}

.ea-section-head {
	display: flex;
	align-items: center;
	justify-content: space-between;
	margin-bottom: 1rem;
	gap: 1rem;
}

.ea-section-label {
	font-size: 0.72rem;
	font-weight: 700;
	letter-spacing: 0.07em;
	text-transform: uppercase;
	color: var(--atp-gray-500, #6b7280);
	margin-bottom: 0.75rem;
	display: flex;
	align-items: center;
	gap: 0.5rem;
}

.ea-section-head .ea-section-label {
	margin-bottom: 0;
}

.ea-attention-count {
	background: #fee2e2;
	color: #ef4444;
	border-radius: 999px;
	padding: 0.1rem 0.5rem;
	font-size: 0.68rem;
}

/* Attention list */
.ea-attention-list {
	display: flex;
	flex-direction: column;
	gap: 0.5rem;
}

.ea-attention-row {
	display: flex;
	align-items: center;
	gap: 0.75rem;
	padding: 0.6rem 0.75rem;
	background: #fffbeb;
	border: 1px solid #fde68a;
	border-radius: 6px;
}

.ea-attention-info {
	flex: 1;
	display: flex;
	flex-direction: column;
}

.ea-attention-reason {
	display: flex;
	align-items: center;
	gap: 0.5rem;
}

.ea-last-active {
	font-size: 0.72rem;
	color: var(--atp-gray-500, #6b7280);
}

/* Badges */
.ea-badge {
	display: inline-block;
	padding: 0.15rem 0.5rem;
	border-radius: 999px;
	font-size: 0.68rem;
	font-weight: 600;
}

.ea-badge-notstarted { background: #f3f4f6; color: #4b5563; }
.ea-badge-inprogress { background: #fef9c3; color: #854d0e; }
.ea-badge-completed  { background: #dcfce7; color: #166534; }
.ea-badge-stalled    { background: #fff7ed; color: #c2410c; }

/* Distribution chart */
.ea-distribution-hint {
	font-size: 0.76rem;
	color: var(--atp-gray-400, #9ca3af);
	margin-bottom: 1rem;
}

.ea-dist-chart {
	display: flex;
	align-items: flex-end;
	gap: 0.35rem;
	overflow-x: auto;
	padding-bottom: 0.25rem;
}

.ea-dist-col {
	display: flex;
	flex-direction: column;
	align-items: center;
	min-width: 60px;
	flex: 1;
	cursor: default;
}

.ea-dist-bar-wrap {
	display: flex;
	flex-direction: column;
	align-items: center;
	height: 100px;
	justify-content: flex-end;
}

.ea-dist-bar {
	width: 32px;
	background: #3b82f6;
	border-radius: 4px 4px 0 0;
	transition: height 0.3s ease;
	min-height: 4px;
}

.ea-dist-count {
	font-size: 0.72rem;
	font-weight: 700;
	color: var(--atp-gray-700, #374151);
	margin-top: 0.25rem;
}

.ea-dist-label {
	font-size: 0.65rem;
	color: var(--atp-gray-500, #6b7280);
	text-align: center;
	margin-top: 0.4rem;
	line-height: 1.3;
	max-width: 64px;
	overflow: hidden;
	text-overflow: ellipsis;
	white-space: nowrap;
}

/* Search */
.ea-search {
	padding: 0.4rem 0.75rem;
	border: 1px solid var(--atp-gray-300, #d1d5db);
	border-radius: 5px;
	font-size: 0.82rem;
	color: var(--atp-gray-900, #111827);
	background: var(--atp-card-bg, #ffffff);
	width: 220px;
}

.ea-search:focus {
	outline: none;
	border-color: #3b82f6;
}

/* Table */
.ea-table-wrap {
	overflow-x: auto;
	border-radius: 6px;
	border: 1px solid var(--atp-gray-200, #e5e7eb);
}

.ea-table {
	width: 100%;
	border-collapse: collapse;
	font-size: 0.84rem;
}

.ea-table th {
	padding: 0.6rem 1rem;
	text-align: left;
	font-size: 0.68rem;
	font-weight: 700;
	text-transform: uppercase;
	letter-spacing: 0.05em;
	color: var(--atp-gray-500, #6b7280);
	background: var(--atp-gray-50, #f9fafb);
	border-bottom: 1px solid var(--atp-gray-200, #e5e7eb);
	white-space: nowrap;
}

.ea-th-sortable {
	cursor: pointer;
	user-select: none;
}

.ea-th-sortable:hover {
	color: var(--atp-gray-900, #111827);
}

.ea-table td {
	padding: 0.65rem 1rem;
	border-bottom: 1px solid var(--atp-gray-100, #f3f4f6);
	color: var(--atp-gray-700, #374151);
}

.ea-table tr:last-child td {
	border-bottom: none;
}

.ea-table tr:hover td {
	background: var(--atp-gray-50, #f9fafb);
}

/* Student cell */
.ea-student-cell {
	display: flex;
	align-items: center;
	gap: 0.6rem;
}

.ea-avatar-sm {
	width: 30px;
	height: 30px;
	border-radius: 50%;
	background: var(--atp-gray-200, #e5e7eb);
	display: flex;
	align-items: center;
	justify-content: center;
	font-size: 0.7rem;
	font-weight: 700;
	color: var(--atp-gray-600, #4b5563);
	flex-shrink: 0;
}

.ea-student-avatar {
	width: 36px;
	height: 36px;
	border-radius: 50%;
	background: var(--atp-gray-200, #e5e7eb);
	display: flex;
	align-items: center;
	justify-content: center;
	font-size: 0.8rem;
	font-weight: 700;
	color: var(--atp-gray-600, #4b5563);
	flex-shrink: 0;
}

.ea-student-name {
	font-weight: 600;
	color: var(--atp-gray-900, #111827);
	font-size: 0.84rem;
}

.ea-student-email {
	font-size: 0.72rem;
	color: var(--atp-gray-400, #9ca3af);
}

/* Progress cell */
.ea-prog-cell {
	display: flex;
	align-items: center;
	gap: 0.5rem;
}

.ea-prog-bar-wrap {
	width: 80px;
	height: 6px;
	background: var(--atp-gray-200, #e5e7eb);
	border-radius: 999px;
	overflow: hidden;
	flex-shrink: 0;
}

.ea-prog-bar-fill {
	height: 100%;
	border-radius: 999px;
	transition: width 0.3s ease;
}

.ea-prog-pct {
	font-size: 0.75rem;
	font-weight: 600;
	color: var(--atp-gray-600, #4b5563);
	min-width: 32px;
}

.ea-node-label {
	font-size: 0.78rem;
	color: var(--atp-gray-600, #4b5563);
}

.ea-date {
	font-size: 0.78rem;
	color: var(--atp-gray-500, #6b7280);
}

/* Empty state */
.ea-empty-state {
	text-align: center;
	padding: 4rem 1rem;
	color: var(--atp-gray-500, #6b7280);
}

.ea-empty-icon {
	font-size: 3rem;
	margin-bottom: 0.75rem;
}

.ea-empty-title {
	font-size: 1rem;
	font-weight: 600;
	color: var(--atp-gray-700, #374151);
	margin: 0 0 0.4rem 0;
}

.ea-empty-sub {
	font-size: 0.85rem;
	color: var(--atp-gray-400, #9ca3af);
	margin: 0;
}

/* Loading */
.ea-loading {
	display: flex;
	align-items: center;
	justify-content: center;
	gap: 0.75rem;
	padding: 4rem 1rem;
	color: var(--atp-gray-500, #6b7280);
	font-size: 0.9rem;
}

.ea-loading-spinner {
	width: 20px;
	height: 20px;
	border: 2px solid var(--atp-gray-200, #e5e7eb);
	border-top-color: #3b82f6;
	border-radius: 50%;
	animation: spin 0.7s linear infinite;
}

@keyframes spin { to { transform: rotate(360deg); } }

/* Error */
.ea-error {
	text-align: center;
	padding: 3rem 1rem;
	color: var(--atp-gray-500, #6b7280);
}

.ea-btn {
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

.ea-btn-outline {
	background: transparent;
	color: #3b82f6;
	border: 1px solid #dbeafe;
}

.ea-btn-outline:hover { background: #eff6ff; }

@media (max-width: 640px) {
	.ea-stats-row { gap: 0.5rem; }
	.ea-stat-card { padding: 0.75rem; }
	.ea-stat-value { font-size: 1.3rem; }
}
</style>
