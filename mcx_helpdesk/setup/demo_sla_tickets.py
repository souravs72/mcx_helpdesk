# Copyright (c) 2026, Ascra Technologies LLP and contributors
# For license information, please see license.txt

"""Seed open demo tickets at Warning, Critical, and Breached/L2 escalation states."""

from __future__ import annotations

import frappe
from frappe.desk.form.assign_to import add as assign_to
from frappe.desk.form.assign_to import clear as clear_assignments
from frappe.utils import add_to_date, now_datetime

from mcx_helpdesk.mcx_helpdesk.escalation import apply_escalation
from mcx_helpdesk.mcx_helpdesk.sla_alerts import _evaluate_ticket, process_proactive_sla_alerts
from mcx_helpdesk.mcx_helpdesk.sla_settings import get_sla_alert_settings
from mcx_helpdesk.setup.escalation import _ensure_existing_supervisor_agents, ensure_escalation_users

DEMO_SLA_PREFIX = "[DEMO SLA]"

# Urgent first-response window is 30 minutes on the Default SLA.
URGENT_FIRST_RESPONSE_MINUTES = 30

DEMO_SLA_TICKETS = [
	{
		"subject": f"{DEMO_SLA_PREFIX} Warning — member portal login delayed",
		"description": "Demo ticket kept open near the SLA warning threshold for supervisor board and dashboard demos.",
		"scenario": "warning",
		"target_pct": 77,
	},
	{
		"subject": f"{DEMO_SLA_PREFIX} Critical — trading terminal slow during market hours",
		"description": "Demo ticket kept open near the SLA critical threshold for live-queue and agent banner demos.",
		"scenario": "critical",
		"target_pct": 92,
	},
	{
		"subject": f"{DEMO_SLA_PREFIX} Breached — portal access still blocked (L2 escalated)",
		"description": "Demo ticket with failed first-response SLA, escalated to department head for breach and escalation demos.",
		"scenario": "breached_l2",
	},
]

_TICKET_DEFAULTS = {
	"priority": "Urgent",
	"ticket_type": "IT - Portal Access",
	"sub_issue_type": "Login Issue",
	"agent_group": "IT",
	"customer": "Alpha Brokers",
	"contact_email": "priya@alphabrokers.com",
	"assign_to": "mcx.it.agent@demo.com",
}


def setup_demo_sla_tickets() -> dict:
	"""Create or refresh the three SLA demo tickets. Safe to re-run before a client demo."""
	if "helpdesk" not in frappe.get_installed_apps():
		frappe.throw("Helpdesk app is not installed on this site")

	ensure_escalation_users()
	_ensure_existing_supervisor_agents()
	_remove_existing_demo_sla_tickets()
	created = []

	for spec in DEMO_SLA_TICKETS:
		ticket_name = _create_demo_ticket(spec)
		created.append(
			{
				"name": ticket_name,
				"subject": spec["subject"],
				"scenario": spec["scenario"],
			}
		)

	process_proactive_sla_alerts()
	frappe.db.commit()
	frappe.clear_cache()

	summary = []
	for row in created:
		doc = frappe.db.get_value(
			"HD Ticket",
			row["name"],
			[
				"agreement_status",
				"mcx_sla_risk_level",
				"mcx_sla_risk_pct",
				"mcx_escalation_level",
				"response_by",
			],
			as_dict=True,
		)
		summary.append({**row, **doc})

	return {"tickets": summary}


def _remove_existing_demo_sla_tickets():
	for name in frappe.get_all("HD Ticket", filters={"subject": ["like", f"{DEMO_SLA_PREFIX}%"]}, pluck="name"):
		frappe.delete_doc("HD Ticket", name, force=True, ignore_permissions=True)


def _create_demo_ticket(spec: dict) -> str:
	contact = frappe.db.get_value("Contact", {"email_id": _TICKET_DEFAULTS["contact_email"]}, "name")
	ticket = frappe.get_doc(
		{
			"doctype": "HD Ticket",
			"subject": spec["subject"],
			"description": spec["description"],
			"priority": _TICKET_DEFAULTS["priority"],
			"ticket_type": _TICKET_DEFAULTS["ticket_type"],
			"sub_issue_type": _TICKET_DEFAULTS["sub_issue_type"],
			"agent_group": _TICKET_DEFAULTS["agent_group"],
			"customer": _TICKET_DEFAULTS["customer"],
			"contact": contact,
			"raised_by": _TICKET_DEFAULTS["contact_email"],
			"status": "Open",
		}
	)
	ticket.insert(ignore_permissions=True)

	scenario = spec["scenario"]
	if scenario in ("warning", "critical"):
		_apply_proactive_sla_state(ticket.name, spec["target_pct"])
	elif scenario == "breached_l2":
		_apply_breached_l2_state(ticket.name)
	else:
		frappe.throw(f"Unknown SLA demo scenario: {scenario}")

	if scenario != "breached_l2":
		_ensure_initial_assignee(ticket.name)
	return ticket.name


def _ensure_initial_assignee(ticket_name: str):
	assignee = _TICKET_DEFAULTS["assign_to"]
	if not frappe.db.exists("HD Agent", assignee):
		return
	clear_assignments("HD Ticket", ticket_name)
	assign_to({"assign_to": [assignee], "doctype": "HD Ticket", "name": ticket_name})


def _apply_proactive_sla_state(ticket_name: str, target_pct: float):
	"""Backdate the first-response SLA window so the ticket sits at the target risk %."""
	sla_start, deadline = _window_for_pct(target_pct, URGENT_FIRST_RESPONSE_MINUTES)
	frappe.db.set_value(
		"HD Ticket",
		ticket_name,
		{
			"creation": sla_start,
			"service_level_agreement_creation": sla_start,
			"response_by": deadline,
			"agreement_status": "First Response Due",
			"status": "Open",
			"status_category": "Open",
			"mcx_sla_risk_notified_level": "None",
			"mcx_sla_breach_escalated": 0,
			"mcx_escalation_level": 0,
		},
		update_modified=False,
	)

	row = frappe.db.get_value(
		"HD Ticket",
		ticket_name,
		[
			"name",
			"agreement_status",
			"response_by",
			"resolution_by",
			"service_level_agreement_creation",
			"creation",
			"mcx_sla_risk_level",
			"mcx_sla_risk_target",
			"mcx_sla_risk_notified_level",
		],
		as_dict=True,
	)
	settings = get_sla_alert_settings()
	_evaluate_ticket(row, settings)


def _apply_breached_l2_state(ticket_name: str):
	"""Fail first-response SLA and escalate twice (L1 supervisor, then L2 dept head)."""
	now = now_datetime()
	sla_start = add_to_date(now, minutes=-(URGENT_FIRST_RESPONSE_MINUTES + 45), as_datetime=True)
	response_by = add_to_date(now, minutes=-45, as_datetime=True)

	frappe.db.set_value(
		"HD Ticket",
		ticket_name,
		{
			"creation": sla_start,
			"service_level_agreement_creation": sla_start,
			"response_by": response_by,
			"agent_group": _TICKET_DEFAULTS["agent_group"],
			"agreement_status": "Failed",
			"status": "Open",
			"status_category": "Open",
			"mcx_sla_risk_level": "None",
			"mcx_sla_risk_target": "",
			"mcx_sla_risk_pct": 0,
			"mcx_sla_risk_notified_level": "None",
			"mcx_sla_breach_escalated": 0,
			"mcx_escalation_level": 0,
		},
		update_modified=False,
	)

	apply_escalation(ticket_name)
	frappe.db.set_value(
		"HD Ticket",
		ticket_name,
		"mcx_sla_breach_escalated",
		0,
		update_modified=False,
	)
	apply_escalation(ticket_name)


def _window_for_pct(target_pct: float, total_minutes: int) -> tuple[object, object]:
	"""Return (sla_start, deadline) so that *now* sits at target_pct through the SLA window."""
	now = now_datetime()
	total_seconds = total_minutes * 60
	elapsed_seconds = total_seconds * (target_pct / 100.0)
	remaining_seconds = max(total_seconds - elapsed_seconds, 60)
	sla_start = add_to_date(now, seconds=-int(elapsed_seconds), as_datetime=True)
	deadline = add_to_date(now, seconds=int(remaining_seconds), as_datetime=True)
	return sla_start, deadline
