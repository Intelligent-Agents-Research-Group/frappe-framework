import { createApp } from 'vue';
import StudentDashboard from './StudentDashboard.vue';

window.mountStudentDashboard = function (selector) {
	const instance = createApp(StudentDashboard).mount(selector);
	window.refreshStudentDashboard = () => instance.init();
};
