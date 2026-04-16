frappe.pages['atp_admin'].on_page_load = function (wrapper) {
	frappe.ui.make_app_page({
		parent: wrapper,
		title: 'ATP Admin',
		single_column: true
	});

	$(wrapper).find('.layout-main-section').html('<div id="atp-admin-app"></div>');

	frappe.require('admin_dashboard.bundle.js').then(() => {
		if (window.mountAdminDashboard) {
			window.mountAdminDashboard('#atp-admin-app');
		} else {
			console.error('mountAdminDashboard not found in bundle.');
		}
	});
};

frappe.pages['atp_admin'].on_page_show = function () {
	document.body.classList.add('atp-full-page');
};

frappe.pages['atp_admin'].on_page_hide = function () {
	document.body.classList.remove('atp-full-page');
};
