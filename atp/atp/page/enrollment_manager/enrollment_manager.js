frappe.pages['enrollment_manager'].on_page_show = function () {
	document.body.classList.add('atp-full-page');
};

frappe.pages['enrollment_manager'].on_page_hide = function () {
	document.body.classList.remove('atp-full-page');
};

frappe.pages['enrollment_manager'].on_page_load = function (wrapper) {
	frappe.ui.make_app_page({
		parent: wrapper,
		title: 'Enrollment Manager',
		single_column: true
	});

	$(wrapper).find('.layout-main-section').html('<div id="enrollment-manager-app"></div>');

	frappe.require('enrollment_manager.bundle.js').then(() => {
		if (window.mountEnrollmentManager) {
			window.mountEnrollmentManager('#enrollment-manager-app');
		} else {
			console.error('mountEnrollmentManager not found in bundle.');
		}
	});
};
