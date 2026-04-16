frappe.pages['atp_settings'].on_page_show = function () {
	document.body.classList.add('atp-full-page');
};

frappe.pages['atp_settings'].on_page_hide = function () {
	document.body.classList.remove('atp-full-page');
};

frappe.pages['atp_settings'].on_page_load = function (wrapper) {
	frappe.ui.make_app_page({
		parent: wrapper,
		title: 'ATP Settings',
		single_column: true
	});

	$(wrapper).find('.layout-main-section').html('<div id="atp-settings-app"></div>');

	frappe.require('atp_settings.bundle.js').then(() => {
		if (window.mountATPSettings) {
			window.mountATPSettings('#atp-settings-app');
		} else {
			console.error('mountATPSettings not found in bundle.');
		}
	});
};
