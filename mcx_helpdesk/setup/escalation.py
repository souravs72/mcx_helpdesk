# Copyright (c) 2026, Ascra Technologies LLP and contributors
# For license information, please see license.txt

"""Auto-setup MCX escalation matrix, supervisors, and Helpdesk escalation rules."""

from __future__ import annotations

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

from mcx_helpdesk.constants import (
	COUNTRY_HEAD,
	ESCALATION_SUPERVISORS,
	PRIORITY_LADDER,
	TEAMS,
)
from mcx_helpdesk.setup.demo import is_demo_mode_enabled
from mcx_helpdesk.setup.install import ensure_agent, ensure_user


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


def ensure_escalation_users():
	"""Create supervisor / head demo users when demo mode is on or user is missing."""
	if not is_demo_mode_enabled():
		_ensure_existing_supervisor_agents()
		return

	seen: set[str] = set()
	for team, supervisors in ESCALATION_SUPERVISORS.items():
		for person in supervisors:
			email = person["email"]
			if email in seen:
				continue
			seen.add(email)
			ensure_user(email, person["full_name"])
			ensure_agent(email, person["full_name"])

	country_email = COUNTRY_HEAD["email"]
	if country_email not in seen:
		ensure_user(country_email, COUNTRY_HEAD["full_name"])
		ensure_agent(country_email, COUNTRY_HEAD["full_name"])


def _ensure_existing_supervisor_agents():
	"""Ensure HD Agent exists for supervisors already present as users."""
	for supervisors in ESCALATION_SUPERVISORS.values():
		for person in supervisors:
			if frappe.db.exists("User", person["email"]):
				ensure_agent(person["email"], person["full_name"])
	if frappe.db.exists("User", COUNTRY_HEAD["email"]):
		ensure_agent(COUNTRY_HEAD["email"], COUNTRY_HEAD["full_name"])


def ensure_hd_escalation_rules():
	"""Create Helpdesk escalation rules per department (used on SLA breach)."""
	for team in TEAMS:
		supervisors = ESCALATION_SUPERVISORS.get(team, [])
		if not supervisors:
			continue
		l1 = supervisors[0]
		to_agent = l1["email"] if frappe.db.exists("HD Agent", l1["email"]) else ""
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
	ensure_escalation_users()
	ensure_hd_escalation_rules()
