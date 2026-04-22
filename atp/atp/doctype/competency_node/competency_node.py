import frappe
from frappe.model.document import Document


class CompetencyNode(Document):
    def validate(self):
        if self.bkt_params:
            self._validate_bkt_params()

    def _validate_bkt_params(self):
        import json
        try:
            params = json.loads(self.bkt_params) if isinstance(self.bkt_params, str) else self.bkt_params
        except Exception:
            frappe.throw("BKT Parameters must be valid JSON")

        required = {"L0", "T", "S", "G"}
        missing = required - set(params.keys())
        if missing:
            frappe.throw(f"BKT Parameters missing keys: {missing}")

        for key, val in params.items():
            if key in required and not (0.0 <= float(val) <= 1.0):
                frappe.throw(f"BKT parameter {key} must be between 0.0 and 1.0")

    def get_default_bkt_params(self) -> dict:
        import json
        if self.bkt_params:
            return json.loads(self.bkt_params) if isinstance(self.bkt_params, str) else self.bkt_params
        return {"L0": 0.3, "T": 0.1, "S": 0.1, "G": 0.2}
