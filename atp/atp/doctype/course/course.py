# Copyright (c) 2024, atp and contributors
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

@frappe.whitelist()
def save_config(course_name, scene_config):
	doc = frappe.get_doc("Course", course_name)
	doc.scene_config = scene_config
	doc.save()
	return doc.name
