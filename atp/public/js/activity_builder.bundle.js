
import { createApp } from 'vue';
import AppBuilder from './AppBuilder.vue';

window.mountActivityBuilder = function (selector, courseName) {
    if (courseName) {
        window.cur_course = courseName;
    }
    const app = createApp(AppBuilder, { courseName });
    app.mount(selector);
}
