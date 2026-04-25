<script setup>
import { ref, onMounted, computed } from 'vue';

const enrollments = ref([]);
const loading = ref(true);
const loadError = ref(false);
const userName = ref('');
const userEmail = ref('');
const activeFilter = ref('ongoing'); // 'ongoing' | 'completed'

// ── Data loading ──────────────────────────────────────────────────────────

const init = async () => {
	loadError.value = false;
	loading.value = true;
	try {
		userEmail.value = frappe.session.user;
		const userInfo = frappe.session.user_info || {};
		userName.value = userInfo.full_name || userEmail.value.split('@')[0];

		const result = await frappe.db.get_list('Course Enrollment', {
			filters: { student: frappe.session.user },
			fields: ['name', 'course', 'status', 'progress', 'modified', 'sequence_order'],
			order_by: 'modified desc',
			limit: 50,
		});

		const enriched = await Promise.all(
			result.map(async (e) => {
				try {
					const { message: cd } = await frappe.call({
						method: 'frappe.client.get_value',
						args: { doctype: 'Course', filters: e.course, fieldname: ['title', 'thumbnail', 'description', 'flow_data', 'scene_config'] },
					});
					const progressPct = _calcProgress(e, cd.flow_data);
					let prerequisites = [];
					if (cd.scene_config) {
						try { prerequisites = JSON.parse(cd.scene_config).prerequisites || []; } catch {}
					}
					return {
						...e,
						courseTitle: cd.title || e.course,
						courseThumbnail: cd.thumbnail || '',
						courseDescription: cd.description || '',
						_progressPct: progressPct,
						_prerequisites: prerequisites,
						_seqOrder: e.sequence_order || 0,
					};
				} catch {
					return { ...e, courseTitle: e.course, courseThumbnail: '', courseDescription: '', _progressPct: 0, _prerequisites: [], _seqOrder: 0 };
				}
			}),
		);

		// Compute prerequisite locks
		const completedCourses = new Set(enriched.filter((e) => e.status === 'Completed').map((e) => e.course));
		const courseNameToTitle = Object.fromEntries(enriched.map((e) => [e.course, e.courseTitle]));
		const withPrereqLock = enriched.map((e) => {
			const unmet = (e._prerequisites || []).filter((p) => !completedCourses.has(p));
			return {
				...e,
				_prereqLocked: unmet.length > 0,
				_unmetPrereqs: unmet.map((p) => courseNameToTitle[p] || p),
			};
		});

		// Compute sequence locks: within sequenced courses, each step blocks the next until complete
		const seqMap = new Map(); // sequence_order → enrollment
		withPrereqLock.forEach((e) => {
			if (e._seqOrder > 0) seqMap.set(e._seqOrder, e);
		});
		const seqKeys = Array.from(seqMap.keys()).sort((a, b) => a - b);
		let seqBlockedAfter = false;
		const seqLocked = new Set();
		for (const k of seqKeys) {
			const e = seqMap.get(k);
			if (seqBlockedAfter) seqLocked.add(e.name);
			if (e.status !== 'Completed') seqBlockedAfter = true;
		}

		const withLocked = withPrereqLock.map((e) => ({
			...e,
			_locked: e._prereqLocked || seqLocked.has(e.name),
		}));

		enrollments.value = withLocked;
	} catch (err) {
		console.error('StudentDashboard: load error', err);
		loadError.value = true;
	} finally {
		loading.value = false;
	}
};

const _calcProgress = (enrollment, flowDataStr) => {
	if (enrollment.status === 'Completed') return 100;
	if (!enrollment.progress || !flowDataStr) return 0;
	try {
		const flow = JSON.parse(flowDataStr);
		const progress = JSON.parse(enrollment.progress);
		const total = flow.nodes?.length || 0;
		if (total === 0) return 0;
		const idx = flow.nodes.findIndex((n) => n.id === progress.currentNodeId);
		return idx < 0 ? 0 : Math.round((idx / total) * 100);
	} catch {
		return 0;
	}
};

// ── Computed ──────────────────────────────────────────────────────────────

const ongoingCourses = computed(() =>
	enrollments.value.filter((e) => e.status !== 'Completed'),
);

const completedCourses = computed(() =>
	enrollments.value.filter((e) => e.status === 'Completed'),
);

const sortEnrollments = (list) => {
	const sequenced = list.filter((e) => e._seqOrder > 0).sort((a, b) => a._seqOrder - b._seqOrder);
	const unsequenced = list.filter((e) => !e._seqOrder);
	return [...sequenced, ...unsequenced];
};

const visibleCourses = computed(() =>
	sortEnrollments(activeFilter.value === 'completed' ? completedCourses.value : ongoingCourses.value),
);

const completedCount = computed(() => completedCourses.value.length);

const getInitials = (name) => {
	if (!name) return 'U';
	return name
		.split(' ')
		.map((w) => w[0])
		.join('')
		.toUpperCase()
		.slice(0, 2);
};

const getCTA = (e) => {
	if (e._locked) return '🔒 Locked';
	if (e.status === 'Completed') return 'Review';
	if (e.progress) return 'Continue';
	return 'Start';
};

const getStatusLabel = (e) => {
	if (e._locked) return 'Locked';
	if (e.status === 'Completed') return 'Completed';
	if (e.progress) return 'In Progress';
	return 'Not Started';
};

const getStatusClass = (e) => {
	if (e._locked) return 'atp-badge-locked';
	if (e.status === 'Completed') return 'atp-badge-completed';
	if (e.progress) return 'atp-badge-inprogress';
	return 'atp-badge-notstarted';
};

const getThumbEmoji = (title) => {
	const t = (title || '').toLowerCase();
	if (t.includes('negotiat')) return '🤝';
	if (t.includes('robot') || t.includes('vex')) return '🤖';
	if (t.includes('minecraft')) return '🎮';
	if (t.includes('code') || t.includes('program')) return '💻';
	if (t.includes('science') || t.includes('lab')) return '🔬';
	return '📚';
};

// ── Actions ───────────────────────────────────────────────────────────────

const openCourse = (enrollment) => {
	if (enrollment._locked) {
		const prereqList = enrollment._unmetPrereqs.join(', ');
		frappe.show_alert({ message: `Complete first: ${prereqList}`, indicator: 'orange' }, 4);
		return;
	}
	frappe.set_route('course_player', enrollment.name);
};

const joinActivity = () => {
	frappe.show_alert({ message: 'Join Activity — coming soon', indicator: 'blue' });
};

const goSettings = () => {
	frappe.set_route('atp_settings');
};

const logout = () => {
	frappe.call({ method: 'logout' }).then(() => {
		window.location.href = '/login';
	});
};

onMounted(() => {
	init();
});

defineExpose({ init });
</script>

<template>
	<div class="atp-dashboard">
		<!-- Page header (matches screenshot all-caps style) -->
		<div class="dash-header">
			<span class="dash-title">STUDENT DASHBOARD</span>
		</div>

		<div class="dash-body">
			<div v-if="loading" class="loading-state">Loading your courses…</div>

			<div v-else-if="loadError" class="error-state">
				<div class="error-icon">⚠️</div>
				<p>Could not load your courses.</p>
				<button class="atp-btn atp-btn-primary" style="margin-top:0.75rem" @click="init">Retry</button>
			</div>

			<div v-else class="dash-content">
				<!-- Left: course grid -->
				<div class="dash-main">
					<!-- Tab bar -->
					<div class="atp-tabs">
						<div
							class="atp-tab"
							:class="{ active: activeFilter === 'ongoing' }"
							@click="activeFilter = 'ongoing'"
						>
							Ongoing Activity
						</div>
						<div
							class="atp-tab"
							:class="{ active: activeFilter === 'completed' }"
							@click="activeFilter = 'completed'"
						>
							Completed ({{ completedCount }})
						</div>
					</div>

					<!-- Empty state -->
					<div v-if="visibleCourses.length === 0" class="empty-state">
						<div class="empty-icon">📋</div>
						<p v-if="activeFilter === 'ongoing'">No courses assigned yet. Check back with your educator.</p>
						<p v-else>You haven't completed any courses yet. Keep going!</p>
					</div>

					<!-- Course card grid -->
					<div v-else class="atp-card-grid">
						<div
							v-for="e in visibleCourses"
							:key="e.name"
							class="atp-course-card"
							:class="{ 'atp-course-card-locked': e._locked }"
							@click="openCourse(e)"
						>
							<!-- Thumbnail -->
							<div class="card-thumb">
								<img
									v-if="e.courseThumbnail"
									:src="e.courseThumbnail"
									:alt="e.courseTitle"
								/>
								<span v-else class="thumb-emoji">{{ getThumbEmoji(e.courseTitle) }}</span>
								<div v-if="e._locked" class="card-lock-overlay">🔒</div>
							</div>

							<!-- Card body -->
							<div class="card-body">
								<div class="card-title-row">
									<p class="card-title">{{ e.courseTitle }}</p>
									<span v-if="e._seqOrder > 0" class="card-step-badge">Step {{ e._seqOrder }}</span>
								</div>
								<div v-if="e._locked && e._unmetPrereqs && e._unmetPrereqs.length" class="card-prereq-hint">
									Complete first: {{ e._unmetPrereqs.join(', ') }}
								</div>
								<div class="card-meta">
									<span class="atp-badge" :class="getStatusClass(e)">
										{{ getStatusLabel(e) }}
									</span>
									<span class="progress-pct">{{ e._progressPct }}%</span>
								</div>
								<div class="atp-progress-bar">
									<div class="fill" :style="{ width: e._progressPct + '%' }"></div>
								</div>
								<div class="card-cta">
									<button class="atp-btn atp-btn-primary card-action-btn" :disabled="e._locked">
										{{ e._locked ? '🔒 Locked' : (getCTA(e) + ' →') }}
									</button>
								</div>
							</div>
						</div>
					</div>
				</div>

				<!-- Right: profile panel -->
				<div class="dash-profile">
					<div class="atp-avatar">
						<span>{{ getInitials(userName) }}</span>
					</div>
					<div class="atp-profile-name">{{ userName }}</div>
					<div class="atp-profile-links">
						<a @click.prevent="activeFilter = 'completed'">Completed Activities</a>
						<a @click.prevent="goSettings">Settings</a>
						<a @click.prevent="logout">Sign Out</a>
					</div>
				</div>
			</div>
		</div>
	</div>
</template>

<style scoped>
.atp-dashboard {
	font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
	background: var(--atp-bg, #f9fafb);
	min-height: 100%;
}

.dash-header {
	display: flex;
	align-items: center;
	height: 48px;
	padding: 0 1.5rem;
	background: var(--atp-card-bg, #ffffff);
	border-bottom: 1px solid var(--atp-gray-200, #e5e7eb);
}

.dash-title {
	font-size: 0.85rem;
	font-weight: 700;
	letter-spacing: 0.08em;
	text-transform: uppercase;
	color: var(--atp-gray-900, #111827);
}

.dash-body {
	padding: 1.75rem 1.5rem;
}

.loading-state {
	text-align: center;
	padding: 3rem;
	color: var(--atp-gray-500, #6b7280);
	font-size: 0.9rem;
}

.error-state {
	text-align: center;
	padding: 3rem 1rem;
	color: var(--atp-gray-500, #6b7280);
	font-size: 0.9rem;
}

.error-icon {
	font-size: 2rem;
	margin-bottom: 0.5rem;
}

.dash-content {
	display: flex;
	gap: 2rem;
	align-items: flex-start;
}

.dash-main {
	flex: 1;
	min-width: 0;
}

/* Profile */
.dash-profile {
	width: 180px;
	flex-shrink: 0;
	padding-top: 0.5rem;
}

/* Tabs */
.atp-tabs {
	display: flex;
	border-bottom: 2px solid var(--atp-gray-200, #e5e7eb);
	margin-bottom: 1.25rem;
}

.atp-tab {
	padding: 0.5rem 1rem;
	font-size: 0.82rem;
	font-weight: 600;
	color: var(--atp-gray-500, #6b7280);
	cursor: pointer;
	border-bottom: 2px solid transparent;
	margin-bottom: -2px;
	transition: color 0.15s, border-color 0.15s;
	user-select: none;
}

.atp-tab.active {
	color: var(--atp-blue, #3b82f6);
	border-bottom-color: var(--atp-blue, #3b82f6);
}

/* Empty state */
.empty-state {
	text-align: center;
	padding: 3rem 1rem;
	color: var(--atp-gray-500, #6b7280);
}

.empty-icon {
	font-size: 2.5rem;
	margin-bottom: 0.75rem;
}

/* Card grid */
.atp-card-grid {
	display: grid;
	grid-template-columns: repeat(auto-fill, minmax(190px, 1fr));
	gap: 1.25rem;
}

.atp-course-card {
	background: var(--atp-card-bg, #ffffff);
	border: 1px solid var(--atp-gray-200, #e5e7eb);
	border-radius: 6px;
	overflow: hidden;
	cursor: pointer;
	transition: box-shadow 0.15s ease, border-color 0.15s ease;
}

.atp-course-card:hover {
	box-shadow: 0 4px 8px rgba(0,0,0,0.08);
	border-color: var(--atp-blue-muted, #dbeafe);
}

.card-thumb {
	width: 100%;
	aspect-ratio: 4 / 3;
	background: var(--atp-gray-100, #f3f4f6);
	display: flex;
	align-items: center;
	justify-content: center;
	overflow: hidden;
}

.card-thumb img {
	width: 100%;
	height: 100%;
	object-fit: cover;
}

.thumb-emoji {
	font-size: 3rem;
}

.card-body {
	padding: 0.75rem;
}

.card-title-row {
	display: flex;
	align-items: flex-start;
	justify-content: space-between;
	gap: 0.35rem;
	margin-bottom: 0.5rem;
}

.card-title {
	font-size: 0.82rem;
	font-weight: 600;
	color: var(--atp-gray-900, #111827);
	margin: 0;
	line-height: 1.35;
	flex: 1;
	min-width: 0;
}

.card-step-badge {
	font-size: 0.62rem;
	font-weight: 700;
	background: #eff6ff;
	color: #3b82f6;
	border: 1px solid #dbeafe;
	border-radius: 3px;
	padding: 0.1rem 0.35rem;
	white-space: nowrap;
	flex-shrink: 0;
	margin-top: 0.05rem;
}

.card-meta {
	display: flex;
	align-items: center;
	justify-content: space-between;
	margin-bottom: 0.4rem;
}

.progress-pct {
	font-size: 0.7rem;
	color: var(--atp-gray-500, #6b7280);
	font-weight: 600;
}

/* Badges */
.atp-badge {
	display: inline-block;
	padding: 0.15rem 0.5rem;
	border-radius: 999px;
	font-size: 0.68rem;
	font-weight: 600;
}

.atp-badge-notstarted { background: var(--atp-gray-100, #f3f4f6); color: var(--atp-gray-600, #4b5563); }
.atp-badge-inprogress { background: var(--atp-badge-inprogress-bg, #fef9c3); color: var(--atp-badge-inprogress-fg, #854d0e); }
.atp-badge-completed  { background: var(--atp-badge-completed-bg, #dcfce7); color: var(--atp-badge-completed-fg, #166534); }
.atp-badge-locked     { background: #f3f4f6; color: #9ca3af; }

/* Locked card state */
.atp-course-card-locked {
	opacity: 0.75;
}

.atp-course-card-locked:hover {
	cursor: default;
	box-shadow: none;
	border-color: var(--atp-gray-200, #e5e7eb);
}

.card-thumb {
	position: relative;
}

.card-lock-overlay {
	position: absolute;
	inset: 0;
	background: rgba(255,255,255,0.55);
	display: flex;
	align-items: center;
	justify-content: center;
	font-size: 1.8rem;
}

.card-prereq-hint {
	font-size: 0.68rem;
	color: var(--atp-gray-500, #6b7280);
	margin-bottom: 0.35rem;
	line-height: 1.4;
}

.card-action-btn:disabled {
	opacity: 0.6;
	cursor: not-allowed;
	background: #9ca3af;
}

/* Progress bar */
.atp-progress-bar {
	height: 4px;
	background: var(--atp-gray-200, #e5e7eb);
	border-radius: 999px;
	overflow: hidden;
	margin-bottom: 0.6rem;
}

.atp-progress-bar .fill {
	height: 100%;
	background: #3b82f6;
	border-radius: 999px;
	transition: width 0.3s ease;
}

.card-cta {
	text-align: right;
}

.card-action-btn {
	padding: 0.3rem 0.7rem;
	font-size: 0.75rem;
	background: #3b82f6;
	color: #ffffff;
	border: none;
	border-radius: 5px;
	font-weight: 600;
	cursor: pointer;
	transition: background 0.15s;
}

.card-action-btn:hover {
	background: #2563eb;
}

/* Profile panel */
.atp-avatar {
	width: 60px;
	height: 60px;
	border-radius: 50%;
	background: var(--atp-gray-200, #e5e7eb);
	display: flex;
	align-items: center;
	justify-content: center;
	font-size: 1.3rem;
	font-weight: 700;
	color: var(--atp-gray-600, #4b5563);
	margin-bottom: 0.6rem;
}

.atp-profile-name {
	font-weight: 700;
	font-size: 0.95rem;
	color: var(--atp-gray-900, #111827);
	margin-bottom: 0.75rem;
}

.atp-profile-links {
	display: flex;
	flex-direction: column;
	gap: 0.3rem;
}

.atp-profile-links a {
	display: block;
	color: #3b82f6;
	font-size: 0.85rem;
	text-decoration: none;
	cursor: pointer;
}

.atp-profile-links a:hover {
	text-decoration: underline;
}

.atp-profile-link-soon {
	display: block;
	font-size: 0.85rem;
	color: var(--atp-gray-400, #9ca3af);
	cursor: default;
	user-select: none;
}

@media (max-width: 640px) {
	.dash-profile {
		display: none;
	}

	.atp-card-grid {
		grid-template-columns: repeat(2, 1fr);
	}
}
</style>
