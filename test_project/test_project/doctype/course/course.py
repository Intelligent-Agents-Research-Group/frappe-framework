# Copyright (c) 2024, Test and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class Course(Document):
	pass

@frappe.whitelist()
def save_flow(course_name, flow_data):
    doc = frappe.get_doc("Course", course_name)
    doc.flow_data = flow_data
    doc.save()
    return doc.name

