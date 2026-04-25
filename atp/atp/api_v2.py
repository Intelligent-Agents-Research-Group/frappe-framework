"""
ATP v2 API — whitelisted endpoints for runtime services and learner client.
All methods require authentication (no guest access).
"""

from __future__ import annotations

import json
import os
from datetime import datetime

import frappe


# ── Config helpers ────────────────────────────────────────────────────────────

def _get_engine_url() -> str:
    return os.environ.get("PED_AGENT_BASE_URL", "http://localhost:8010")


# ── Scenario / Modality ───────────────────────────────────────────────────────

@frappe.whitelist()
def get_training_scenario(scenario_id: str) -> dict:
    """Return full scenario with ordered steps and competency nodes."""
    if not frappe.db.exists("Training Scenario", scenario_id):
        frappe.throw(f"Training Scenario '{scenario_id}' not found", frappe.DoesNotExistError)
    scenario = frappe.get_doc("Training Scenario", scenario_id)
    return scenario.get_full_scenario()


@frappe.whitelist()
def get_scenario_list(modality_type: str | None = None) -> list[dict]:
    """Return published scenarios, optionally filtered by modality_type."""
    filters: dict = {"is_published": 1}
    if modality_type:
        modality_names = frappe.get_all(
            "Training Modality", filters={"modality_type": modality_type}, pluck="name"
        )
        filters["modality"] = ["in", modality_names]

    return frappe.get_all(
        "Training Scenario",
        filters=filters,
        fields=["name", "title", "modality", "version", "description", "requires_pair"],
    )


@frappe.whitelist()
def get_training_modality(modality_type: str) -> dict:
    """Return modality definition with parameter_schema and session_state_template."""
    name = frappe.db.get_value("Training Modality", {"modality_type": modality_type}, "name")
    if not name:
        frappe.throw(f"Training Modality '{modality_type}' not found", frappe.DoesNotExistError)
    return frappe.get_doc("Training Modality", name).as_dict()


# ── Learner Profile ───────────────────────────────────────────────────────────

@frappe.whitelist()
def get_learner_profile(learner_id: str) -> dict:
    """Return learner profile with current competency estimates."""
    if not frappe.db.exists("Learner Profile", learner_id):
        frappe.throw(f"Learner Profile '{learner_id}' not found", frappe.DoesNotExistError)

    profile = frappe.get_doc("Learner Profile", learner_id)
    records = frappe.get_all(
        "Competency Record",
        filters={"learner": learner_id},
        fields=["name", "competency_node", "current_estimate", "session_count", "last_updated"],
    )
    result = profile.as_dict()
    result["competency_records"] = records
    return result


@frappe.whitelist()
def get_or_create_learner_profile(user_email: str) -> dict:
    """Idempotent: get or create a LearnerProfile for the given user email."""
    from atp.atp.doctype.learner_profile.learner_profile import LearnerProfile
    profile = LearnerProfile.get_or_create_for_user(user_email)
    return {"learner_id": profile.name, "display_name": profile.display_name}


# ── Session ───────────────────────────────────────────────────────────────────

@frappe.whitelist()
def get_active_session(learner_id: str | None = None) -> dict | None:
    """Return the active TrainingSession for this learner, or None."""
    if not learner_id:
        learner_id = _get_learner_id_for_current_user()
    if not learner_id:
        return None

    session = frappe.db.get_value(
        "Training Session",
        {"learner": learner_id, "status": "Active", "docstatus": 1},
        ["name", "scenario", "status", "started_at"],
        as_dict=True,
    )
    return session


@frappe.whitelist()
def create_and_submit_session(scenario_id: str) -> dict:
    """
    Create and submit a TrainingSession, start it on the engine, and return the
    session ID, learner ID, and the agent's opening utterance for immediate rendering.
    """
    user_email = frappe.session.user
    if user_email == "Guest":
        frappe.throw("Authentication required")

    from atp.atp.doctype.learner_profile.learner_profile import LearnerProfile
    profile = LearnerProfile.get_or_create_for_user(user_email)

    if not frappe.db.exists("Training Scenario", scenario_id):
        frappe.throw(f"Scenario '{scenario_id}' not found")

    scenario = frappe.get_doc("Training Scenario", scenario_id)
    if not scenario.is_published:
        frappe.throw(f"Scenario '{scenario_id}' is not published")

    session = frappe.get_doc({
        "doctype": "Training Session",
        "learner": profile.name,
        "scenario": scenario_id,
        "scenario_version": scenario.version or "1.0.0",
        "delivery_mode": "web_2d",
        "status": "Draft",
    })
    session.insert(ignore_permissions=True)
    session.submit()
    frappe.db.commit()

    # Call engine /session/start and capture the opening agent response
    import httpx
    from atp.atp.doctype.training_session.training_session import _engine_auth_headers

    opening_agent_responses = []
    character_id = "Agent"
    try:
        payload = {
            "session_id": session.name,
            "learner_id": profile.name,
            "scenario_id": scenario_id,
            "scenario_version": scenario.version or "1.0.0",
            "delivery_mode": "web_2d",
        }
        resp = httpx.post(
            f"{_get_engine_url()}/session/start",
            json=payload,
            timeout=15.0,
            headers=_engine_auth_headers(),
        )
        resp.raise_for_status()
        engine_data = resp.json()
        opening_agent_responses = engine_data.get("opening_agent_responses", [])
        character_id = engine_data.get("character_id", "Agent")
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning("Engine /session/start failed: %s", e)

    return {
        "session_id": session.name,
        "learner_id": profile.name,
        "opening_agent_responses": opening_agent_responses,
        "character_id": character_id,
    }


@frappe.whitelist()
def get_learner_state(session_id: str) -> dict:
    """Proxy GET /learner/state/{session_id} to the Pedagogical Engine."""
    import httpx
    from atp.atp.doctype.training_session.training_session import _engine_auth_headers
    resp = httpx.get(
        f"{_get_engine_url()}/learner/state/{session_id}",
        timeout=10.0,
        headers=_engine_auth_headers(),
    )
    resp.raise_for_status()
    return resp.json()


@frappe.whitelist()
def session_turn(
    session_id: str,
    learner_id: str,
    turn_id: str,
    learner_input: str,
    input_modality: str = "text",
    turn_type: str = "conversational",
    timestamp: str = "",
) -> dict:
    """Proxy POST /session/turn to the Pedagogical Engine."""
    import httpx
    from atp.atp.doctype.training_session.training_session import _engine_auth_headers
    resp = httpx.post(
        f"{_get_engine_url()}/session/turn",
        json={
            "session_id": session_id,
            "learner_id": learner_id,
            "turn_id": turn_id,
            "learner_input": learner_input,
            "input_modality": input_modality,
            "turn_type": turn_type,
            "timestamp": timestamp,
        },
        timeout=60.0,
        headers=_engine_auth_headers(),
    )
    resp.raise_for_status()
    return resp.json()


@frappe.whitelist()
def session_end(
    session_id: str,
    learner_id: str,
    end_reason: str = "completed",
    learner_initiated: bool = True,
) -> dict:
    """Proxy POST /session/end to the Pedagogical Engine."""
    import httpx
    from atp.atp.doctype.training_session.training_session import _engine_auth_headers
    resp = httpx.post(
        f"{_get_engine_url()}/session/end",
        json={
            "session_id": session_id,
            "learner_id": learner_id,
            "end_reason": end_reason,
        },
        timeout=15.0,
        headers=_engine_auth_headers(),
    )
    resp.raise_for_status()
    new_status = "Completed" if end_reason == "completed" else "Abandoned"
    frappe.db.set_value("Training Session", session_id, "status", new_status)
    frappe.db.commit()
    return resp.json()


# ── Session Events ────────────────────────────────────────────────────────────

@frappe.whitelist(allow_guest=False)
def write_session_event(
    session_id: str,
    event_type: str,
    event_data: str | dict,
    turn_id: str | None = None,
    written_by: str = "engine",
    trigger_source: str = "engine",
    rmq_routing_key: str = "",
) -> dict:
    """Write a SessionEvent record. Called by the Pedagogical Engine."""
    if not frappe.db.exists("Training Session", session_id):
        frappe.throw(f"Training Session '{session_id}' not found")

    if isinstance(event_data, str):
        try:
            event_data = json.loads(event_data)
        except Exception:
            pass

    seq = (frappe.db.count("Session Event", {"session": session_id}) or 0) + 1
    turn_seq = (frappe.db.count("Session Event", {"session": session_id, "event_type": "turn"}) or 0) + 1 if event_type == "turn" else None

    event = frappe.get_doc({
        "doctype": "Session Event",
        "session": session_id,
        "event_type": event_type,
        "turn_id": turn_id,
        "sequence_number": seq,
        "written_by": written_by,
        "trigger_source": trigger_source,
        "rmq_routing_key": rmq_routing_key,
        "timestamp": datetime.utcnow(),
        "event_data": event_data,
    })
    event.insert(ignore_permissions=True)
    frappe.db.commit()

    if turn_seq is not None:
        frappe.db.set_value("Training Session", session_id, "turn_count", turn_seq)
    return {"event_id": event.name, "sequence_number": seq}


# ── Competency Records ────────────────────────────────────────────────────────

@frappe.whitelist(allow_guest=False)
def update_competency_record(
    learner_id: str,
    competency_node_id: str,
    new_estimate: float,
    session_id: str | None = None,
) -> dict:
    """Update or create a CompetencyRecord with the new estimate from the engine."""
    if not frappe.db.exists("Learner Profile", learner_id):
        frappe.throw(f"Learner Profile '{learner_id}' not found")
    if not frappe.db.exists("Competency Node", competency_node_id):
        frappe.throw(f"Competency Node '{competency_node_id}' not found")

    from atp.atp.doctype.competency_record.competency_record import CompetencyRecord
    record = CompetencyRecord.get_or_create(learner_id, competency_node_id)

    previous = float(record.current_estimate or 0.0)
    record.current_estimate = round(float(new_estimate), 4)
    record.session_count = (record.session_count or 0) + 1
    record.last_updated = datetime.utcnow()

    history = record.history if isinstance(record.history, list) else (
        json.loads(record.history) if record.history else []
    )
    history.append({
        "session_id": session_id,
        "delta": round(float(new_estimate) - previous, 4),
        "source": "native",
        "timestamp": record.last_updated.isoformat(),
    })
    record.history = json.dumps(history)
    record.save(ignore_permissions=True)
    frappe.db.commit()

    return {
        "competency_node_id": competency_node_id,
        "previous_estimate": previous,
        "new_estimate": record.current_estimate,
    }


# ── Bridge / External integrations ───────────────────────────────────────────

@frappe.whitelist(allow_guest=False)
def get_competency_mapping_schema(source_name: str) -> dict:
    """Return a CompetencyMappingSchema by external_system_name."""
    name = frappe.db.get_value(
        "Competency Mapping Schema", {"external_system_name": source_name}, "name"
    )
    if not name:
        frappe.throw(
            f"Competency Mapping Schema for source '{source_name}' not found",
            frappe.DoesNotExistError,
        )
    doc = frappe.get_doc("Competency Mapping Schema", name)
    return {
        "name": doc.name,
        "external_system_name": doc.external_system_name,
        "version": doc.version or "1.0",
        "mapping_rules": doc.mapping_rules if isinstance(doc.mapping_rules, list) else (
            json.loads(doc.mapping_rules) if doc.mapping_rules else []
        ),
    }


@frappe.whitelist(allow_guest=False)
def get_learner_id_by_email(email: str) -> dict:
    """Return learner_id for the given user email, creating a profile if needed."""
    from atp.atp.doctype.learner_profile.learner_profile import LearnerProfile
    profile = LearnerProfile.get_or_create_for_user(email)
    return {"learner_id": profile.name}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_learner_id_for_current_user() -> str | None:
    user = frappe.session.user
    if user == "Guest":
        return None
    return frappe.db.get_value("Learner Profile", {"user": user}, "name")
