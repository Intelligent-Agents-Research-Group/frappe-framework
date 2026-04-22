import json
import logging
from datetime import datetime

import frappe
from frappe.model.document import Document

logger = logging.getLogger(__name__)


class TrainingSession(Document):
    def on_submit(self):
        self._ensure_learner_profile()
        self._set_started_at()

    def on_cancel(self):
        self._emit_session_end("abandoned")

    def _ensure_learner_profile(self):
        from atp.atp.doctype.learner_profile.learner_profile import LearnerProfile
        if not self.learner:
            frappe.throw("Learner Profile is required before submitting a session")

    def _set_started_at(self):
        frappe.db.set_value("Training Session", self.name, {
            "started_at": datetime.utcnow(),
            "status": "Active",
        })

    def _emit_session_start(self):
        """
        POST session/start to the Pedagogical Engine.
        Non-blocking: logs a warning if the engine is unreachable so the session
        still submits successfully in Frappe.
        """
        import httpx
        from atp.atp.api_v2 import _get_engine_url

        scenario = frappe.get_doc("Training Scenario", self.scenario)
        payload = {
            "session_id": self.name,
            "learner_id": self.learner,
            "scenario_id": self.scenario,
            "scenario_version": self.scenario_version or "1.0.0",
            "delivery_mode": self.delivery_mode or "web_2d",
        }
        try:
            resp = httpx.post(
                f"{_get_engine_url()}/session/start",
                json=payload,
                timeout=5.0,
                headers=_engine_auth_headers(),
            )
            resp.raise_for_status()
        except Exception as e:
            logger.warning("Pedagogical Engine unreachable on session submit: %s", e)
            frappe.log_error(title="ATP Engine Unreachable", message=str(e))

    def _emit_session_end(self, end_reason: str):
        import httpx
        from atp.atp.api_v2 import _get_engine_url

        try:
            httpx.post(
                f"{_get_engine_url()}/session/end",
                json={"session_id": self.name, "end_reason": end_reason},
                timeout=3.0,
                headers=_engine_auth_headers(),
            )
        except Exception as e:
            logger.warning("Engine session/end failed: %s", e)


def _engine_auth_headers() -> dict:
    try:
        token = frappe.db.get_single_value("ATP Settings", "engine_bearer_token") or ""
    except Exception:
        token = ""
    return {"Authorization": f"Bearer {token}"} if token else {}
