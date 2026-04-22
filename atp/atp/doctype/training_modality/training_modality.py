import frappe
from frappe.model.document import Document


class TrainingModality(Document):
    def validate(self):
        if not self.modality_type:
            frappe.throw("Modality Type is required")
        # Ensure modality_type is a valid identifier
        if not self.modality_type.replace("_", "").isalnum():
            frappe.throw("Modality Type must contain only letters, numbers, and underscores")
