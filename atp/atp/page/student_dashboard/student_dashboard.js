frappe.pages['student_dashboard'].on_page_show = function () {
	document.body.classList.add('atp-full-page');
	if (window.refreshStudentDashboard) {
		window.refreshStudentDashboard();
	}
};

frappe.pages['student_dashboard'].on_page_hide = function () {
	document.body.classList.remove('atp-full-page');
};

frappe.pages['student_dashboard'].on_page_load = function (wrapper) {
	frappe.ui.make_app_page({
		parent: wrapper,
		title: 'Student Dashboard',
		single_column: true
	});

	$(wrapper).find('.layout-main-section').html('<div id="student-dashboard-app"></div>');

	frappe.require('student_dashboard.bundle.js').then(() => {
		if (window.mountStudentDashboard) {
			window.mountStudentDashboard('#student-dashboard-app');
		} else {
			console.error('mountStudentDashboard not found in bundle.');
		}
	});
};
