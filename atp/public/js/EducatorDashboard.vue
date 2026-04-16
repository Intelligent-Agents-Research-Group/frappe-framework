<script setup>
import { ref, computed, onMounted, nextTick } from 'vue';

const courses = ref([]);
const loading = ref(true);
const loadError = ref(false);
const showCreateModal = ref(false);
const newCourseTitle = ref('');
const creating = ref(false);
const titleInputRef = ref(null);
const userName = ref('');
const userRoles = ref([]);

const isAdmin = computed(() =>
	userRoles.value.includes('Administrator') ||
	userRoles.value.includes('System Manager')
);

onMounted(async () => {
	userName.value = frappe.boot?.full_name || frappe.session?.user || '';
	userRoles.value = frappe.user_roles || frappe.boot?.user?.roles || [];
	await loadCourses();
});

async function loadCourses() {
	loading.value = true;
	loadError.value = false;
	try {
		const r = await frappe.call({ method: 'atp.atp.api.get_educator_courses' });
		courses.value = r.message || [];
	} catch {
		loadError.value = true;
	} finally {
		loading.value = false;
	}
}

function courseEmoji(title) {
	const t = (title || '').toLowerCase();
	if (t.includes('negotiat')) return '🤝';
	if (t.includes('collab')) return '👥';
	if (t.includes('robot') || t.includes('vex')) return '🤖';
	if (t.includes('code') || t.includes('program')) return '💻';
	return '📚';
}

function openBuilder(name) {
	frappe.set_route('course_builder', name);
}

async function openCreateModal() {
	newCourseTitle.value = '';
	showCreateModal.value = true;
	await nextTick();
	titleInputRef.value?.focus();
}

async function createCourse() {
	const title = newCourseTitle.value.trim();
	if (!title || creating.value) return;
	creating.value = true;
	try {
		const doc = await frappe.db.insert({ doctype: 'Course', title });
		showCreateModal.value = false;
		frappe.set_route('course_builder', doc.name);
	} catch (e) {
		frappe.show_alert({ message: e?.message || 'Failed to create course.', indicator: 'red' });
	} finally {
		creating.value = false;
	}
}

function logout() {
	frappe.call({ method: 'logout' }).then(() => {
		window.location.href = '/login';
	});
}

function openAdminPanel() {
	window.location.href = '/desk';
}

const goToEnrollmentManager = () => frappe.set_route('enrollment_manager');
const goToAnalytics = () => frappe.set_route('educator_analytics');
const goToSettings = () => frappe.set_route('atp_settings');
</script>

<template>
  <div class="atp-page">

    <!-- ── Header ───────────────────────────────────────────────── -->
    <div class="atp-page-header">
      <h1 class="page-title">Educator Dashboard</h1>
      <div style="flex:1" />
      <span
        v-if="isAdmin"
        class="atp-badge atp-badge-notstarted"
        style="font-size:0.68rem;letter-spacing:0.06em;margin-right:0.25rem"
      >Admin</span>
      <span style="font-size:0.82rem;color:var(--atp-gray-600);margin-right:0.5rem">{{ userName }}</span>
      <button class="atp-btn atp-btn-outline" @click="logout">Sign Out</button>
    </div>

    <!-- ── Body ─────────────────────────────────────────────────── -->
    <div class="atp-page-body">

      <!-- Courses section -->
      <div class="atp-edu-section">
        <div class="atp-edu-section-head">
          <span class="atp-section-label">Your Courses</span>
          <button class="atp-btn atp-btn-primary" @click="openCreateModal">+ Create Course</button>
        </div>

        <div v-if="loading" class="atp-edu-loading">Loading…</div>

        <div v-else-if="loadError" class="atp-edu-empty">
          <div class="atp-edu-empty-icon">⚠️</div>
          <p class="atp-edu-empty-title">Could not load courses</p>
          <p class="atp-edu-empty-msg">Check your connection and try again.</p>
          <button class="atp-btn atp-btn-primary" @click="loadCourses">Retry</button>
        </div>

        <div v-else-if="courses.length === 0" class="atp-edu-empty">
          <div class="atp-edu-empty-icon">📚</div>
          <p class="atp-edu-empty-title">No courses yet</p>
          <p class="atp-edu-empty-msg">Create your first course to get started.</p>
          <button class="atp-btn atp-btn-primary" @click="openCreateModal">+ Create Course</button>
        </div>

        <div v-else class="atp-card-grid">
          <div
            v-for="course in courses"
            :key="course.name"
            class="atp-course-card"
            @click="openBuilder(course.name)"
          >
            <div class="card-thumb">
              <img v-if="course.thumbnail" :src="course.thumbnail" alt="" />
              <span v-else>{{ courseEmoji(course.title) }}</span>
            </div>
            <div class="card-body">
              <p class="card-title">{{ course.title }}</p>
              <div class="card-meta">
                <span
                  :class="['atp-badge',
                    course.is_published ? 'atp-badge-completed' : 'atp-badge-notstarted']"
                >{{ course.is_published ? 'Published' : 'Draft' }}</span>
                <span
                  v-if="course.enrollment_count > 0"
                  style="font-size:0.72rem;color:var(--atp-gray-500)"
                >{{ course.enrollment_count }} student{{ course.enrollment_count !== 1 ? 's' : '' }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Quick Actions -->
      <div class="atp-edu-section">
        <div class="atp-section-label" style="margin-bottom:0.75rem">Quick Actions</div>
        <div class="atp-edu-actions">
          <button class="atp-edu-action-card" @click="goToEnrollmentManager">
            <span class="atp-edu-action-icon">👥</span>
            <span class="atp-edu-action-label">Manage Students</span>
          </button>
          <button class="atp-edu-action-card" @click="goToAnalytics">
            <span class="atp-edu-action-icon">📊</span>
            <span class="atp-edu-action-label">Analytics</span>
          </button>
          <button class="atp-edu-action-card" @click="goToSettings">
            <span class="atp-edu-action-icon">⚙️</span>
            <span class="atp-edu-action-label">Settings</span>
          </button>
          <button v-if="isAdmin" class="atp-edu-action-card" @click="openAdminPanel">
            <span class="atp-edu-action-icon">🔧</span>
            <span class="atp-edu-action-label">Admin Panel</span>
          </button>
        </div>
      </div>

    </div><!-- /atp-page-body -->

    <!-- ── Create Course Modal ───────────────────────────────────── -->
    <div v-if="showCreateModal" class="atp-modal-overlay" @click.self="showCreateModal = false">
      <div class="atp-modal">
        <div class="atp-modal-header">
          <span>New Course</span>
          <button class="atp-modal-close" @click="showCreateModal = false">&times;</button>
        </div>
        <div class="atp-modal-body">
          <div class="atp-form-field">
            <label>Course Title</label>
            <input
              ref="titleInputRef"
              v-model="newCourseTitle"
              class="atp-input"
              placeholder="e.g. Introduction to Negotiation"
              :disabled="creating"
              @keydown.enter="createCourse"
            />
          </div>
        </div>
        <div class="atp-modal-footer">
          <button class="atp-btn atp-btn-outline" @click="showCreateModal = false">Cancel</button>
          <button
            class="atp-btn atp-btn-primary"
            :disabled="!newCourseTitle.trim() || creating"
            @click="createCourse"
          >{{ creating ? 'Creating…' : 'Create & Open Builder' }}</button>
        </div>
      </div>
    </div>

  </div>
</template>
