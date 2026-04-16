frappe.pages['educator_dashboard'].on_page_load = function (wrapper) {
	frappe.ui.make_app_page({
		parent: wrapper,
		title: 'Educator Dashboard',
		single_column: true
	});

	$(wrapper).find('.layout-main-section').html('<div id="educator-dashboard-app"></div>');

	frappe.require('educator_dashboard.bundle.js').then(() => {
		if (window.mountEducatorDashboard) {
			window.mountEducatorDashboard('#educator-dashboard-app');
		} else {
			console.error('mountEducatorDashboard not found in bundle.');
		}
	});
};

frappe.pages['educator_dashboard'].on_page_show = function () {
	document.body.classList.add('atp-full-page');
};

frappe.pages['educator_dashboard'].on_page_hide = function () {
	document.body.classList.remove('atp-full-page');
};
