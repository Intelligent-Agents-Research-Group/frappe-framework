import { createApp } from 'vue';
import EnrollmentManager from './EnrollmentManager.vue';

window.mountEnrollmentManager = function (selector) {
	createApp(EnrollmentManager).mount(selector);
};
