import frappe
from frappe.model.document import Document


class LearnerProfile(Document):
    @staticmethod
    def get_or_create_for_user(user_email: str) -> "LearnerProfile":
        existing = frappe.db.get_value("Learner Profile", {"user": user_email}, "name")
        if existing:
            return frappe.get_doc("Learner Profile", existing)

        user_doc = frappe.get_doc("User", user_email)
        profile = frappe.get_doc({
            "doctype": "Learner Profile",
            "user": user_email,
            "display_name": user_doc.full_name or user_email,
        })
        profile.insert(ignore_permissions=True)
        frappe.db.commit()
        return profile

    def get_competency_records(self) -> list[dict]:
        return frappe.get_all(
            "Competency Record",
            filters={"learner": self.name},
            fields=["name", "competency_node", "current_estimate", "session_count", "last_updated"],
        )
