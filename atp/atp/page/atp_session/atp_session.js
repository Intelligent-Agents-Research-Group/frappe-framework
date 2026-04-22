frappe.pages["atp_session"].on_page_show = function () {
	document.body.classList.add("atp-full-page");
};

frappe.pages["atp_session"].on_page_hide = function () {
	document.body.classList.remove("atp-full-page");
};

frappe.pages["atp_session"].on_page_load = function (wrapper) {
	frappe.ui.make_app_page({
		parent: wrapper,
		title: "Training Session",
		single_column: true,
	});

	$(wrapper).find(".layout-main-section").html('<div id="atp-session-app"></div>');

	const route = frappe.get_route();
	const enrollmentParam = route[1] ? decodeURIComponent(route[1]) : null;
	const scenarioParam = route[2] ? decodeURIComponent(route[2]) : null;

	frappe.require("atp_session.bundle.js").then(() => {
		if (window.mountATPSession) {
			window.mountATPSession("#atp-session-app", enrollmentParam, scenarioParam);
		}
	});
};
