# Copyright (c) 2026, Ascra Technologies LLP and contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

TEAMS = ["Trading", "Clearing", "IT", "Compliance"]

ISSUE_TYPES = [
	("Trading - Order Entry", "Medium", "Trading"),
	("Trading - Margin Query", "Medium", "Trading"),
	("Clearing - Settlement", "High", "Clearing"),
	("Clearing - Payout", "High", "Clearing"),
	("IT - Portal Access", "High", "IT"),
	("IT - System Downtime", "Urgent", "IT"),
	("Compliance - Reporting", "Medium", "Compliance"),
	("Compliance - KYC", "High", "Compliance"),
]

SUB_ISSUE_TYPES = [
	("Order Rejection", "Trading - Order Entry"),
	("Price Mismatch", "Trading - Margin Query"),
	("Settlement Delay", "Clearing - Settlement"),
	("Payout Pending", "Clearing - Payout"),
	("Login Issue", "IT - Portal Access"),
	("Password Reset", "IT - Portal Access"),
	("System Outage", "IT - System Downtime"),
	("Regulatory Filing", "Compliance - Reporting"),
	("KYC Update", "Compliance - KYC"),
]

DEMO_AGENTS = [
	{"email": "souravsingh2609@gmail.com", "full_name": "Sourav Singh", "team": "IT"},
	{"email": "mcx.trading.agent@demo.com", "full_name": "MCX Trading Agent", "team": "Trading"},
	{"email": "mcx.clearing.agent@demo.com", "full_name": "MCX Clearing Agent", "team": "Clearing"},
	{"email": "mcx.compliance.agent@demo.com", "full_name": "MCX Compliance Agent", "team": "Compliance"},
]


def after_install():
	from mcx_helpdesk.setup.sync import sync_mcx_helpdesk

	sync_mcx_helpdesk()


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
					"in_list_view": 1,
					"in_standard_filter": 1,
					"depends_on": "eval:doc.ticket_type != ''",
					"link_filters": '[["HD Sub Issue Type","issue_type","=","eval:doc.ticket_type"]]',
				}
			]
		},
		ignore_validate=True,
		update=True,
	)


def ensure_custom_field_metadata():
	"""Keep Custom Field flags aligned with fixtures after install/migrate."""
	name = "HD Ticket-sub_issue_type"
	if not frappe.db.exists("Custom Field", name):
		return
	frappe.db.set_value(
		"Custom Field",
		name,
		{
			"depends_on": "eval:doc.ticket_type != ''",
			"link_filters": '[["HD Sub Issue Type","issue_type","=","eval:doc.ticket_type"]]',
			"module": "MCX Helpdesk",
			"label": "Sub Issue Type",
		},
	)


def ensure_ticket_template_field():
	"""Register Sub Issue Type on Default template so Helpdesk desk UI shows it."""
	if not frappe.db.exists("HD Ticket Template", "Default"):
		return

	template = frappe.get_doc("HD Ticket Template", "Default")
	existing = {row.fieldname for row in template.fields}
	if "sub_issue_type" in existing:
		return

	template.append(
		"fields",
		{
			"fieldname": "sub_issue_type",
			"required": 0,
			"hide_from_customer": 0,
			"placeholder": "Select sub issue for the chosen issue type",
		},
	)
	template.save(ignore_permissions=True)


def get_sub_issue_mapping():
	mapping: dict[str, list[str]] = {}
	for sub_issue_name, issue_type in SUB_ISSUE_TYPES:
		mapping.setdefault(issue_type, []).append(sub_issue_name)
	return mapping


def ensure_sub_issue_field_dependency():
	"""Filter Sub Issue Type options by selected Issue Type in Helpdesk UI."""
	from helpdesk.api.settings.field_dependency import create_update_field_dependency

	mapping = get_sub_issue_mapping()
	fields_criteria = {
		"display": {"enabled": True, "value": [{"label": "Any", "value": "Any"}]},
		"mandatory": {"enabled": False, "value": []},
	}

	create_update_field_dependency(
		parent_field="ticket_type",
		child_field="sub_issue_type",
		parent_child_mapping=frappe.as_json(mapping),
		enabled=True,
		fields_criteria=frappe.as_json(fields_criteria),
	)


def ensure_labels():
	labels = [
		("HD Ticket", "ticket_type", "Issue Type"),
		("HD Ticket", "agent_group", "Department"),
		("HD Team", "team_name", "Department Name"),
	]
	for doctype, fieldname, label in labels:
		name = f"{doctype}-{fieldname}-label"
		if frappe.db.exists("Property Setter", name):
			frappe.db.set_value("Property Setter", name, "value", label)
			continue
		frappe.get_doc(
			{
				"doctype": "Property Setter",
				"doctype_or_field": "DocField",
				"doc_type": doctype,
				"field_name": fieldname,
				"property": "label",
				"property_type": "Data",
				"value": label,
				"module": "MCX Helpdesk",
			}
		).insert(ignore_permissions=True)


def ensure_issue_types():
	for name, priority, _team in ISSUE_TYPES:
		if frappe.db.exists("HD Ticket Type", name):
			frappe.db.set_value("HD Ticket Type", name, "priority", priority)
			continue
		frappe.get_doc({"doctype": "HD Ticket Type", "name": name, "priority": priority}).insert(
			ignore_permissions=True
		)


def ensure_sub_issue_types():
	for sub_issue_name, issue_type in SUB_ISSUE_TYPES:
		if frappe.db.exists("HD Sub Issue Type", sub_issue_name):
			frappe.db.set_value("HD Sub Issue Type", sub_issue_name, "issue_type", issue_type)
			continue
		frappe.get_doc(
			{
				"doctype": "HD Sub Issue Type",
				"sub_issue_name": sub_issue_name,
				"issue_type": issue_type,
			}
		).insert(ignore_permissions=True)


def disable_legacy_teams():
	for team in ["Billing", "Product Experts"]:
		if not frappe.db.exists("HD Team", team):
			continue
		frappe.db.set_value("HD Team", team, "disabled", 1)
		assignment_rule = frappe.db.get_value("HD Team", team, "assignment_rule")
		if assignment_rule:
			frappe.db.set_value("Assignment Rule", assignment_rule, "disabled", 1)


def setup_demo_agents_and_teams():
	team_users: dict[str, list[str]] = {team: [] for team in TEAMS}

	for agent in DEMO_AGENTS:
		ensure_user(agent["email"], agent["full_name"])
		ensure_agent(agent["email"], agent["full_name"])
		team = agent["team"]
		if team in team_users:
			team_users[team].append(agent["email"])

	for team in TEAMS:
		users = team_users.get(team, [])
		if users:
			ensure_team(team, users)
		elif frappe.db.exists("HD Team", team):
			frappe.db.set_value("HD Team", team, "disabled", 1)


def ensure_user(email, full_name):
	if frappe.db.exists("User", email):
		user = frappe.get_doc("User", email)
		user.enabled = 1
		user.full_name = full_name
		user.save(ignore_permissions=True)
		if "Agent" not in frappe.get_roles(email):
			user.add_roles("Agent", "Desk User")
		return user

	user = frappe.get_doc(
		{
			"doctype": "User",
			"email": email,
			"first_name": full_name,
			"enabled": 1,
			"send_welcome_email": 0,
			"new_password": "demo@123",
		}
	)
	user.insert(ignore_permissions=True)
	user.add_roles("Agent", "Desk User")
	return user


def ensure_agent(user_email, full_name=None):
	if frappe.db.exists("HD Agent", user_email):
		frappe.db.set_value("HD Agent", user_email, "is_active", 1)
		return
	if not full_name:
		full_name = frappe.db.get_value("User", user_email, "full_name") or user_email
	frappe.get_doc(
		{"doctype": "HD Agent", "user": user_email, "agent_name": full_name}
	).insert(ignore_permissions=True)


def ensure_team(name, users):
	if frappe.db.exists("HD Team", name):
		team = frappe.get_doc("HD Team", name)
	else:
		team = frappe.get_doc({"doctype": "HD Team", "team_name": name})

	team.disabled = 0
	team.users = []
	for user in users:
		team.append("users", {"user": user})
	team.save(ignore_permissions=True)


def configure_email_account():
	for account_name in frappe.get_all(
		"Email Account", filters={"enable_incoming": 1}, pluck="name"
	):
		ea = frappe.get_doc("Email Account", account_name)
		ea.enable_incoming = 1
		ea.enable_outgoing = 1
		ea.create_contact = 1
		ea.track_email_status = 1

		if ea.use_imap:
			if not ea.imap_folder:
				ea.append("imap_folder", {"folder_name": "INBOX", "append_to": "HD Ticket"})
			else:
				for folder in ea.imap_folder:
					folder.append_to = "HD Ticket"

		ea.save(ignore_permissions=True)


def configure_hd_settings():
	settings = frappe.get_doc("HD Settings", "HD Settings")
	settings.default_ticket_type = "IT - Portal Access"
	settings.send_acknowledgement_email = 1
	settings.restrict_tickets_by_agent_group = 1
	settings.do_not_restrict_tickets_without_an_agent_group = 0
	if not settings.acknowledgement_email_content:
		settings.acknowledgement_email_content = (
			"<p>Dear Member,</p>"
			"<p>Your request has been received and registered as ticket "
			"<strong>{{ doc.name }}</strong>.</p>"
			"<p>Our support team will respond shortly.</p>"
			"<p>Regards,<br>MCX Support</p>"
		)
	settings.save(ignore_permissions=True)
