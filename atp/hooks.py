app_name = "atp"
app_title = "ATP"
app_publisher = "atp"
app_description = "Adaptive Training Platform"
app_email = "atp@example.com"
app_license = "mit"

# Apps
# ------------------

# required_apps = []

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "atp",
# 		"logo": "/assets/atp/logo.png",
# 		"title": "Atp",
# 		"route": "/atp",
# 		"has_permission": "atp.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
app_include_css = "/assets/atp/css/atp.css"
# app_include_js = "/assets/atp/js/atp.js"

# include js, css files in header of web template (login page branding)
web_include_css = "/assets/atp/css/atp-login.css"
web_include_js = "/assets/atp/js/atp-login.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "atp/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "atp/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
role_home_page = {
    "ATP Student": "student_dashboard",
    "ATP Educator": "educator_dashboard",
    "System Manager": "atp_admin",
    "Administrator": "atp_admin",
}

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# automatically load and sync documents of this doctype from downstream apps
# importable_doctypes = [doctype_1]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "atp.utils.jinja_methods",
# 	"filters": "atp.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "atp.install.before_install"
# after_install = "atp.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "atp.uninstall.before_uninstall"
# after_uninstall = "atp.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "atp.utils.before_app_install"
# after_app_install = "atp.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "atp.utils.before_app_uninstall"
# after_app_uninstall = "atp.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "atp.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

permission_query_conditions = {
    "Course Enrollment": "atp.atp.api.get_enrollment_permission_query",
}

# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# Document Events
# ---------------
# Hook on document methods and events


# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"atp.tasks.all"
# 	],
# 	"daily": [
# 		"atp.tasks.daily"
# 	],
# 	"hourly": [
# 		"atp.tasks.hourly"
# 	],
# 	"weekly": [
# 		"atp.tasks.weekly"
# 	],
# 	"monthly": [
# 		"atp.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "atp.install.before_tests"

# Extend DocType Class
# ------------------------------
#
# Specify custom mixins to extend the standard doctype controller.
# extend_doctype_class = {
# 	"Task": "atp.custom.task.CustomTaskMixin"
# }

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "atp.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "atp.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
before_request = ["atp.atp.api.atp_before_request"]
after_request = ["atp.atp.api.atp_post_login_redirect"]

# Job Events
# ----------
# before_job = ["atp.utils.before_job"]
# after_job = ["atp.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"atp.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

# Translation
# ------------
# List of apps whose translatable strings should be excluded from this app's translations.
# ignore_translatable_strings_from = []

# Fixtures
# --------
fixtures = [
    {"doctype": "Role", "filters": [["name", "in", ["ATP Educator", "ATP Student"]]]},
]

