import { createApp } from 'vue';
import EducatorAnalytics from './EducatorAnalytics.vue';

window.mountEducatorAnalytics = function (selector) {
	createApp(EducatorAnalytics).mount(selector);
};
