import { createApp } from 'vue';
import AdminDashboard from './AdminDashboard.vue';

window.mountAdminDashboard = function (selector) {
	createApp(AdminDashboard).mount(selector);
};
