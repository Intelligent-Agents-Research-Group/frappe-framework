
import { createApp } from 'vue';
import AppPlayer from './AppPlayer.vue';

window.mountCoursePlayer = function (selector, enrollmentName) {
    if (enrollmentName) {
        window.cur_enrollment = enrollmentName;
    }
    createApp(AppPlayer, { enrollmentName }).mount(selector);
}
