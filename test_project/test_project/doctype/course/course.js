// Copyright (c) 2024, Test and contributors
// For license information, please see license.txt

frappe.ui.form.on("Course", {
    refresh(frm) {
        if (!frm.doc.__islocal) {
            frm.add_custom_button('Open Builder', () => {
                frappe.set_route('course_builder', frm.doc.name);
            });
        }
    },
});
