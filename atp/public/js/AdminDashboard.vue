<script setup>
import { ref, onMounted, nextTick, computed } from 'vue';

const userName = ref('');
const stats = ref({ students: 0, educators: 0, courses: 0, enrollments: 0 });
const users = ref([]);
const courses = ref([]);
const loadingUsers = ref(true);
const loadingCourses = ref(true);
const loadingStats = ref(true);

// Add user modal
const showAddModal = ref(false);
const addRole = ref('ATP Student');
const addEmail = ref('');
const addFullName = ref('');
const addPassword = ref('');
const adding = ref(false);
const addEmailRef = ref(null);

onMounted(async () => {
	userName.value = frappe.boot?.full_name || frappe.session?.user || '';
	await Promise.all([loadStats(), loadUsers(), loadCourses()]);
});

async function loadStats() {
	loadingStats.value = true;
	try {
		const r = await frappe.call({ method: 'atp.atp.api.get_admin_stats' });
		stats.value = r.message || stats.value;
	} catch {
		// silently show zeros
	} finally {
		loadingStats.value = false;
	}
}

async function loadUsers() {
	loadingUsers.value = true;
	try {
		const r = await frappe.call({ method: 'atp.atp.api.get_all_users' });
		users.value = r.message || [];
	} catch {
		users.value = [];
	} finally {
		loadingUsers.value = false;
	}
}

async function loadCourses() {
	loadingCourses.value = true;
	try {
		const r = await frappe.call({ method: 'atp.atp.api.get_all_courses_admin' });
		courses.value = r.message || [];
	} catch {
		courses.value = [];
	} finally {
		loadingCourses.value = false;
	}
}

function openAddModal(role) {
	addRole.value = role;
	addEmail.value = '';
	addFullName.value = '';
	addPassword.value = '';
	showAddModal.value = true;
	nextTick(() => addEmailRef.value?.focus());
}

async function addUser() {
	const email = addEmail.value.trim();
	const full_name = addFullName.value.trim();
	const password = addPassword.value;
	if (!email || !full_name || !password) {
		frappe.show_alert({ message: 'Please fill in all fields.', indicator: 'orange' });
		return;
	}
	adding.value = true;
	try {
		await frappe.call({
			method: 'atp.atp.api.add_atp_user',
			args: { email, full_name, role: addRole.value, password },
		});
		frappe.show_alert({ message: `${addRole.value === 'ATP Student' ? 'Student' : 'Educator'} added.`, indicator: 'green' }, 3);
		showAddModal.value = false;
		await Promise.all([loadUsers(), loadStats()]);
	} catch (e) {
		frappe.show_alert({ message: e?.message || 'Failed to add user.', indicator: 'red' }, 5);
	} finally {
		adding.value = false;
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

function logout() {
	frappe.call({ method: 'logout' }).then(() => { window.location.href = '/login'; });
}

const userSearch = ref('');

const filteredUsers = computed(() => {
	const q = userSearch.value.toLowerCase().trim();
	if (!q) return users.value;
	return users.value.filter(u =>
		(u.full_name || '').toLowerCase().includes(q) || u.email.toLowerCase().includes(q),
	);
});
</script>

<template>
  <div class="atp-page">

    <!-- Header -->
    <div class="atp-page-header">
      <h1 class="page-title">ATP Admin</h1>
      <div style="flex:1" />
      <span style="font-size:0.82rem;color:var(--atp-gray-600);margin-right:0.5rem">{{ userName }}</span>
      <button class="atp-btn atp-btn-outline" @click="logout">Sign Out</button>
    </div>

    <div class="atp-page-body">

      <!-- Stats row -->
      <div class="admin-stats-row">
        <div class="stat-card">
          <div class="stat-value">{{ loadingStats ? '…' : stats.students }}</div>
          <div class="stat-label">Students</div>
        </div>
        <div class="stat-card">
          <div class="stat-value">{{ loadingStats ? '…' : stats.educators }}</div>
          <div class="stat-label">Educators</div>
        </div>
        <div class="stat-card">
          <div class="stat-value">{{ loadingStats ? '…' : stats.courses }}</div>
          <div class="stat-label">Courses</div>
        </div>
        <div class="stat-card">
          <div class="stat-value">{{ loadingStats ? '…' : stats.enrollments }}</div>
          <div class="stat-label">Enrollments</div>
        </div>
      </div>

      <!-- Users section -->
      <div class="atp-edu-section">
        <div class="atp-edu-section-head">
          <span class="atp-section-label">Users</span>
          <div style="display:flex;gap:0.5rem">
            <button class="atp-btn atp-btn-outline" @click="openAddModal('ATP Student')">+ Add Student</button>
            <button class="atp-btn atp-btn-primary" @click="openAddModal('ATP Educator')">+ Add Educator</button>
          </div>
        </div>

        <div v-if="loadingUsers" class="atp-edu-loading">Loading…</div>
        <div v-else-if="users.length === 0" class="atp-edu-empty">
          <div class="atp-edu-empty-icon">👥</div>
          <p class="atp-edu-empty-title">No ATP users yet</p>
        </div>
        <div v-else>
          <input
            v-model="userSearch"
            class="atp-input admin-search"
            type="search"
            placeholder="Search name or email…"
            style="margin-bottom:0.75rem"
          />
          <div v-if="filteredUsers.length === 0" class="atp-edu-loading">No users match your search.</div>
          <div v-else class="admin-table-wrap">
          <table class="admin-table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Email</th>
                <th>Role</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="u in filteredUsers" :key="u.email">
                <td>{{ u.full_name || '—' }}</td>
                <td class="table-email">{{ u.email }}</td>
                <td>
                  <span
                    class="atp-badge"
                    :class="u.role === 'ATP Student' ? 'atp-badge-inprogress' : 'atp-badge-completed'"
                  >{{ u.role }}</span>
                </td>
                <td>
                  <span
                    class="atp-badge"
                    :class="u.enabled ? 'atp-badge-completed' : 'atp-badge-notstarted'"
                  >{{ u.enabled ? 'Active' : 'Disabled' }}</span>
                </td>
              </tr>
            </tbody>
          </table>
          </div>
        </div>
      </div>

      <!-- All Courses section -->
      <div class="atp-edu-section">
        <div class="atp-edu-section-head">
          <span class="atp-section-label">All Courses</span>
        </div>

        <div v-if="loadingCourses" class="atp-edu-loading">Loading…</div>
        <div v-else-if="courses.length === 0" class="atp-edu-empty">
          <div class="atp-edu-empty-icon">📚</div>
          <p class="atp-edu-empty-title">No courses yet</p>
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
              <div class="card-meta" style="display:flex;align-items:center;justify-content:space-between">
                <span
                  :class="['atp-badge', course.is_published ? 'atp-badge-completed' : 'atp-badge-notstarted']"
                >{{ course.is_published ? 'Published' : 'Draft' }}</span>
                <span v-if="course.enrollment_count > 0" style="font-size:0.72rem;color:var(--atp-gray-500)">
                  {{ course.enrollment_count }} student{{ course.enrollment_count !== 1 ? 's' : '' }}
                </span>
              </div>
              <p class="card-owner">{{ course.owner_name || course.owner }}</p>
            </div>
          </div>
        </div>
      </div>

      <!-- Quick Links -->
      <div class="atp-edu-section">
        <div class="atp-section-label" style="margin-bottom:0.75rem">Quick Links</div>
        <div class="atp-edu-actions">
          <button class="atp-edu-action-card" @click="frappe.set_route('enrollment_manager')">
            <span class="atp-edu-action-icon">👥</span>
            <span class="atp-edu-action-label">Enrollment Manager</span>
          </button>
          <button class="atp-edu-action-card" @click="frappe.set_route('atp_settings')">
            <span class="atp-edu-action-icon">⚙️</span>
            <span class="atp-edu-action-label">ATP Settings</span>
          </button>
          <button class="atp-edu-action-card" @click="window.location.href='/desk'">
            <span class="atp-edu-action-icon">🔧</span>
            <span class="atp-edu-action-label">Frappe Desk</span>
          </button>
        </div>
      </div>

    </div>

    <!-- Add User Modal -->
    <div v-if="showAddModal" class="atp-modal-overlay" @click.self="showAddModal = false">
      <div class="atp-modal">
        <div class="atp-modal-header">
          <span>Add {{ addRole === 'ATP Student' ? 'Student' : 'Educator' }}</span>
          <button class="atp-modal-close" @click="showAddModal = false">&times;</button>
        </div>
        <div class="atp-modal-body">
          <div class="atp-form-field">
            <label>Email</label>
            <input
              ref="addEmailRef"
              v-model="addEmail"
              class="atp-input"
              type="email"
              placeholder="user@example.com"
              :disabled="adding"
            />
          </div>
          <div class="atp-form-field">
            <label>Full Name</label>
            <input
              v-model="addFullName"
              class="atp-input"
              placeholder="Jane Doe"
              :disabled="adding"
            />
          </div>
          <div class="atp-form-field">
            <label>Password</label>
            <input
              v-model="addPassword"
              class="atp-input"
              type="password"
              placeholder="Temporary password"
              :disabled="adding"
              @keydown.enter="addUser"
            />
          </div>
        </div>
        <div class="atp-modal-footer">
          <button class="atp-btn atp-btn-outline" @click="showAddModal = false">Cancel</button>
          <button
            class="atp-btn atp-btn-primary"
            :disabled="!addEmail.trim() || !addFullName.trim() || !addPassword || adding"
            @click="addUser"
          >{{ adding ? 'Adding…' : 'Add User' }}</button>
        </div>
      </div>
    </div>

  </div>
</template>

<style scoped>
/* Stats */
.admin-stats-row {
  display: flex;
  gap: 1rem;
  margin-bottom: 1.5rem;
  flex-wrap: wrap;
}

.stat-card {
  flex: 1;
  min-width: 120px;
  background: var(--atp-card-bg, #ffffff);
  border: 1px solid var(--atp-gray-200, #e5e7eb);
  border-radius: 8px;
  padding: 1.25rem 1.5rem;
  text-align: center;
}

.stat-value {
  font-size: 2rem;
  font-weight: 700;
  color: var(--atp-blue, #3b82f6);
  line-height: 1;
  margin-bottom: 0.35rem;
}

.stat-label {
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--atp-gray-500, #6b7280);
}

/* Table */
.admin-table-wrap {
  overflow-x: auto;
  border-radius: 6px;
  border: 1px solid var(--atp-gray-200, #e5e7eb);
}

.admin-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.84rem;
}

.admin-table th {
  padding: 0.6rem 1rem;
  text-align: left;
  font-size: 0.7rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--atp-gray-500, #6b7280);
  background: var(--atp-gray-50, #f9fafb);
  border-bottom: 1px solid var(--atp-gray-200, #e5e7eb);
}

.admin-table td {
  padding: 0.65rem 1rem;
  border-bottom: 1px solid var(--atp-gray-100, #f3f4f6);
  color: var(--atp-gray-900, #111827);
}

.admin-table tr:last-child td {
  border-bottom: none;
}

.table-email {
  color: var(--atp-gray-500, #6b7280);
  font-size: 0.8rem;
}

/* Course cards */
.card-owner {
  font-size: 0.7rem;
  color: var(--atp-gray-400, #9ca3af);
  margin: 0.3rem 0 0 0;
}

/* Search input */
.atp-input {
  padding: 0.4rem 0.7rem;
  border: 1px solid var(--atp-gray-300, #d1d5db);
  border-radius: 5px;
  font-size: 0.875rem;
  color: var(--atp-gray-900, #111827);
  background: #ffffff;
  box-sizing: border-box;
  transition: border-color 0.15s, box-shadow 0.15s;
}

.atp-input:focus {
  outline: none;
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.12);
}

.admin-search {
  width: 100%;
  max-width: 320px;
}
</style>
