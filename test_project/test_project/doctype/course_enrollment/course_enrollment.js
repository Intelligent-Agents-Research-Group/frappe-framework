// Copyright (c) 2024, Test and contributors
// For license information, please see license.txt

frappe.ui.form.on("Course Enrollment", {
    refresh(frm) {
        if (!frm.doc.__islocal) {
            frm.add_custom_button('Open Player', () => {
                // Use Query Param for robust reload persistence
                window.location.href = `/app/course_player?enrollment=${encodeURIComponent(frm.doc.name)}`;
            });
        }
    },
});
