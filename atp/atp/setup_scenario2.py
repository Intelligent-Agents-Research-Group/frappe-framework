"""
Create SCEN-0002: Difficult Conversation — Giving Constructive Feedback

Run with:
    bench --site atp.localhost execute atp.atp.setup_scenario2.run
"""
from __future__ import annotations
import json
import frappe

BKT_DEFAULT = {"L0": 0.3, "T": 0.1, "S": 0.1, "G": 0.2}

COMPETENCY_NODES = [
    {
        "label": "Empathic Opening",
        "description": "Opens the conversation with empathy, not judgment",
        "modality_type": "negotiation_single",
        "mastery_threshold": 0.75,
    },
    {
        "label": "Specific Behavior Focus",
        "description": "Describes specific observable behaviors rather than character traits",
        "modality_type": "negotiation_single",
        "mastery_threshold": 0.8,
    },
    {
        "label": "Impact Articulation",
        "description": "Clearly explains the business or team impact of the behavior",
        "modality_type": "negotiation_single",
        "mastery_threshold": 0.8,
    },
    {
        "label": "Active Listening",
        "description": "Acknowledges the employee's perspective without dismissing it",
        "modality_type": "negotiation_single",
        "mastery_threshold": 0.75,
    },
    {
        "label": "Collaborative Problem Solving",
        "description": "Works with the employee to identify solutions rather than dictating them",
        "modality_type": "negotiation_single",
        "mastery_threshold": 0.8,
    },
]

ENGINE_DIRECTIVES = """You are Alex Rivera, a software engineer who has been missing sprint deadlines for the past two months. You are meeting with your manager for a feedback conversation. You are initially defensive but open to dialogue if treated respectfully.

Respond naturally as Alex. If your manager is judgmental or blaming, push back defensively. If they are specific, empathetic, and focused on the work rather than your character, become more open and collaborative.

Your hidden context (don't reveal unless the conversation leads there naturally):
- You've been dealing with unclear requirements from the product team that caused the delays
- You were hesitant to escalate because you didn't want to seem like you were making excuses
- You genuinely want to improve and are frustrated too

Session context: {session_state}
Learner (manager) state: {learner_state}

Respond ONLY with JSON:
{"speech": "...", "nonverbal": {"expression": "...", "posture": "..."}, "strategy_note": "..."}

Keep responses conversational, 2-4 sentences. Be realistic — neither a pushover nor impossible to reach."""

SCENARIO_STEPS = [
    {
        "step_id": "opening",
        "step_type": "situation",
        "order": 1,
        "situation_text": "You've called a 1:1 with Alex Rivera. Over the past two months, Alex has missed three sprint commitments. The team is starting to feel the impact. This is a critical conversation — Alex is talented but the pattern needs to change.",
        "input_expected": 0,
        "input_type": "none",
        "branch_conditions": json.dumps([]),
    },
    {
        "step_id": "conversation",
        "step_type": "question",
        "order": 2,
        "situation_text": "Alex just sat down. The meeting has started.",
        "input_expected": 1,
        "input_type": "text",
        "branch_conditions": json.dumps([
            {
                "predicate": {"type": "consecutive_errors", "min_count": 3},
                "next_step_id": "intervention",
            },
            {
                "predicate": {"type": "turn_count_above", "threshold": 8},
                "next_step_id": "debrief",
            },
        ]),
    },
    {
        "step_id": "intervention",
        "step_type": "reflection",
        "order": 3,
        "situation_text": "Coaching moment: Alex is becoming defensive. Try to refocus on specific behaviors and their impact rather than general criticism.",
        "input_expected": 1,
        "input_type": "text",
        "branch_conditions": json.dumps([
            {"predicate": {"type": "always"}, "next_step_id": "conversation"},
        ]),
    },
    {
        "step_id": "debrief",
        "step_type": "debrief",
        "order": 4,
        "situation_text": "The conversation has concluded. Time to reflect on how it went.",
        "input_expected": 0,
        "input_type": "none",
        "branch_conditions": json.dumps([]),
    },
]


def run():
    frappe.set_user("Administrator")

    node_names = []
    for node in COMPETENCY_NODES:
        existing = frappe.db.get_value("Competency Node", {"label": node["label"]}, "name")
        if existing:
            node_names.append(existing)
            print(f"  Skipping existing Competency Node: {existing} — {node['label']}")
            continue
        doc = frappe.get_doc({
            "doctype": "Competency Node",
            "label": node["label"],
            "description": node["description"],
            "modality_type": node["modality_type"],
            "mastery_threshold": node["mastery_threshold"],
            "bkt_params": json.dumps(BKT_DEFAULT),
        })
        doc.insert(ignore_permissions=True)
        node_names.append(doc.name)
        print(f"  Competency Node: {doc.name} — {node['label']}")

    # Create Agent Character
    existing_char = frappe.db.get_value("Agent Character", {"display_name": "Alex Rivera"}, "name")
    if existing_char:
        char_name = existing_char
        print(f"  Skipping existing Agent Character: {char_name}")
    else:
        char = frappe.get_doc({
            "doctype": "Agent Character",
            "display_name": "Alex Rivera",
            "instructional_role": "counterpart",
            "persona_description": "A talented but deadline-challenged software engineer. Starts defensive, opens up when treated with respect. Driven by unclear requirements and fear of escalation.",
            "voice_profile_id": "neutral_professional",
        })
        char.insert(ignore_permissions=True)
        char_name = char.name
        print(f"  Agent Character: {char_name} — Alex Rivera")

    # Create Training Scenario
    if frappe.db.exists("Training Scenario", {"title": "Difficult Conversation: Giving Constructive Feedback"}):
        print("  Training Scenario SCEN-0002 already exists, skipping.")
        frappe.db.commit()
        return

    scenario = frappe.get_doc({
        "doctype": "Training Scenario",
        "title": "Difficult Conversation: Giving Constructive Feedback",
        "modality": "negotiation_single",
        "version": "1.0.0",
        "description": "You are a manager who needs to address repeated deadline misses with a team member. Practice giving specific, empathetic feedback that leads to collaborative problem-solving.",
        "is_published": 0,
        "requires_pair": 0,
    })
    scenario.insert(ignore_permissions=True)

    # Add competency nodes as child rows
    for i, node_name in enumerate(node_names):
        frappe.get_doc({
            "doctype": "Scenario Competency Node",
            "parenttype": "Training Scenario",
            "parent": scenario.name,
            "parentfield": "competency_nodes",
            "competency_node": node_name,
            "weight": 1.0,
            "idx": i + 1,
        }).insert(ignore_permissions=True)

    # Add steps
    for step in SCENARIO_STEPS:
        frappe.get_doc({
            "doctype": "Scenario Step",
            "parenttype": "Training Scenario",
            "parent": scenario.name,
            "parentfield": "steps",
            "step_id": step["step_id"],
            "step_type": step["step_type"],
            "order": step["order"],
            "situation_text": step["situation_text"],
            "input_expected": step.get("input_expected", 1),
            "input_type": step.get("input_type", "text"),
            "branch_conditions": step["branch_conditions"],
            "idx": step["order"],
        }).insert(ignore_permissions=True)

    # Publish now that steps are attached
    frappe.db.set_value("Training Scenario", scenario.name, "is_published", 1)

    # Patch the modality engine_directives to include the new character
    frappe.db.set_value("Training Modality", "negotiation_single", "engine_directives", ENGINE_DIRECTIVES)
    frappe.db.commit()

    print(f"\nCreated Training Scenario: {scenario.name}")
    print(f"  Title: {scenario.title}")
    print(f"  Competency nodes: {len(node_names)}")
    print(f"  Agent: {char_name} (Alex Rivera)")
    print(f"\nTo try it, open:")
    print(f"  http://atp.localhost:8001/atp_session")
