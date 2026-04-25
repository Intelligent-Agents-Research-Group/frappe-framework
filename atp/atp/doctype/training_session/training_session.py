import json
import logging
from datetime import datetime

import frappe
from frappe.model.document import Document

logger = logging.getLogger(__name__)


class TrainingSession(Document):
    def on_submit(self):
        # Session start (engine call + opening utterance) is handled by
        # api_v2.create_and_submit_session(), which is the only call path for
        # learner-initiated sessions. This hook only handles the Frappe-side state.
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
