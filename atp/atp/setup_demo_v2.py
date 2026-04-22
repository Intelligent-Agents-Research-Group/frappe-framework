"""
ATP v2 Demo Seed Data

Run with:
    bench --site atp.localhost execute atp.atp.setup_demo_v2.run
"""

from __future__ import annotations

import json

import frappe


# ── BKT defaults ─────────────────────────────────────────────────────────────
BKT_DEFAULT = {"L0": 0.3, "T": 0.1, "S": 0.1, "G": 0.2}

# ── Negotiation competency nodes ──────────────────────────────────────────────
COMPETENCY_NODES = [
    {
        "label": "BATNA Identification",
        "description": "Learner can identify and articulate their BATNA before entering negotiation",
        "modality_type": "negotiation_single",
        "mastery_threshold": 0.8,
    },
    {
        "label": "Opening Anchor",
        "description": "Learner makes an assertive, justified opening anchor",
        "modality_type": "negotiation_single",
        "mastery_threshold": 0.8,
    },
    {
        "label": "Interest Probing",
        "description": "Learner asks questions to uncover the counterpart's underlying interests",
        "modality_type": "negotiation_single",
        "mastery_threshold": 0.75,
    },
    {
        "label": "Concession Strategy",
        "description": "Learner makes concessions strategically (decreasing increments, conditional)",
        "modality_type": "negotiation_single",
        "mastery_threshold": 0.8,
    },
    {
        "label": "ZOPA Recognition",
        "description": "Learner identifies the Zone of Possible Agreement",
        "modality_type": "negotiation_single",
        "mastery_threshold": 0.75,
    },
    {
        "label": "Closing Technique",
        "description": "Learner closes effectively (summary close, conditional close, or alternative close)",
        "modality_type": "negotiation_single",
        "mastery_threshold": 0.8,
    },
]

# ── Negotiation modality engine directives ────────────────────────────────────
ENGINE_DIRECTIVES = """You are {character.display_name}, {character.persona_description}.

SESSION CONTEXT:
- Scenario: {scenario.title}
- Current Phase: {session_state.phase}
- Current Strategy: {session_state.current_strategy}
- Turn Count: {session_state.turn_count}
- Concessions Used: {session_state.concessions_used}
- Agent Mood Shift: {session_state.agent_mood_shift}

YOUR NEGOTIATION POSITION:
- Opening Anchor: {modality_parameters.opening_anchor}
- Aspiration Point: {modality_parameters.aspiration_point}
- Resistance Point: {modality_parameters.resistance_point}
- BATNA (hidden): {modality_parameters.batna}
- Concession Strategy: {modality_parameters.concession_strategy}
- Priorities (ordered): {modality_parameters.priorities}
- Emotional Profile: {modality_parameters.emotional_profile}

LEARNER STATE:
- Competency Estimates: {learner_state.competency_estimates}
- Affective State: {learner_state.affective_state}
- Consecutive Errors: {learner_state.consecutive_errors}

INSTRUCTIONAL STRATEGY: {session_state.current_strategy}

RESPONSE FORMAT (JSON):
{
  "spoken_text": "Your in-character response to the learner's last message",
  "nonverbal_cues": {"gesture": null, "expression": "neutral", "gaze": "direct"},
  "assessment": {
    "competency_node_id": "ID of the primary competency demonstrated or missed",
    "score_delta": 0.0,
    "observation": true
  },
  "next_phase": null,
  "agent_mood_delta": 0.0
}

RULES:
- Stay fully in character. Never break the fourth wall.
- Do NOT reveal your BATNA or resistance point.
- Your concession strategy is {modality_parameters.concession_strategy}.
- If the strategy is socratic_questioning: end with a probing question.
- If the strategy is direct_instruction: offer a brief coaching hint outside character (prefix with [COACH]).
- Respond in 2-4 sentences of spoken text.
"""

NEGOTIATION_SESSION_STATE_TEMPLATE = {
    "modality_type": "negotiation_single",
    "session_id": "",
    "turn_count": 0,
    "hints_used": 0,
    "interventions_triggered": 0,
    "current_strategy": "socratic_questioning",
    "affective_state": {"engagement": 0.6, "frustration": 0.1, "confidence": 0.5},
    "consecutive_errors": 0,
    "phase": "opening",
    "current_agent_position": "",
    "current_learner_position": None,
    "offers_made": [],
    "concessions_used": 0,
    "agent_mood_shift": 0.0,
    "zopa_identified": False,
    "impasse_count": 0,
    "learner_anchored_first": None,
    "interest_probe_count": 0,
}

NEGOTIATION_PARAMETER_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "required": ["batna", "aspiration_point", "resistance_point", "opening_anchor", "concession_strategy", "priorities", "emotional_profile"],
    "properties": {
        "batna": {"type": "string"},
        "aspiration_point": {"type": "string"},
        "resistance_point": {"type": "string"},
        "opening_anchor": {"type": "string"},
        "concession_strategy": {"type": "string", "enum": ["decreasing_increments", "reciprocal", "hardball", "collaborative", "anchored_firmness"]},
        "priorities": {"type": "array", "items": {"type": "string"}},
        "emotional_profile": {"type": "string"},
        "context_background": {"type": "string"},
    },
}


def run():
    frappe.set_user("Administrator")

    print("\n=== ATP v2 Seed Data ===\n")

    # 1. Training Modality
    modality_name = _upsert_training_modality()

    # 2. Competency Nodes
    comp_node_names = _upsert_competency_nodes()

    # 3. Agent Character
    character_name = _upsert_agent_character()

    # 4. Sensor Configs
    _upsert_sensor_configs()

    # 5. Training Scenario
    scenario_name = _upsert_training_scenario(modality_name, comp_node_names, character_name)

    # 6. Service account (if requested)
    print("\nDone! Seed data summary:")
    print(f"  Training Modality:  {modality_name}")
    print(f"  Competency Nodes:   {len(comp_node_names)} nodes")
    print(f"  Agent Character:    {character_name}")
    print(f"  Training Scenario:  {scenario_name}")
    print("\nTo start a demo session, open:")
    print("  http://atp.localhost:8001/atp_session\n")


def _upsert_training_modality() -> str:
    if frappe.db.exists("Training Modality", {"modality_type": "negotiation_single"}):
        name = frappe.db.get_value("Training Modality", {"modality_type": "negotiation_single"}, "name")
        doc = frappe.get_doc("Training Modality", name)
    else:
        doc = frappe.get_doc({"doctype": "Training Modality"})

    doc.update({
        "modality_type": "negotiation_single",
        "display_name": "Negotiation — Single Party",
        "is_active": 1,
        "description": "One learner negotiates against one AI counterpart agent. Covers anchoring, interest probing, concession strategy, ZOPA, and closing.",
        "engine_directives": ENGINE_DIRECTIVES,
        "parameter_schema": NEGOTIATION_PARAMETER_SCHEMA,
        "session_state_template": NEGOTIATION_SESSION_STATE_TEMPLATE,
    })

    if doc.name:
        doc.save(ignore_permissions=True)
        print(f"  Updated Training Modality: {doc.name}")
    else:
        doc.insert(ignore_permissions=True)
        print(f"  Created Training Modality: {doc.name}")

    frappe.db.commit()
    return doc.name


def _upsert_competency_nodes() -> list[str]:
    names = []
    for node_data in COMPETENCY_NODES:
        existing = frappe.db.get_value(
            "Competency Node",
            {"label": node_data["label"], "modality_type": node_data["modality_type"]},
            "name",
        )
        if existing:
            doc = frappe.get_doc("Competency Node", existing)
        else:
            doc = frappe.get_doc({"doctype": "Competency Node"})

        doc.update({**node_data, "bkt_params": BKT_DEFAULT})

        if doc.name:
            doc.save(ignore_permissions=True)
        else:
            doc.insert(ignore_permissions=True)

        names.append(doc.name)
        print(f"  Competency Node: {doc.name} — {doc.label}")

    frappe.db.commit()
    return names


def _upsert_agent_character() -> str:
    existing = frappe.db.get_value("Agent Character", {"display_name": "Jordan Chen"}, "name")
    if existing:
        doc = frappe.get_doc("Agent Character", existing)
    else:
        doc = frappe.get_doc({"doctype": "Agent Character"})

    doc.update({
        "display_name": "Jordan Chen",
        "instructional_role": "counterpart",
        "persona_description": "HR Manager at TechCorp, analytical and firm. Has been trying to fill this senior software engineer role for 3 months.",
        "default_modality_parameters": {
            "batna": "Move on to the next candidate in the pipeline (2 strong alternates identified)",
            "aspiration_point": "$95,000 salary with on-site 5 days/week",
            "resistance_point": "$118,000 salary with 3 days remote",
            "opening_anchor": "$92,000 with standard benefits and on-site requirement",
            "concession_strategy": "decreasing_increments",
            "priorities": ["base_salary", "remote_flexibility", "start_date", "equity"],
            "emotional_profile": "firm_professional",
            "context_background": "Has been trying to fill this role for 3 months and is under pressure. Team needs someone quickly but budget is constrained.",
        },
    })

    if doc.name:
        doc.save(ignore_permissions=True)
    else:
        doc.insert(ignore_permissions=True)

    frappe.db.commit()
    print(f"  Agent Character: {doc.name} — {doc.display_name}")
    return doc.name


def _upsert_sensor_configs():
    sensors = [
        {
            "sensor_type": "facial_expression",
            "display_name": "Facial Expression (Camera)",
            "confidence_weight": 0.8,
            "description": "DeepFace-based emotion detection at 2fps",
        },
        {
            "sensor_type": "voice_affect",
            "display_name": "Voice Affect (Microphone)",
            "confidence_weight": 0.75,
            "description": "Whisper transcript + librosa prosody features per utterance",
        },
        {
            "sensor_type": "blockly_event",
            "display_name": "Blockly Workspace Events",
            "confidence_weight": 0.9,
            "description": "Block placement, deletion, run, test events from Blockly workspace",
        },
        {
            "sensor_type": "physiological_sim",
            "display_name": "Physiological Sensor (Simulated)",
            "confidence_weight": 0.6,
            "description": "Simulated GSR/heart-rate for testing sensor fusion pipeline",
        },
    ]
    for s in sensors:
        existing = frappe.db.get_value("Sensor Config", {"sensor_type": s["sensor_type"]}, "name")
        if existing:
            doc = frappe.get_doc("Sensor Config", existing)
        else:
            doc = frappe.get_doc({"doctype": "Sensor Config"})
        doc.update({**s, "is_active": 1})
        if doc.name:
            doc.save(ignore_permissions=True)
        else:
            doc.insert(ignore_permissions=True)
        print(f"  Sensor Config: {doc.name} — {doc.sensor_type}")
    frappe.db.commit()


def _upsert_training_scenario(modality_name: str, comp_node_names: list[str], character_name: str) -> str:
    existing = frappe.db.get_value("Training Scenario", {"title": "Salary Negotiation: Software Engineer Offer"}, "name")
    if existing:
        doc = frappe.get_doc("Training Scenario", existing)
    else:
        doc = frappe.get_doc({"doctype": "Training Scenario"})

    char_params = frappe.db.get_value("Agent Character", character_name, "default_modality_parameters")
    if isinstance(char_params, str):
        char_params = json.loads(char_params)

    doc.update({
        "title": "Salary Negotiation: Software Engineer Offer",
        "modality": modality_name,
        "version": "1.0.0",
        "is_published": 1,
        "requires_pair": 0,
        "description": "Negotiate a senior software engineer job offer with Jordan Chen, HR Manager at TechCorp. Practice anchoring, interest probing, and strategic concessions.",
        "competency_nodes": [
            {"competency_node": n, "weight": 1.0} for n in comp_node_names
        ],
        "steps": [
            {
                "step_id": "step_001_opening",
                "step_type": "situation",
                "order": 1,
                "input_expected": 1,
                "input_type": "text",
                "situation_text": "You've just received a job offer from TechCorp for a Senior Software Engineer position. Jordan Chen, the HR Manager, is ready to discuss the details. The posted range was $95,000–$120,000. Your research shows the market rate is $118,000–$135,000 for your level of experience. Jordan opens with: 'We're really excited about you joining the team. We'd like to offer you $92,000 with our standard benefits package. What are your thoughts?'",
                "modality_parameters": {**char_params},
                "branch_conditions": {
                    "default_next_step": "step_002_exploration",
                    "conditions": [
                        {
                            "condition_id": "branch_anchored_early",
                            "label": "Learner anchored assertively",
                            "next_step": "step_002_exploration",
                            "predicate": {
                                "type": "session_state",
                                "state_path": "$.learner_anchored_first",
                                "operator": "is_true",
                                "value": None,
                            },
                        }
                    ],
                },
            },
            {
                "step_id": "step_002_exploration",
                "step_type": "question",
                "order": 2,
                "input_expected": 1,
                "input_type": "text",
                "situation_text": "The negotiation continues. Jordan responds to your opening position. Explore interests, ask clarifying questions, and work toward an agreement.",
                "modality_parameters": {**char_params},
                "branch_conditions": {
                    "default_next_step": "step_003_bargaining",
                    "conditions": [
                        {
                            "condition_id": "branch_low_mastery",
                            "label": "Low mastery — needs coaching",
                            "next_step": "step_003_bargaining",
                            "predicate": {
                                "type": "turn_assessment",
                                "operator": "lt",
                                "value": 0,
                            },
                        },
                        {
                            "condition_id": "branch_high_frustration",
                            "label": "High frustration",
                            "next_step": "step_003_bargaining",
                            "predicate": {
                                "type": "affective",
                                "affective_dimension": "frustration",
                                "operator": "gt",
                                "value": 0.7,
                            },
                        },
                    ],
                },
            },
            {
                "step_id": "step_003_bargaining",
                "step_type": "task",
                "order": 3,
                "input_expected": 1,
                "input_type": "text",
                "situation_text": "You're in the bargaining phase. Make strategic concessions and work toward a deal that meets your interests. Remember your BATNA.",
                "modality_parameters": {**char_params},
                "branch_conditions": {
                    "default_next_step": "debrief",
                    "conditions": [
                        {
                            "condition_id": "branch_to_debrief_on_close",
                            "label": "Move to debrief",
                            "next_step": "debrief",
                            "predicate": {
                                "type": "session_state",
                                "state_path": "$.phase",
                                "operator": "eq",
                                "value": "closing",
                            },
                        }
                    ],
                },
            },
            {
                "step_id": "debrief",
                "step_type": "debrief",
                "order": 4,
                "input_expected": 0,
                "input_type": "none",
                "situation_text": "Session complete. Review your negotiation performance.",
                "modality_parameters": {},
                "branch_conditions": {"default_next_step": "debrief"},
            },
        ],
    })

    if doc.name:
        doc.save(ignore_permissions=True)
        print(f"  Updated Training Scenario: {doc.name}")
    else:
        doc.insert(ignore_permissions=True)
        print(f"  Created Training Scenario: {doc.name}")

    frappe.db.commit()
    return doc.name


def create_service_account() -> dict:
    """
    Create a Frappe API key for the atp-engine service account.
    Prints the key/secret pair to stdout — copy into .env.v2.
    """
    frappe.set_user("Administrator")

    service_user = "atp-engine@service.atp"

    if not frappe.db.exists("User", service_user):
        user = frappe.get_doc({
            "doctype": "User",
            "email": service_user,
            "first_name": "ATP Engine",
            "last_name": "Service",
            "user_type": "System User",
            "enabled": 1,
        })
        user.insert(ignore_permissions=True)

    from frappe.core.doctype.user.user import generate_keys
    keys = generate_keys(service_user)

    print(f"\nService account created: {service_user}")
    print(f"FRAPPE_API_KEY={keys.get('api_key')}")
    print(f"FRAPPE_API_SECRET={keys.get('api_secret')}")
    print("Add these to .env.v2\n")

    return keys
