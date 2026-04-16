import { createApp } from 'vue';
import ATPSettings from './ATPSettings.vue';

window.mountATPSettings = function (selector) {
	createApp(ATPSettings).mount(selector);
};
