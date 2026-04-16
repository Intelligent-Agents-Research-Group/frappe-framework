frappe.pages['educator_analytics'].on_page_load = function (wrapper) {
	frappe.ui.make_app_page({
		parent: wrapper,
		title: 'Class Analytics',
		single_column: true
	});

	$(wrapper).find('.layout-main-section').html('<div id="educator-analytics-app"></div>');

	frappe.require('educator_analytics.bundle.js').then(() => {
		if (window.mountEducatorAnalytics) {
			window.mountEducatorAnalytics('#educator-analytics-app');
		} else {
			console.error('mountEducatorAnalytics not found in bundle.');
		}
	});
};

frappe.pages['educator_analytics'].on_page_show = function () {
	document.body.classList.add('atp-full-page');
};

frappe.pages['educator_analytics'].on_page_hide = function () {
	document.body.classList.remove('atp-full-page');
};
