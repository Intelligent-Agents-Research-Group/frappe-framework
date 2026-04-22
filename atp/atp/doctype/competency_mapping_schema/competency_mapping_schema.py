import json

import frappe
from frappe.model.document import Document


class CompetencyMappingSchema(Document):
    def validate_payload(self, raw_payload: dict) -> list[dict]:
        """Dry-run: return list of extracted signals without modifying any records."""
        rules = json.loads(self.mapping_rules) if isinstance(self.mapping_rules, str) else (self.mapping_rules or [])
        extracted = []
        for rule in rules:
            value = _extract_value(raw_payload, rule.get("external_signal", ""))
            if value is not None:
                delta = _apply_transform(value, rule.get("score_transform", {}))
                extracted.append({
                    "external_field": rule["external_signal"],
                    "extracted_value": value,
                    "competency_node_id": rule["competency_node_id"],
                    "score_delta": delta,
                    "confidence": rule.get("confidence_weight", 0.8),
                })
        return extracted


def _extract_value(payload: dict, path: str):
    """Simple $ JSONPath resolver for top-level fields."""
    if path.startswith("$."):
        key = path[2:]
        return payload.get(key)
    return None


def _apply_transform(value: float, transform: dict) -> float:
    t_type = transform.get("type", "direct_delta")
    if t_type == "direct_delta":
        return float(value)
    if t_type == "linear_scale":
        in_min = transform.get("input_min", 0)
        in_max = transform.get("input_max", 100)
        out_min = transform.get("output_min", 0.0)
        out_max = transform.get("output_max", 1.0)
        ratio = (float(value) - in_min) / max(in_max - in_min, 1)
        return out_min + ratio * (out_max - out_min)
    if t_type == "threshold":
        direction = transform.get("threshold_direction", "above")
        threshold = transform.get("threshold_value", 0.5)
        if direction == "above":
            return 0.1 if float(value) >= threshold else -0.05
        return 0.1 if float(value) <= threshold else -0.05
    if t_type == "boolean":
        return 0.1 if value else -0.05
    return float(value)
