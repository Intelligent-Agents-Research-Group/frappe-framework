import json

import frappe
from frappe.model.document import Document


class TrainingScenario(Document):
    def validate(self):
        self._validate_steps()

    def _validate_steps(self):
        if not self.steps:
            return
        step_ids = [s.step_id for s in self.steps]
        if len(step_ids) != len(set(step_ids)):
            frappe.throw("Step IDs must be unique within a scenario")

    def before_save(self):
        if self.is_published:
            self._validate_for_publish()

    def _validate_for_publish(self):
        if not self.steps:
            frappe.throw("A published scenario must have at least one step")
        step_types = [s.step_type for s in self.steps]
        if "debrief" not in step_types:
            frappe.throw("A published scenario must include a debrief step")

    def get_full_scenario(self) -> dict:
        """Return full scenario data including steps, competency nodes, and character."""
        scenario = self.as_dict()
        scenario["steps"] = sorted(
            [s.as_dict() for s in self.steps],
            key=lambda x: x.get("order", 0),
        )
        scenario["competency_nodes"] = [cn.as_dict() for cn in self.competency_nodes]
        if self.agent_character:
            try:
                char = frappe.get_doc("Agent Character", self.agent_character)
                scenario["agent_character_data"] = {
                    "name": char.name,
                    "display_name": char.display_name or "",
                    "instructional_role": char.instructional_role or "",
                    "persona_description": char.persona_description or "",
                    "default_modality_parameters": char.default_modality_parameters or {},
                }
            except Exception:
                scenario["agent_character_data"] = {}
        else:
            scenario["agent_character_data"] = {}
        return scenario
