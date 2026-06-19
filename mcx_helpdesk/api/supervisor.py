# Copyright (c) 2026, Ascra Technologies LLP and contributors
# For license information, please see license.txt

"""Supervisor live queue API with SLA countdown data."""

from __future__ import annotations

import frappe
from frappe.utils import get_datetime, now_datetime, time_diff_in_seconds

from helpdesk.utils import agent_only
from mcx_helpdesk.mcx_helpdesk.sla_settings import get_sla_alert_settings


@frappe.whitelist()
@agent_only
def get_supervisor_queue(team: str | None = None, limit: int = 100) -> dict:
	"""Live queue for supervisors — open tickets sorted by nearest SLA deadline."""
	if "Agent Manager" not in frappe.get_roles():
		frappe.throw("Only managers can view the supervisor board.", frappe.PermissionError)

	limit = min(max(frappe.utils.cint(limit) or 100, 1), 200)
	filters = {
		"status_category": "Open",
		"agreement_status": ["in", ["First Response Due", "Resolution Due", "Failed"]],
	}
	if team:
		filters["agent_group"] = team

	fields = [
		"name",
		"subject",
		"priority",
		"agent_group",
		"agreement_status",
		"response_by",
		"resolution_by",
		"service_level_agreement_creation",
		"creation",
		"first_responded_on",
		"mcx_sla_risk_level",
		"mcx_sla_risk_pct",
		"mcx_escalation_level",
		"mcx_sla_breach_escalated",
		"_assign",
	]

	tickets = frappe.get_all("HD Ticket", filters=filters, fields=fields, limit=limit * 3)
	rows = []
	now = now_datetime()

	for ticket in tickets:
		row = _build_queue_row(ticket, now)
		if row:
			rows.append(row)

	rows.sort(key=lambda r: (r["sort_rank"], r["seconds_remaining"]))
	rows = rows[:limit]

	settings = get_sla_alert_settings()
	return {
		"tickets": rows,
		"total_count": len(rows),
		"settings": settings,
		"server_time": now.isoformat(),
	}


def _build_queue_row(ticket: dict, now) -> dict | None:
	deadline_info = _active_deadline(ticket, now)
	if not deadline_info:
		return None

	target_name, deadline, window_start = deadline_info
	total_seconds = max(time_diff_in_seconds(deadline, window_start), 1)
	remaining = int(time_diff_in_seconds(deadline, now))
	elapsed_pct = min(max((time_diff_in_seconds(now, window_start) / total_seconds) * 100, 0), 100)

	settings = get_sla_alert_settings()
	risk = ticket.get("mcx_sla_risk_level") or "None"
	if ticket.get("agreement_status") == "Failed":
		risk = "Breached"
	elif elapsed_pct >= settings["critical_threshold_pct"]:
		risk = risk if risk == "Critical" else "Critical"
	elif elapsed_pct >= settings["warning_threshold_pct"]:
		risk = risk if risk in ("Warning", "Critical") else "Warning"

	assignees = _parse_assignees(ticket.get("_assign"))

	return {
		"name": ticket.name,
		"subject": ticket.subject,
		"priority": ticket.priority,
		"department": ticket.agent_group,
		"agreement_status": ticket.agreement_status,
		"sla_target": target_name,
		"deadline": get_datetime(deadline).isoformat(),
		"seconds_remaining": remaining,
		"elapsed_pct": round(elapsed_pct, 1),
		"risk_level": risk,
		"escalation_level": ticket.get("mcx_escalation_level") or 0,
		"is_escalated": bool(ticket.get("mcx_sla_breach_escalated")),
		"assignees": assignees,
		"sort_rank": 0 if remaining > 0 else 1,
	}


def _active_deadline(ticket: dict, now):
	sla_start = get_datetime(ticket.get("service_level_agreement_creation") or ticket.get("creation"))

	if ticket.get("agreement_status") == "First Response Due" and ticket.get("response_by"):
		deadline = get_datetime(ticket["response_by"])
		return ("First Response", deadline, sla_start)

	if ticket.get("agreement_status") in ("Resolution Due", "Failed") and ticket.get("resolution_by"):
		deadline = get_datetime(ticket["resolution_by"])
		return ("Resolution", deadline, sla_start)

	if ticket.get("agreement_status") == "Failed" and ticket.get("response_by"):
		deadline = get_datetime(ticket["response_by"])
		if deadline < now:
			return ("First Response", deadline, sla_start)

	return None


def _parse_assignees(assign_field: str | None) -> list[str]:
	if not assign_field:
		return []
	try:
		import json

		parsed = json.loads(assign_field)
		if isinstance(parsed, list):
			return parsed
	except Exception:
		pass
	return [a.strip() for a in str(assign_field).split(",") if a.strip()]
