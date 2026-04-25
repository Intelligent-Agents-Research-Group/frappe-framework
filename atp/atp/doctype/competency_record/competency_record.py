import json
from datetime import datetime

import frappe
from frappe.model.document import Document


class CompetencyRecord(Document):
    def update_bkt(self, observation: bool, session_id: str | None = None) -> float:
        """Apply a BKT update and return the new estimate."""
        node = frappe.get_doc("Competency Node", self.competency_node)
        params = node.get_default_bkt_params()

        L = float(self.current_estimate or params["L0"])
        T, S, G = params["T"], params["S"], params["G"]

        if observation:
            P_L = (L * (1 - S)) / (L * (1 - S) + (1 - L) * G)
        else:
            P_L = (L * S) / (L * S + (1 - L) * (1 - G))
        new_L = P_L + (1 - P_L) * T

        self.current_estimate = round(new_L, 4)
        self.session_count = (self.session_count or 0) + 1
        self.last_updated = datetime.utcnow()

        history = json.loads(self.history) if isinstance(self.history, str) and self.history else (self.history or [])
        history.append({
            "session_id": session_id,
            "delta": round(new_L - L, 4),
            "source": "native",
            "timestamp": self.last_updated.isoformat(),
        })
        self.history = json.dumps(history)
        self.save(ignore_permissions=True)
        return self.current_estimate

    @staticmethod
    def get_or_create(learner_name: str, competency_node_id: str) -> "CompetencyRecord":
        existing = frappe.db.get_value(
            "Competency Record",
            {"learner": learner_name, "competency_node": competency_node_id},
            "name",
        )
        if existing:
            return frappe.get_doc("Competency Record", existing)

        node = frappe.get_doc("Competency Node", competency_node_id)
        params = node.get_default_bkt_params()
        rec = frappe.get_doc({
            "doctype": "Competency Record",
            "learner": learner_name,
            "competency_node": competency_node_id,
            "current_estimate": params["L0"],
            "session_count": 0,
            "history": "[]",
        })
        rec.insert(ignore_permissions=True)
        frappe.db.commit()
        return rec
