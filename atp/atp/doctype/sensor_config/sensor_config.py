import frappe
from frappe.model.document import Document


class SensorConfig(Document):
    def validate(self):
        if self.confidence_weight and not (0.0 <= self.confidence_weight <= 1.0):
            frappe.throw("Confidence Weight must be between 0.0 and 1.0")
