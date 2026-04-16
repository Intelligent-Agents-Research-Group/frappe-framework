frappe.pages['course_player'].on_page_show = function () {
	document.body.classList.add('atp-full-page');
};

frappe.pages['course_player'].on_page_hide = function () {
	document.body.classList.remove('atp-full-page');
};

frappe.pages['course_player'].on_page_load = function (wrapper) {
    var page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'Course Player',
        single_column: true
    });

    let enrollmentName = null;
    const route = frappe.get_route();

    if (route[0] === 'course_player') {
        // Strategy 1: Route Options
        if (frappe.route_options && frappe.route_options.enrollment) {
            enrollmentName = frappe.route_options.enrollment;
        }
        // Strategy 2: URL Route (e.g., /app/course_player/EnrollmentName)
        else if (route[1]) {
            enrollmentName = route[1];
        }
        // Strategy 3: Query Params
        else {
            const params = new URLSearchParams(window.location.search);
            enrollmentName = params.get('enrollment');
        }

        if (enrollmentName) {
            enrollmentName = decodeURIComponent(enrollmentName);
            page.set_title('Player: ' + enrollmentName);
        } else {
            page.set_title('Course Player');
            frappe.show_alert({ message: 'No enrollment selected.', indicator: 'orange' });
        }
    }

    const assetPath = 'course_player.bundle.js';

    $(wrapper).find('.layout-main-section').html('<div id="course-player-app"></div>');

    try {
        frappe.require(assetPath).then(() => {
            if (window.mountCoursePlayer) {
                window.mountCoursePlayer('#course-player-app', enrollmentName);
            } else {
                console.error("Mount function not found in bundle.");
            }
        });
    } catch (e) {
        console.error("Failed to load course player bundle", e);
        $(wrapper).find('.layout-main-section').append('<div class="alert alert-danger">Failed to load Course Player.</div>');
    }
}
