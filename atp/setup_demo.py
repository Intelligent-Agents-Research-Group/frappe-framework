"""
ATP Demo Data Setup
===================
Creates demo educator + student accounts, a sample course, and enrollments
for local development and testing ONLY.

Usage:
    bench --site <site-name> execute atp.setup_demo.run

Accounts created:
    educator.demo@atp.local   password: Educator@123   role: ATP Educator
    student.anna@atp.local    password: Student@123    role: ATP Student  (in-progress)
    student.ben@atp.local     password: Student@123    role: ATP Student  (completed)
    student.chris@atp.local   password: Student@123    role: ATP Student  (not started)

IMPORTANT: Never run this in production. The script blocks execution unless
frappe.conf.developer_mode is truthy.
"""

import json
import frappe


# ── Demo account definitions ─────────────────────────────────────────────────

DEMO_EDUCATOR = {
    "email": "educator.demo@atp.local",
    "first_name": "Educator",
    "last_name": "Demo",
    "password": "Educator@123",
    "roles": ["ATP Educator"],
}

DEMO_STUDENTS = [
    {"email": "student.anna@atp.local",  "first_name": "Anna",  "last_name": "Chen",    "password": "Student@123"},
    {"email": "student.ben@atp.local",   "first_name": "Ben",   "last_name": "Okafor",  "password": "Student@123"},
    {"email": "student.chris@atp.local", "first_name": "Chris", "last_name": "Ramirez", "password": "Student@123"},
]

DEMO_COURSE_TITLE = "Introduction to Negotiation"

# Node layout for the sample course (x/y positions for the graph)
DEMO_NODES = [
    {"id": "demo_n1", "type": "PDF",           "label": "Welcome & Overview",        "x": 100,  "y": 100},
    {"id": "demo_n2", "type": "Video",          "label": "Negotiation Fundamentals",  "x": 350,  "y": 100},
    {"id": "demo_n3", "type": "Quiz",           "label": "Knowledge Check",           "x": 600,  "y": 100},
    {"id": "demo_n4", "type": "Task",           "label": "Role-Play Exercise",        "x": 850,  "y": 100},
    {"id": "demo_n5", "type": "Survey",         "label": "Self-Assessment",           "x": 1100, "y": 100},
    {"id": "demo_n6", "type": "Virtual Agent",  "label": "AI Negotiation Partner",   "x": 1350, "y": 100},
]

DEMO_EDGES = [
    ("demo_n1", "demo_n2"),
    ("demo_n2", "demo_n3"),
    ("demo_n3", "demo_n4"),
    ("demo_n4", "demo_n5"),
    ("demo_n5", "demo_n6"),
]


# ── Entry point ──────────────────────────────────────────────────────────────

def run():
    _guard()
    print("=== ATP Demo Setup ===")
    _ensure_roles()
    _create_user(DEMO_EDUCATOR["email"], DEMO_EDUCATOR["first_name"], DEMO_EDUCATOR["last_name"],
                 DEMO_EDUCATOR["password"], DEMO_EDUCATOR["roles"])
    for s in DEMO_STUDENTS:
        _create_user(s["email"], s["first_name"], s["last_name"], s["password"], ["ATP Student"])
    course_name = _create_course()
    _create_enrollments(course_name)
    frappe.db.commit()
    _print_summary(course_name)


# ── Internals ────────────────────────────────────────────────────────────────

def _guard():
    if not frappe.conf.get("developer_mode"):
        frappe.throw(
            "ATP demo setup only runs in developer mode. "
            "Set developer_mode = 1 in site_config.json first."
        )


def _ensure_roles():
    for role_name in ("ATP Educator", "ATP Student"):
        if not frappe.db.exists("Role", role_name):
            role = frappe.get_doc({"doctype": "Role", "role_name": role_name, "desk_access": 1})
            role.insert(ignore_permissions=True)
            print(f"  Created role: {role_name}")
        else:
            print(f"  Role exists: {role_name}")


def _create_user(email, first_name, last_name, password, roles):
    if frappe.db.exists("User", email):
        print(f"  User exists (skipped): {email}")
        return
    user = frappe.get_doc({
        "doctype": "User",
        "email": email,
        "first_name": first_name,
        "last_name": last_name,
        "enabled": 1,
        "send_welcome_email": 0,
        "new_password": password,
        "roles": [{"role": r} for r in roles],
    })
    user.insert(ignore_permissions=True)
    print(f"  Created user: {email}")


def _build_flow_data():
    nodes = []
    for n in DEMO_NODES:
        nodes.append({
            "id": n["id"],
            "type": "default",
            "label": n["label"],
            "position": {"x": n["x"], "y": n["y"]},
            "data": {
                "componentType": n["type"],
                "config": _default_config(n["type"], n["label"]),
            },
        })

    edges = []
    for idx, (src, tgt) in enumerate(DEMO_EDGES):
        edges.append({
            "id": f"demo_e{idx + 1}",
            "source": src,
            "target": tgt,
            "markerEnd": {"type": "arrowclosed"},
        })

    return json.dumps({"nodes": nodes, "edges": edges, "viewport": {"x": 0, "y": 0, "zoom": 0.85}})


def _default_config(component_type, label):
    """Return a minimal but illustrative default config per component type."""
    if component_type == "PDF":
        return {"fileUrl": "", "description": f"Read through the {label} document."}
    if component_type == "Video":
        return {"videoUrl": "", "description": f"Watch the {label} video."}
    if component_type == "Quiz":
        return {
            "questions": [
                {
                    "text": "What is the most important principle of principled negotiation?",
                    "options": ["Focus on positions", "Separate people from the problem", "Win at all costs", "Avoid compromise"],
                    "correct": 1,
                },
                {
                    "text": "BATNA stands for:",
                    "options": ["Best Alternative To a Negotiated Agreement", "Basic Approach To Negotiation Analysis", "Better Agreement Through Negotiated Approaches", "None of the above"],
                    "correct": 0,
                },
            ]
        }
    if component_type == "Task":
        return {
            "title": "Role-Play Exercise",
            "instructions": "Pair up with a partner. One person plays the buyer, the other the seller. Negotiate the price of a used car. Apply the principled negotiation techniques you have learned.",
            "completionCriteria": "Complete at least one full negotiation round.",
        }
    if component_type == "Survey":
        return {
            "questions": [
                {"text": "How confident do you feel about applying negotiation techniques?", "type": "scale"},
                {"text": "What aspect of negotiation do you want to practise more?", "type": "text"},
            ]
        }
    if component_type == "Virtual Agent":
        return {"agentUrl": "", "displayName": "AI Negotiation Partner", "description": "Practice negotiation with the AI agent."}
    return {}


def _create_course():
    if frappe.db.exists("Course", DEMO_COURSE_TITLE):
        print(f"  Course exists (skipped): {DEMO_COURSE_TITLE}")
        return DEMO_COURSE_TITLE

    flow_data = _build_flow_data()
    scene_config = json.dumps({
        "environment": {"background": "Boardroom", "mood": "Formal"},
        "agents": [{"name": "Dr. Rivera", "role": "Negotiation Coach", "avatarUrl": ""}],
        "persona": {"archetype": "Analytical", "modality": "Negotiation", "difficulty": 2},
    })

    course = frappe.get_doc({
        "doctype": "Course",
        "title": DEMO_COURSE_TITLE,
        "is_published": 1,
        "description": (
            "<p>This introductory course covers the fundamentals of principled negotiation. "
            "You will learn key frameworks, practise with interactive exercises, and engage "
            "with an AI negotiation partner to build your skills.</p>"
        ),
        "flow_data": flow_data,
        "scene_config": scene_config,
    })
    course.insert(ignore_permissions=True)
    print(f"  Created course: {DEMO_COURSE_TITLE}")
    return course.name


def _get_node_id(index):
    return DEMO_NODES[index]["id"]


def _create_enrollments(course_name):
    # Anna — In Progress at node 3 (Knowledge Check)
    _create_enrollment(
        course=course_name,
        student="student.anna@atp.local",
        status="In Progress",
        progress={"currentNodeId": _get_node_id(2)},  # node index 2 = demo_n3
    )

    # Ben — Completed
    _create_enrollment(
        course=course_name,
        student="student.ben@atp.local",
        status="Completed",
        progress={"currentNodeId": _get_node_id(5)},  # last node
    )

    # Chris — Not started (no progress)
    _create_enrollment(
        course=course_name,
        student="student.chris@atp.local",
        status="In Progress",
        progress=None,
    )


def _create_enrollment(course, student, status, progress):
    existing = frappe.db.exists("Course Enrollment", {"course": course, "student": student})
    if existing:
        print(f"  Enrollment exists (skipped): {student} → {course}")
        return

    enrollment = frappe.get_doc({
        "doctype": "Course Enrollment",
        "course": course,
        "student": student,
        "status": status,
        "enrolled_by": "educator.demo@atp.local",
        "progress": json.dumps(progress) if progress else None,
    })
    enrollment.insert(ignore_permissions=True)
    print(f"  Created enrollment: {student} → {course} [{status}]")


def _print_summary(course_name):
    print("")
    print("=== Demo setup complete ===")
    print("")
    print("Demo Accounts:")
    print(f"  educator.demo@atp.local   password: Educator@123   → Frappe Desk (ATP Educator)")
    print(f"  student.anna@atp.local    password: Student@123    → Student Dashboard (In Progress)")
    print(f"  student.ben@atp.local     password: Student@123    → Student Dashboard (Completed)")
    print(f"  student.chris@atp.local   password: Student@123    → Student Dashboard (Not Started)")
    print("")
    print(f"Demo Course: '{course_name}' (6 nodes)")
    print("")
    print("Test checklist:")
    print("  1. Login as student.anna → should land on /app/student_dashboard")
    print("  2. Click Continue on course → player loads at node 3 (Knowledge Check)")
    print("  3. Login as student.ben → course shows Completed badge")
    print("  4. Login as educator.demo → Desk access, open Enrollment Manager")
    print("  5. Open Course Builder for 'Introduction to Negotiation'")
