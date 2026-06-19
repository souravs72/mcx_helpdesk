# Copyright (c) 2026, Ascra Technologies LLP and contributors
# For license information, please see license.txt

"""Auto-setup MCX escalation fields and sync Helpdesk escalation rules from desk settings."""

from __future__ import annotations

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

from mcx_helpdesk.constants import PRIORITY_LADDER, TEAMS
from mcx_helpdesk.setup.demo import is_demo_mode_enabled
from mcx_helpdesk.setup.install import ensure_agent, ensure_user


# Demo-only supervisor matrix — never used in production after initial desk setup.
DEMO_ESCALATION_RULES = [
	{"team": "IT", "l1_user": "souravsingh2609@gmail.com", "l2_user": "mcx.it.head@demo.com"},
	{"team": "Trading", "l1_user": "mcx.trading.supervisor@demo.com", "l2_user": "mcx.trading.head@demo.com"},
	{"team": "Clearing", "l1_user": "mcx.clearing.supervisor@demo.com", "l2_user": "mcx.clearing.head@demo.com"},
	{"team": "Compliance", "l1_user": "mcx.compliance.supervisor@demo.com", "l2_user": "mcx.compliance.head@demo.com"},
]

DEMO_COUNTRY_HEAD = "mcx.country.head@demo.com"
DEMO_DEPUTY_COUNTRY_HEAD = "mcx.country.head.backup@demo.com"

DEMO_ESCALATION_USERS = [
	("souravsingh2609@gmail.com", "IT Supervisor"),
	("mcx.it.head@demo.com", "IT Department Head"),
	("mcx.trading.supervisor@demo.com", "Trading Supervisor"),
	("mcx.trading.head@demo.com", "Trading Department Head"),
	("mcx.clearing.supervisor@demo.com", "Clearing Supervisor"),
	("mcx.clearing.head@demo.com", "Clearing Department Head"),
	("mcx.compliance.supervisor@demo.com", "Compliance Supervisor"),
	("mcx.compliance.head@demo.com", "Compliance Department Head"),
	("mcx.country.head@demo.com", "MCX Country Head"),
	("mcx.country.head.backup@demo.com", "MCX Deputy Country Head"),
]


def ensure_escalation_custom_fields():
	create_custom_fields(
		{
			"HD Ticket": [
				{
					"fieldname": "mcx_escalation_level",
					"label": "Escalation Level",
					"fieldtype": "Int",
					"insert_after": "agreement_status",
					"read_only": 1,
					"default": "0",
					"description": "Number of SLA breach escalations applied to this ticket",
				},
				{
					"fieldname": "mcx_last_escalated_on",
					"label": "Last Escalated On",
					"fieldtype": "Datetime",
					"insert_after": "mcx_escalation_level",
					"read_only": 1,
				},
				{
					"fieldname": "mcx_sla_breach_escalated",
					"label": "SLA Breach Escalated",
					"fieldtype": "Check",
					"insert_after": "mcx_last_escalated_on",
					"hidden": 1,
					"default": "0",
				},
			]
		},
		ignore_validate=True,
	)


def ensure_escalation_settings_doc():
	"""Ensure MCX Escalation Settings single exists; seed demo rows only on demo sites."""
	if not frappe.db.exists("DocType", "MCX Escalation Settings"):
		return
	if frappe.db.exists("MCX Escalation Settings", "MCX Escalation Settings"):
		return

	doc = frappe.get_doc(
		{
			"doctype": "MCX Escalation Settings",
			"enabled": 1,
			"reescalate_after_hours": 4,
		}
	)

	if is_demo_mode_enabled():
		doc.country_head_user = DEMO_COUNTRY_HEAD
		doc.deputy_country_head_user = DEMO_DEPUTY_COUNTRY_HEAD
		for row in DEMO_ESCALATION_RULES:
			doc.append("escalation_rules", row)

	doc.insert(ignore_permissions=True)


def ensure_escalation_users():
	"""Create demo supervisor users when demo mode is on."""
	if not is_demo_mode_enabled():
		_ensure_existing_supervisor_agents()
		return

	for email, full_name in DEMO_ESCALATION_USERS:
		ensure_user(email, full_name)
		ensure_agent(email, full_name)


def _ensure_existing_supervisor_agents():
	"""Ensure HD Agent exists for supervisors already configured in desk settings."""
	if not frappe.db.exists("DocType", "MCX Escalation Settings"):
		return
	if not frappe.db.exists("MCX Escalation Settings", "MCX Escalation Settings"):
		return

	settings = frappe.get_single("MCX Escalation Settings")
	for row in settings.escalation_rules:
		for user in (row.l1_user, row.l2_user):
			if user and frappe.db.exists("User", user):
				name = frappe.db.get_value("User", user, "full_name") or user
				ensure_agent(user, name)
	for user in (settings.country_head_user, settings.deputy_country_head_user):
		if user and frappe.db.exists("User", user):
			name = frappe.db.get_value("User", user, "full_name") or user
			ensure_agent(user, name)


def ensure_hd_escalation_rules():
	"""Sync native HD Escalation Rules from MCX Escalation Settings (L1 per team)."""
	if not frappe.db.exists("DocType", "MCX Escalation Settings"):
		return
	if not frappe.db.exists("MCX Escalation Settings", "MCX Escalation Settings"):
		return

	settings = frappe.get_single("MCX Escalation Settings")
	configured_teams = {row.team for row in settings.escalation_rules}

	for team in TEAMS:
		row = next((r for r in settings.escalation_rules if r.team == team), None)
		l1_user = row.l1_user if row else ""
		to_agent = l1_user if l1_user and frappe.db.exists("HD Agent", l1_user) else ""
		if not to_agent:
			to_agent = _fallback_team_agent_email(team)
		if not to_agent:
			continue

		values = {
			"is_enabled": 1,
			"team": team,
			"priority": "",
			"ticket_type": "",
			"to_agent": to_agent,
			"to_team": team,
			"to_priority": _next_priority("Medium"),
		}

		existing_name = frappe.db.get_value(
			"HD Escalation Rule",
			{"team": team, "priority": "", "ticket_type": ""},
			"name",
		)
		if existing_name:
			doc = frappe.get_doc("HD Escalation Rule", existing_name)
			changed = False
			for field, value in values.items():
				if doc.get(field) != value:
					doc.set(field, value)
					changed = True
			if changed:
				doc.save(ignore_permissions=True)
			continue

		frappe.get_doc({"doctype": "HD Escalation Rule", **values}).insert(ignore_permissions=True)

	# Disable HD Escalation Rules for teams removed from MCX settings.
	for team in TEAMS:
		if team in configured_teams:
			continue
		existing_name = frappe.db.get_value(
			"HD Escalation Rule",
			{"team": team, "priority": "", "ticket_type": ""},
			"name",
		)
		if existing_name:
			frappe.db.set_value("HD Escalation Rule", existing_name, "is_enabled", 0)


def _fallback_team_agent_email(team: str) -> str:
	members = frappe.get_all(
		"HD Team Member",
		filters={"parent": team, "parenttype": "HD Team"},
		pluck="user",
		limit=1,
	)
	if members and frappe.db.exists("HD Agent", members[0]):
		return members[0]
	return ""


def _next_priority(priority: str) -> str:
	if priority not in PRIORITY_LADDER:
		return "High"
	idx = PRIORITY_LADDER.index(priority)
	return PRIORITY_LADDER[min(idx + 1, len(PRIORITY_LADDER) - 1)]


def ensure_escalation_setup():
	if "helpdesk" not in frappe.get_installed_apps():
		return
	ensure_escalation_custom_fields()
	ensure_escalation_settings_doc()
	ensure_escalation_users()
	ensure_hd_escalation_rules()
