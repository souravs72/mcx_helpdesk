# Copyright (c) 2026, Ascra Technologies LLP and contributors
# For license information, please see license.txt

"""Idempotent cleanup for production-quality Helpdesk master data."""

from __future__ import annotations

import frappe

from mcx_helpdesk.constants import LEGACY_TEAMS, TEAMS

JUNK_TICKET_SUBJECTS = {
	"Escalation test ticket",
	"A demo ticket",
	"This is an isue for e",
	"Welcome to Helpdesk",
	"Welcome to Ascra Technologies (Demo)",
	"You've been invited to join Helpdesk",
	"Lorem Ipsum Test Ticket 01",
	"Create a test ticket",
	"subject line",
}

JUNK_TICKET_SUBJECT_PATTERNS = (
	"Security alert",
	"2-Step Verification",
	"Welcome to Helpdesk",
	"invited to join",
)

LEGACY_TICKET_TYPES = ("Bug", "Incident", "Question")

DEFAULT_ARTICLE_TITLES = ("Introduction",)


def cleanup_helpdesk_data():
	"""Run all safe cleanups (idempotent)."""
	if "helpdesk" not in frappe.get_installed_apps():
		return
	cleanup_orphan_assignment_rules()
	normalize_assignment_rule_names()
	cleanup_junk_tickets()
	cleanup_legacy_ticket_types()
	cleanup_default_helpdesk_articles()
	ensure_team_assignment_rule_links()


def normalize_assignment_rule_names():
	"""Rename numbered support rotation rules to canonical team names."""
	for team_name in TEAMS:
		if not frappe.db.exists("HD Team", team_name):
			continue
		linked = frappe.db.get_value("HD Team", team_name, "assignment_rule")
		if not linked:
			continue
		canonical = f"{team_name} - Support Rotation"
		if linked == canonical:
			continue
		if not linked.startswith(f"{team_name} - Support Rotation"):
			continue
		if frappe.db.exists("Assignment Rule", canonical):
			frappe.db.set_value("HD Team", team_name, "assignment_rule", canonical, update_modified=False)
			try:
				frappe.delete_doc("Assignment Rule", linked, force=True, ignore_permissions=True)
			except Exception:
				pass
		else:
			frappe.rename_doc("Assignment Rule", linked, canonical, force=True)
			frappe.db.set_value("HD Team", team_name, "assignment_rule", canonical, update_modified=False)


def cleanup_orphan_assignment_rules():
	"""Keep only the assignment rule linked on each HD Team."""
	for team in frappe.get_all("HD Team", fields=["name", "assignment_rule"]):
		linked = team.assignment_rule
		candidates = frappe.get_all(
			"Assignment Rule",
			filters={
				"document_type": "HD Ticket",
				"name": ["like", f"{team.name} - Support Rotation%"],
			},
			pluck="name",
		)
		for rule_name in candidates:
			if rule_name == linked:
				continue
			try:
				frappe.delete_doc("Assignment Rule", rule_name, force=True, ignore_permissions=True)
			except Exception:
				frappe.log_error(title="MCX Assignment Rule Cleanup", message=frappe.get_traceback())


def ensure_team_assignment_rule_links():
	"""Ensure each active MCX team points at its canonical assignment rule."""
	for team_name in TEAMS:
		if not frappe.db.exists("HD Team", team_name):
			continue
		team = frappe.get_doc("HD Team", team_name)
		if team.assignment_rule and frappe.db.exists("Assignment Rule", team.assignment_rule):
			continue
		canonical = f"{team_name} - Support Rotation"
		if frappe.db.exists("Assignment Rule", canonical):
			frappe.db.set_value("HD Team", team_name, "assignment_rule", canonical, update_modified=False)
			continue
		# Re-save team only when missing a rule entirely (rare).
		if team.users:
			team.save(ignore_permissions=True)


def cleanup_junk_tickets():
	"""Remove test, welcome, and email-noise tickets."""
	for subject in JUNK_TICKET_SUBJECTS:
		_delete_tickets_by_subject(subject, exact=True)

	for pattern in JUNK_TICKET_SUBJECT_PATTERNS:
		_delete_tickets_by_subject(pattern, exact=False)

	# Legacy helpdesk types with no department — usually noise.
	for name in frappe.get_all(
		"HD Ticket",
		filters={
			"ticket_type": ["in", list(LEGACY_TICKET_TYPES)],
			"agent_group": ["in", ["", None]],
		},
		pluck="name",
	):
		_delete_ticket(name)


def _delete_tickets_by_subject(subject: str, exact: bool):
	if exact:
		names = frappe.get_all("HD Ticket", filters={"subject": subject}, pluck="name")
	else:
		names = frappe.db.sql(
			"""
			SELECT name FROM `tabHD Ticket`
			WHERE subject LIKE %(pattern)s
			""",
			{"pattern": f"%{subject}%"},
			pluck="name",
		)
	for name in names:
		_delete_ticket(name)


def _delete_ticket(name: str):
	try:
		frappe.delete_doc("HD Ticket", name, force=True, ignore_permissions=True)
	except Exception:
		frappe.log_error(title="MCX Ticket Cleanup", message=frappe.get_traceback())


def cleanup_legacy_ticket_types():
	"""Disable non-MCX ticket types that confuse the demo."""
	for ticket_type in LEGACY_TICKET_TYPES:
		if not frappe.db.exists("HD Ticket Type", ticket_type):
			continue
		in_use = frappe.db.count("HD Ticket", {"ticket_type": ticket_type})
		if in_use:
			continue
		frappe.delete_doc("HD Ticket Type", ticket_type, force=True, ignore_permissions=True)

	for team in LEGACY_TEAMS:
		if frappe.db.exists("HD Team", team):
			frappe.db.set_value("HD Team", team, "disabled", 1, update_modified=False)
		for rule_name in frappe.get_all(
			"Assignment Rule",
			filters={"name": ["like", f"{team} - Support Rotation%"]},
			pluck="name",
		):
			frappe.db.set_value("Assignment Rule", rule_name, "disabled", 1, update_modified=False)


def cleanup_default_helpdesk_articles():
	"""Remove generic helpdesk placeholder KB content."""
	for title in DEFAULT_ARTICLE_TITLES:
		article = frappe.db.get_value("HD Article", {"title": title}, "name")
		if not article:
			continue
		try:
			frappe.delete_doc(
				"HD Article",
				article,
				force=True,
				ignore_permissions=True,
				ignore_on_trash=True,
			)
		except Exception:
			pass
