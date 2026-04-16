import { createApp } from 'vue';
import EducatorDashboard from './EducatorDashboard.vue';

window.mountEducatorDashboard = function (selector) {
	createApp(EducatorDashboard).mount(selector);
};
