frappe.pages['course_builder'].on_page_load = function (wrapper) {
    var page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'Course Builder',
        single_column: true
    });

    let courseName = null;
    const route = frappe.get_route();

    // Check if we are on the correct page
    if (route[0] === 'course_builder') {
        // Strategy 1: Route Options (passed internally by Frappe)
        if (frappe.route_options && frappe.route_options.course) {
            courseName = frappe.route_options.course;
        }
        // Strategy 2: URL Route (e.g., /app/course_builder/CourseName)
        else if (route[1]) {
            courseName = route[1];
        }
        // Strategy 3: Query Params (e.g., /app/course_builder?course=CourseName)
        else {
            const params = new URLSearchParams(window.location.search);
            courseName = params.get('course');
        }

        if (courseName) {
            // Decoding URI component just in case
            courseName = decodeURIComponent(courseName);
            page.set_title('Builder: ' + courseName);
        } else {
            page.set_title('Course Builder');
            // Don't show error immediately on load, let the Vue app handle it or user navigate
            // But we can show a toast hint
            frappe.show_alert({ message: 'No course selected. Please open from Course list.', indicator: 'orange' });
        }
    }

    const assetPath = 'activity_builder.bundle.js';

    $(wrapper).find('.layout-main-section').html('<div id="course-builder-app"></div>');

    try {
        frappe.require(assetPath).then(() => {
            if (window.mountActivityBuilder) {
                window.mountActivityBuilder('#course-builder-app', courseName);
            } else {
                console.error("Mount function not found in bundle.");
            }
        });
    } catch (e) {
        console.error("Failed to load course builder bundle", e);
        $(wrapper).find('.layout-main-section').append('<div class="alert alert-danger">Failed to load Course Builder.</div>');
    }
}
