# Copyright (c) 2024, atp and contributors
# ATP public API — enrollment management and permission helpers

import frappe
from frappe import _


# ── Permission Helpers ───────────────────────────────────────────────────────

def get_enrollment_permission_query(user):
	"""Restrict ATP Students to see only their own Course Enrollments."""
	if not user:
		user = frappe.session.user
	roles = frappe.get_roles(user)
	if "ATP Student" in roles and "System Manager" not in roles and "ATP Educator" not in roles:
		return f"`tabCourse Enrollment`.`student` = {frappe.db.escape(user)}"
	return ""


# ── Student Account Management ───────────────────────────────────────────────

@frappe.whitelist()
def create_student(email, full_name, password):
	"""Create a single student Frappe User with the ATP Student role."""
	_require_educator()

	email = email.strip().lower()
	full_name = full_name.strip()

	if frappe.db.exists("User", email):
		frappe.throw(_(f"User {email} already exists."))

	names = full_name.split(" ", 1)
	first = names[0]
	last = names[1] if len(names) > 1 else ""

	user = frappe.get_doc({
		"doctype": "User",
		"email": email,
		"first_name": first,
		"last_name": last,
		"enabled": 1,
		"send_welcome_email": 0,
		"new_password": password,
		"roles": [{"role": "ATP Student"}],
	})
	user.insert(ignore_permissions=True)
	frappe.db.commit()
	return {"name": user.name, "email": user.email, "full_name": user.full_name}


@frappe.whitelist()
def bulk_create_students(students_json):
	"""
	Bulk-create student accounts.
	Expects a JSON string: [{"email": "...", "full_name": "...", "password": "..."}]
	Returns a summary dict with created/skipped lists.
	"""
	_require_educator()

	import json
	students = json.loads(students_json)
	created = []
	skipped = []

	for s in students:
		email = s.get("email", "").strip().lower()
		full_name = s.get("full_name", "").strip()
		password = s.get("password", "").strip()
		if not email or not full_name or not password:
			skipped.append({"email": email, "reason": "Missing fields"})
			continue
		if frappe.db.exists("User", email):
			skipped.append({"email": email, "reason": "Already exists"})
			continue
		names = full_name.split(" ", 1)
		first = names[0]
		last = names[1] if len(names) > 1 else ""
		user = frappe.get_doc({
			"doctype": "User",
			"email": email,
			"first_name": first,
			"last_name": last,
			"enabled": 1,
			"send_welcome_email": 0,
			"new_password": password,
			"roles": [{"role": "ATP Student"}],
		})
		user.insert(ignore_permissions=True)
		created.append({"email": email, "full_name": full_name})

	frappe.db.commit()
	return {"created": created, "skipped": skipped}


# ── Enrollment Management ────────────────────────────────────────────────────

@frappe.whitelist()
def enroll_student(course, student):
	"""Enroll a student in a course. Idempotent — safe to call twice."""
	_require_educator()

	existing = frappe.db.exists("Course Enrollment", {"course": course, "student": student})
	if existing:
		return {"name": existing, "status": "already_enrolled"}

	enrollment = frappe.get_doc({
		"doctype": "Course Enrollment",
		"course": course,
		"student": student,
		"status": "In Progress",
		"enrolled_by": frappe.session.user,
	})
	enrollment.insert(ignore_permissions=True)
	frappe.db.commit()
	return {"name": enrollment.name, "status": "enrolled"}


@frappe.whitelist()
def get_enrollment_overview(course):
	"""Return all enrollments for a course, enriched with student names."""
	_require_educator()

	enrollments = frappe.db.get_list(
		"Course Enrollment",
		filters={"course": course},
		fields=["name", "student", "status", "enrolled_by", "modified"],
		order_by="modified desc",
	)
	for e in enrollments:
		user_info = frappe.db.get_value(
			"User", e["student"], ["full_name", "email"], as_dict=True
		) or {}
		e["full_name"] = user_info.get("full_name") or e["student"]
		e["email"] = user_info.get("email") or e["student"]
	return enrollments


@frappe.whitelist()
def get_students():
	"""Return all users with the ATP Student role."""
	_require_educator()

	students = frappe.db.sql(
		"""
		SELECT u.name AS email, u.full_name, u.enabled
		FROM `tabUser` u
		INNER JOIN `tabHas Role` hr ON hr.parent = u.name
		WHERE hr.role = 'ATP Student' AND u.name NOT IN ('Guest', 'Administrator')
		ORDER BY u.full_name
		""",
		as_dict=True,
	)
	return students


@frappe.whitelist()
def update_progress(enrollment_name, current_node_id):
	"""Let a student persist their progress position in a course."""
	enrollment = frappe.get_doc("Course Enrollment", enrollment_name)
	if enrollment.student != frappe.session.user:
		frappe.throw(_("Not permitted"), frappe.PermissionError)
	import json
	enrollment.progress = json.dumps({"currentNodeId": current_node_id})
	enrollment.save(ignore_permissions=True)
	frappe.db.commit()
	return "ok"


@frappe.whitelist()
def complete_course(enrollment_name):
	"""Mark a course enrollment as Completed."""
	enrollment = frappe.get_doc("Course Enrollment", enrollment_name)
	if enrollment.student != frappe.session.user:
		frappe.throw(_("Not permitted"), frappe.PermissionError)
	enrollment.status = "Completed"
	enrollment.save(ignore_permissions=True)
	frappe.db.commit()
	return "ok"


@frappe.whitelist()
def get_educator_courses():
	"""Return all courses with enrollment counts for the educator dashboard."""
	_require_educator()

	courses = frappe.db.get_list(
		"Course",
		fields=["name", "title", "thumbnail", "description", "is_published"],
		order_by="modified desc",
	)

	for course in courses:
		course["enrollment_count"] = frappe.db.count(
			"Course Enrollment",
			filters={"course": course["name"]},
		)

	return courses


@frappe.whitelist()
def preview_course(course_name):
    """Educator previews their own course. Creates or reuses a self-enrollment."""
    _require_educator()

    existing = frappe.db.exists(
        "Course Enrollment",
        {"course": course_name, "student": frappe.session.user},
    )
    if existing:
        return {"name": existing}

    enrollment = frappe.get_doc({
        "doctype": "Course Enrollment",
        "course": course_name,
        "student": frappe.session.user,
        "status": "In Progress",
        "enrolled_by": frappe.session.user,
    })
    enrollment.insert(ignore_permissions=True)
    frappe.db.commit()
    return {"name": enrollment.name}


# ── Educator Credential Management ──────────────────────────────────────────

@frappe.whitelist()
def reset_student_password(student_email, new_password):
	"""Reset an ATP Student's password. Educator-only."""
	_require_educator()
	if not frappe.db.exists("User", student_email):
		frappe.throw(_(f"User {student_email} does not exist."))
	user = frappe.get_doc("User", student_email)
	roles = [r.role for r in user.roles]
	if "ATP Student" not in roles:
		frappe.throw(_("Can only reset passwords for ATP Student accounts."))
	user.new_password = new_password
	user.save(ignore_permissions=True)
	frappe.db.commit()
	return {"status": "ok"}


@frappe.whitelist()
def toggle_student_access(student_email, enabled):
	"""Enable or disable an ATP Student account. Educator-only."""
	_require_educator()
	if not frappe.db.exists("User", student_email):
		frappe.throw(_(f"User {student_email} does not exist."))
	user = frappe.get_doc("User", student_email)
	roles = [r.role for r in user.roles]
	if "ATP Student" not in roles:
		frappe.throw(_("Can only manage ATP Student accounts."))
	user.enabled = 1 if frappe.parse_json(enabled) else 0
	user.save(ignore_permissions=True)
	frappe.db.commit()
	return {"status": "ok", "enabled": user.enabled}


# ── Educator Analytics ────────────────────────────────────────────────────────

@frappe.whitelist()
def get_educator_analytics(course):
	"""
	Return detailed analytics for a course.
	Includes per-student progress, summary stats, and node distribution.
	"""
	_require_educator()
	import json as _json

	enrollments = frappe.db.get_list(
		"Course Enrollment",
		filters={"course": course},
		fields=["name", "student", "status", "progress", "modified"],
		order_by="modified desc",
	)

	flow_data_str = frappe.db.get_value("Course", course, "flow_data")
	total_nodes = 0
	node_labels = []
	if flow_data_str:
		try:
			flow = _json.loads(flow_data_str)
			nodes = flow.get("nodes", [])
			total_nodes = len(nodes)
			node_labels = [n.get("label", f"Node {i + 1}") for i, n in enumerate(nodes)]
		except Exception:
			pass

	node_distribution = [0] * total_nodes

	students_data = []
	for e in enrollments:
		user_info = frappe.db.get_value(
			"User", e["student"], ["full_name", "email"], as_dict=True
		) or {}

		progress_pct = 0
		current_node_idx = -1

		if e["status"] == "Completed":
			progress_pct = 100
			current_node_idx = total_nodes - 1 if total_nodes > 0 else -1
		elif e["progress"] and flow_data_str:
			try:
				flow = _json.loads(flow_data_str)
				prog = _json.loads(e["progress"])
				node_id = prog.get("currentNodeId")
				f_nodes = flow.get("nodes", [])
				idx = next((i for i, n in enumerate(f_nodes) if n["id"] == node_id), -1)
				if idx >= 0 and total_nodes > 0:
					progress_pct = round((idx / total_nodes) * 100)
					current_node_idx = idx
			except Exception:
				pass

		if 0 <= current_node_idx < total_nodes:
			node_distribution[current_node_idx] += 1

		current_node_label = (
			node_labels[current_node_idx]
			if 0 <= current_node_idx < len(node_labels)
			else ("Completed" if e["status"] == "Completed" else "Not started")
		)

		students_data.append({
			"enrollment_name": e["name"],
			"student": e["student"],
			"full_name": user_info.get("full_name") or e["student"],
			"email": user_info.get("email") or e["student"],
			"status": e["status"],
			"progress_pct": progress_pct,
			"current_node_idx": current_node_idx,
			"current_node_label": current_node_label,
			"last_active": str(e["modified"]),
		})

	total = len(students_data)
	completed = sum(1 for s in students_data if s["status"] == "Completed")
	in_progress_count = sum(
		1 for s in students_data if s["status"] != "Completed" and s["progress_pct"] > 0
	)
	not_started = total - completed - in_progress_count
	avg_progress = round(sum(s["progress_pct"] for s in students_data) / total) if total > 0 else 0
	completion_rate = round((completed / total) * 100) if total > 0 else 0

	return {
		"total": total,
		"completed": completed,
		"in_progress": in_progress_count,
		"not_started": not_started,
		"avg_progress": avg_progress,
		"completion_rate": completion_rate,
		"total_nodes": total_nodes,
		"node_labels": node_labels,
		"node_distribution": node_distribution,
		"students": students_data,
	}


@frappe.whitelist()
def get_analytics_courses():
	"""Return all courses with basic enrollment stats for the analytics course picker."""
	_require_educator()
	courses = frappe.db.get_list(
		"Course",
		fields=["name", "title", "is_published"],
		order_by="modified desc",
	)
	for c in courses:
		c["enrollment_count"] = frappe.db.count("Course Enrollment", filters={"course": c["name"]})
	return courses


# ── Student Enrollments (educator view) ─────────────────────────────────────

@frappe.whitelist()
def get_student_enrollments(student_email):
	"""Return all course enrollments for a specific student (educator view)."""
	_require_educator()
	import json as _json

	enrollments = frappe.db.get_list(
		"Course Enrollment",
		filters={"student": student_email},
		fields=["name", "course", "status", "progress", "modified"],
		order_by="modified desc",
	)

	result = []
	for e in enrollments:
		course_title = frappe.db.get_value("Course", e["course"], "title") or e["course"]
		flow_data_str = frappe.db.get_value("Course", e["course"], "flow_data")

		progress_pct = 0
		if e["status"] == "Completed":
			progress_pct = 100
		elif e["progress"] and flow_data_str:
			try:
				flow = _json.loads(flow_data_str)
				prog = _json.loads(e["progress"])
				node_id = prog.get("currentNodeId")
				nodes = flow.get("nodes", [])
				total = len(nodes)
				idx = next((i for i, n in enumerate(nodes) if n["id"] == node_id), -1)
				if idx >= 0 and total > 0:
					progress_pct = round((idx / total) * 100)
			except Exception:
				pass

		result.append({
			"name": e["name"],
			"course": e["course"],
			"course_title": course_title,
			"status": e["status"],
			"progress_pct": progress_pct,
			"modified": str(e["modified"]),
		})

	return result


# ── Admin APIs ──────────────────────────────────────────────────────────────

@frappe.whitelist()
def get_admin_stats():
	"""System-wide counts for the admin dashboard."""
	_require_admin()
	students = frappe.db.sql(
		"SELECT COUNT(DISTINCT parent) FROM `tabHas Role` WHERE role='ATP Student' AND parenttype='User'",
	)[0][0]
	educators = frappe.db.sql(
		"SELECT COUNT(DISTINCT parent) FROM `tabHas Role` WHERE role='ATP Educator' AND parenttype='User'",
	)[0][0]
	courses = frappe.db.count("Course")
	enrollments = frappe.db.count("Course Enrollment")
	return {"students": students, "educators": educators, "courses": courses, "enrollments": enrollments}


@frappe.whitelist()
def get_all_users():
	"""All users with ATP Student or ATP Educator role."""
	_require_admin()
	rows = frappe.db.sql(
		"""
		SELECT u.name AS email, u.full_name, u.enabled, hr.role
		FROM `tabUser` u
		INNER JOIN `tabHas Role` hr ON hr.parent = u.name AND hr.parenttype = 'User'
		WHERE hr.role IN ('ATP Student', 'ATP Educator')
		  AND u.name NOT IN ('Guest', 'Administrator')
		ORDER BY hr.role, u.full_name
		""",
		as_dict=True,
	)
	return rows


@frappe.whitelist()
def add_atp_user(email, full_name, role, password):
	"""Create a new user with the given ATP role."""
	_require_admin()
	email = email.strip().lower()
	full_name = full_name.strip()
	if role not in ("ATP Student", "ATP Educator"):
		frappe.throw(_("Invalid role."))
	if frappe.db.exists("User", email):
		# User exists — just add the role if not present
		user = frappe.get_doc("User", email)
		existing_roles = [r.role for r in user.roles]
		if role not in existing_roles:
			user.append("roles", {"role": role})
			user.save(ignore_permissions=True)
			frappe.db.commit()
		return {"name": user.name, "status": "role_added"}
	names = full_name.split(" ", 1)
	user = frappe.get_doc({
		"doctype": "User",
		"email": email,
		"first_name": names[0],
		"last_name": names[1] if len(names) > 1 else "",
		"enabled": 1,
		"send_welcome_email": 0,
		"new_password": password,
		"roles": [{"role": role}],
	})
	user.insert(ignore_permissions=True)
	frappe.db.commit()
	return {"name": user.name, "status": "created"}


@frappe.whitelist()
def get_all_courses_admin():
	"""All courses from all educators with enrollment counts."""
	_require_admin()
	courses = frappe.db.get_list(
		"Course",
		fields=["name", "title", "thumbnail", "is_published", "owner"],
		order_by="modified desc",
	)
	for c in courses:
		c["enrollment_count"] = frappe.db.count("Course Enrollment", filters={"course": c["name"]})
		c["owner_name"] = frappe.db.get_value("User", c["owner"], "full_name") or c["owner"]
	return courses


# ── Post-Login Routing ───────────────────────────────────────────────────────

def _atp_dashboard_for(user):
	"""Return the correct ATP desk URL for a user, or None if not an ATP user."""
	roles = frappe.get_roles(user)
	# System Manager (admin) takes priority
	if "System Manager" in roles:
		return "/desk/atp_admin"
	if "ATP Educator" in roles:
		return "/desk/educator_dashboard"
	if "ATP Student" in roles:
		return "/desk/student_dashboard"
	return None


def atp_before_request():
	"""
	Redirect already-logged-in ATP users away from /login (and the bare desk
	root) to their correct dashboard.

	When a user with a live session visits /login, Frappe's login.py
	get_context() fires a server-side redirect using get_default_path() or
	"/desk" — completely bypassing the after_request hook.  This before_request
	hook intercepts those paths first.

	We raise werkzeug.exceptions.Found (302) rather than frappe.Redirect because
	before_request runs inside init_request(), which is inside the application()
	try/except that only catches HTTPException via e.get_response().
	frappe.Redirect is not an HTTPException and would surface as a 500 error.
	"""
	from werkzeug.routing import RequestRedirect

	user = getattr(frappe.session, "user", None)
	if not user or user == "Guest":
		return

	path = frappe.local.request.path
	if frappe.local.request.method != "GET":
		return
	# Only intercept entry-point paths, not arbitrary desk pages
	if path not in ("/login", "/", "/desk", "/desk/"):
		return

	dest = _atp_dashboard_for(user)
	if dest:
		raise RequestRedirect(dest)


def atp_post_login_redirect(response=None, **kwargs):
	"""
	Override the post-login home_page in the login JSON response so the
	browser navigates to the correct ATP dashboard on fresh login.

	Frappe's build_response("json") serialises frappe.local.response into the
	HTTP body BEFORE after_request runs, so we mutate the already-built
	Werkzeug response object directly.

	Root cause: ATP roles have desk_access=1 (System Users), so set_user_info()
	sets home_page = get_default_path() or "/desk". Since ATP has no
	add_to_apps_screen entry, get_default_path() returns None → everyone hits
	/desk. role_home_page hook is never consulted for System Users.
	"""
	if response is None:
		return

	# Only JSON responses from the login command carry home_page
	content_type = response.headers.get("Content-Type", "")
	if "json" not in content_type:
		return

	try:
		import json
		data = json.loads(response.data)
	except Exception:
		return

	if data.get("message") != "Logged In":
		return

	user = frappe.session.user
	if not user or user == "Guest":
		return

	dest = _atp_dashboard_for(user)
	if dest:
		data["home_page"] = dest
		response.data = json.dumps(data).encode("utf-8")


# ── Internal Helpers ─────────────────────────────────────────────────────────

def _require_educator():
	roles = frappe.get_roles(frappe.session.user)
	if "ATP Educator" not in roles and "System Manager" not in roles:
		frappe.throw(_("Only educators can perform this action."), frappe.PermissionError)


def _require_admin():
	roles = frappe.get_roles(frappe.session.user)
	if "System Manager" not in roles:
		frappe.throw(_("Only administrators can perform this action."), frappe.PermissionError)
