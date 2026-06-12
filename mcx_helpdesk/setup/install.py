# Copyright (c) 2026, Ascra Technologies LLP and contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

from mcx_helpdesk.constants import ISSUE_TYPES, LEGACY_TEAMS, SUB_ISSUE_TYPES


def ensure_custom_fields():
	create_custom_fields(
		{
			"HD Ticket": [
				{
					"fieldname": "sub_issue_type",
					"label": "Sub Issue Type",
					"fieldtype": "Link",
					"options": "HD Sub Issue Type",
					"insert_after": "ticket_type",
					"depends_on": "eval:doc.ticket_type != ''",
					"in_list_view": 1,
					"in_standard_filter": 1,
				}
			]
		},
		ignore_validate=True,
	)


def ensure_custom_field_metadata():
	"""Ensure Custom Field row exists with correct depends_on (fixtures may omit it)."""
	if not frappe.db.exists("Custom Field", "HD Ticket-sub_issue_type"):
		return
	frappe.db.set_value(
		"Custom Field",
		"HD Ticket-sub_issue_type",
		{
			"depends_on": "eval:doc.ticket_type != ''",
			"in_list_view": 1,
			"in_standard_filter": 1,
		},
	)


def ensure_labels():
	labels = {
		"HD Ticket-agent_group": "Department",
		"HD Ticket-ticket_type": "Issue Type",
		"HD Ticket-agent_group_name": "Department Name",
	}
	for key, label in labels.items():
		doctype, fieldname = key.split("-", 1)
		setter_name = f"{doctype}-{fieldname}-label"
		if frappe.db.exists("Property Setter", setter_name):
			frappe.db.set_value("Property Setter", setter_name, "value", label)
			continue
		frappe.make_property_setter(
			{
				"doctype": doctype,
				"fieldname": fieldname,
				"property": "label",
				"value": label,
				"property_type": "Data",
			},
			ignore_validate=True,
		)


def ensure_issue_types():
	for name, priority, _team in ISSUE_TYPES:
		if frappe.db.exists("HD Ticket Type", name):
			continue
		doc = frappe.get_doc(
			{
				"doctype": "HD Ticket Type",
				"priority": priority,
				"is_system": 0,
			}
		)
		doc.name = name
		doc.insert(ignore_permissions=True)


def ensure_sub_issue_types():
	for sub_name, issue_type in SUB_ISSUE_TYPES:
		if not frappe.db.exists("HD Ticket Type", issue_type):
			continue
		if frappe.db.exists("HD Sub Issue Type", sub_name):
			continue
		frappe.get_doc(
			{
				"doctype": "HD Sub Issue Type",
				"sub_issue_name": sub_name,
				"issue_type": issue_type,
			}
		).insert(ignore_permissions=True)


def ensure_ticket_template_field():
	if not frappe.db.exists("HD Ticket Template", "Default"):
		return
	template = frappe.get_doc("HD Ticket Template", "Default")
	if any(row.fieldname == "sub_issue_type" for row in template.fields):
		return
	template.append(
		"fields",
		{
			"label": "Sub Issue Type",
			"fieldname": "sub_issue_type",
			"fieldtype": "Link",
			"options": "HD Sub Issue Type",
			"required": 0,
		},
	)
	template.save(ignore_permissions=True)


def ensure_sub_issue_field_dependency():
	"""Ensure cascading filter script exists (fixture is primary source)."""
	script_name = "Field Dependency-ticket_type-sub_issue_type"
	if frappe.db.exists("HD Form Script", script_name):
		return

	try:
		from helpdesk.api.settings.field_dependency import create_update_field_dependency
	except ImportError:
		return

	from collections import defaultdict

	mapping: dict[str, list[str]] = defaultdict(list)
	for sub_name, issue_type in SUB_ISSUE_TYPES:
		mapping[issue_type].append(sub_name)

	fields_criteria = {
		"display": {"enabled": True, "value": [{"label": "Any", "value": "Any"}]},
		"mandatory": {"enabled": False, "value": []},
	}

	create_update_field_dependency(
		"ticket_type",
		"sub_issue_type",
		frappe.as_json(dict(mapping)),
		True,
		frappe.as_json(fields_criteria),
	)


def disable_legacy_teams():
	for team in LEGACY_TEAMS:
		if frappe.db.exists("HD Team", team):
			frappe.db.set_value("HD Team", team, "disabled", 1)


def ensure_user(email: str, full_name: str, password: str = "demo@123"):
	if frappe.db.exists("User", email):
		return
	user = frappe.get_doc(
		{
			"doctype": "User",
			"email": email,
			"first_name": full_name,
			"send_welcome_email": 0,
			"user_type": "System User",
		}
	)
	user.new_password = password
	user.insert(ignore_permissions=True)
	user.add_roles("Agent", "Helpdesk Agent")


def ensure_agent(email: str, full_name: str):
	if frappe.db.exists("HD Agent", email):
		return
	frappe.get_doc(
		{
			"doctype": "HD Agent",
			"user": email,
			"agent_name": full_name,
		}
	).insert(ignore_permissions=True)


def ensure_team(name: str, users: list[str]):
	if frappe.db.exists("HD Team", name):
		doc = frappe.get_doc("HD Team", name)
		doc.disabled = 0
		doc.users = []
	else:
		doc = frappe.get_doc({"doctype": "HD Team", "team_name": name, "disabled": 0})

	for user in users:
		doc.append("users", {"user": user})

	doc.save(ignore_permissions=True)


def configure_email_account():
	"""Point incoming mail at HD Ticket (demo sites)."""
	for account in frappe.get_all("Email Account", filters={"enable_incoming": 1}, pluck="name"):
		doc = frappe.get_doc("Email Account", account)
		if doc.append_to == "HD Ticket":
			continue
		doc.append_to = "HD Ticket"
		doc.save(ignore_permissions=True)


def configure_hd_settings(force_ack_template: bool = False):
	"""Set HD Settings defaults; only overwrite ack template when explicitly requested."""
	settings = frappe.get_doc("HD Settings", "HD Settings")
	changed = False

	if not settings.default_ticket_type:
		settings.default_ticket_type = "IT - Portal Access"
		changed = True
	if not settings.default_priority:
		settings.default_priority = "Medium"
		changed = True
	if force_ack_template or not settings.auto_acknowledgement_email_template:
		settings.auto_acknowledgement_email_template = "Acknowledgement"
		changed = True

	if changed:
		settings.save(ignore_permissions=True)
