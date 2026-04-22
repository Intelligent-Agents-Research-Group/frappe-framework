import { createApp } from "vue";
import ATPSession from "./ATPSession.vue";

window.mountATPSession = function (selector, enrollmentName, scenarioId) {
	createApp(ATPSession, { enrollmentName: enrollmentName || null, scenarioId: scenarioId || null }).mount(selector);
};
