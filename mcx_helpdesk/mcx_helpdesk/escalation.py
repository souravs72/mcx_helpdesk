# Copyright (c) 2026, Ascra Technologies LLP and contributors
# For license information, please see license.txt

"""SLA breach detection and multi-level ticket escalation."""

from __future__ import annotations

import frappe
from frappe.desk.form.assign_to import add as assign_to
from frappe.desk.form.assign_to import clear as clear_assignments
from frappe.utils import add_to_date, get_datetime, now_datetime

from mcx_helpdesk.constants import (
	COUNTRY_HEAD,
	ESCALATION_SUPERVISORS,
	PRIORITY_LADDER,
	REESCALATE_AFTER_HOURS,
)


def on_ticket_update(doc, method=None):
	"""Escalate immediately when agreement_status transitions to Failed on save."""
	if not doc.has_value_changed("agreement_status"):
		return
	if doc.agreement_status != "Failed":
		reset_escalation_flag_if_recovered(doc.name)
		return
	if doc.get("mcx_sla_breach_escalated"):
		return
	if doc.status_category != "Open":
		return
	apply_escalation(doc.name)


def reset_escalation_flag_if_recovered(ticket_name: str):
	frappe.db.set_value(
		"HD Ticket",
		ticket_name,
		"mcx_sla_breach_escalated",
		0,
		update_modified=False,
	)


def process_sla_breach_escalations():
	"""Hourly job: escalate newly failed tickets and re-escalate stale breaches."""
	reset_recovered_tickets()
	process_new_breaches()
	process_reescalations()


def reset_recovered_tickets():
	frappe.db.sql(
		"""
		UPDATE `tabHD Ticket`
		SET mcx_sla_breach_escalated = 0
		WHERE agreement_status != 'Failed'
		  AND IFNULL(mcx_sla_breach_escalated, 0) = 1
		"""
	)


def process_new_breaches():
	tickets = frappe.get_all(
		"HD Ticket",
		filters={
			"agreement_status": "Failed",
			"status_category": "Open",
			"mcx_sla_breach_escalated": 0,
		},
		pluck="name",
	)
	for ticket_name in tickets:
		try:
			apply_escalation(ticket_name)
			frappe.db.commit()
		except Exception:
			frappe.db.rollback()
			frappe.log_error(title="MCX SLA Escalation Failed", message=frappe.get_traceback())


def process_reescalations():
	cutoff = add_to_date(now_datetime(), hours=-REESCALATE_AFTER_HOURS, as_datetime=True)
	tickets = frappe.db.sql(
		"""
		SELECT name, agent_group, mcx_escalation_level
		FROM `tabHD Ticket`
		WHERE agreement_status = 'Failed'
		  AND status_category = 'Open'
		  AND IFNULL(mcx_sla_breach_escalated, 0) = 1
		  AND IFNULL(mcx_escalation_level, 0) > 0
		  AND mcx_last_escalated_on <= %(cutoff)s
		""",
		{"cutoff": cutoff},
		as_dict=True,
	)
	for row in tickets:
		max_level = _max_escalation_level(row.agent_group)
		if (row.mcx_escalation_level or 0) >= max_level:
			continue
		try:
			frappe.db.set_value(
				"HD Ticket",
				row.name,
				"mcx_sla_breach_escalated",
				0,
				update_modified=False,
			)
			apply_escalation(row.name)
			frappe.db.commit()
		except Exception:
			frappe.db.rollback()
			frappe.log_error(title="MCX SLA Re-escalation Failed", message=frappe.get_traceback())


def apply_escalation(ticket_name: str):
	if getattr(frappe.flags, "mcx_escalating", False):
		return

	frappe.flags.mcx_escalating = True
	try:
		_apply_escalation(ticket_name)
	finally:
		frappe.flags.mcx_escalating = False


def _apply_escalation(ticket_name: str):
	doc = frappe.get_doc("HD Ticket", ticket_name)
	if doc.agreement_status != "Failed" or doc.status_category != "Open":
		return
	if doc.get("mcx_sla_breach_escalated"):
		return

	current_level = doc.get("mcx_escalation_level") or 0
	next_level = current_level + 1
	target = _get_escalation_target(doc.agent_group, next_level)
	if not target:
		return

	changes = _apply_matrix_escalation(doc, target, next_level)

	frappe.db.set_value(
		"HD Ticket",
		ticket_name,
		{
			"mcx_escalation_level": next_level,
			"mcx_last_escalated_on": now_datetime(),
			"mcx_sla_breach_escalated": 1,
		},
		update_modified=False,
	)

	_log_escalation(ticket_name, target, next_level, changes)
	_queue_escalation_email(ticket_name, target, next_level, changes)


def _apply_matrix_escalation(doc, target: dict, level: int) -> list[str]:
	changes = []
	new_priority = _bump_priority(doc.priority)
	if new_priority != doc.priority:
		frappe.db.set_value("HD Ticket", doc.name, "priority", new_priority, update_modified=False)
		changes.append(f"priority escalated to {new_priority}")

	_reassign_ticket(doc.name, target["email"])
	changes.append(f"escalated to {target['level']} ({target['full_name']})")
	return changes


def _bump_priority(current: str | None) -> str:
	if not current or current not in PRIORITY_LADDER:
		return "High"
	idx = PRIORITY_LADDER.index(current)
	return PRIORITY_LADDER[min(idx + 1, len(PRIORITY_LADDER) - 1)]


def _reassign_ticket(ticket_name: str, agent_email: str):
	if not frappe.db.exists("HD Agent", agent_email):
		return
	clear_assignments("HD Ticket", ticket_name)
	assign_to({"assign_to": [agent_email], "doctype": "HD Ticket", "name": ticket_name})


def _get_escalation_target(team: str | None, level: int) -> dict | None:
	team_levels = ESCALATION_SUPERVISORS.get(team or "", [])
	if level <= len(team_levels):
		target = team_levels[level - 1]
		if frappe.db.exists("User", target["email"]):
			return target
		return _fallback_team_supervisor(team, level)

	if level == len(team_levels) + 1 and frappe.db.exists("User", COUNTRY_HEAD["email"]):
		return COUNTRY_HEAD

	return _fallback_team_supervisor(team, level)


def _fallback_team_supervisor(team: str | None, level: int) -> dict | None:
	if not team or not frappe.db.exists("HD Team", team):
		return None
	members = frappe.get_all(
		"HD Team Member",
		filters={"parent": team, "parenttype": "HD Team"},
		pluck="user",
		limit=1,
	)
	if not members:
		return None
	email = members[0]
	if not frappe.db.exists("HD Agent", email):
		return None
	name = frappe.db.get_value("HD Agent", email, "agent_name") or email
	return {"email": email, "full_name": name, "level": f"L{level}"}


def _max_escalation_level(team: str | None) -> int:
	return len(ESCALATION_SUPERVISORS.get(team or "", [])) + 1


def _log_escalation(ticket_name: str, target: dict, level: int, changes: list[str]):
	from helpdesk.helpdesk.doctype.hd_ticket_activity.hd_ticket_activity import log_ticket_activity

	detail = ", ".join(changes) if changes else "no field changes"
	log_ticket_activity(
		ticket_name,
		f"SLA breach escalation (Level {level} — {target['level']}): {detail}",
	)


def _queue_escalation_email(ticket_name: str, target: dict, level: int, changes: list[str]):
	frappe.enqueue(
		"mcx_helpdesk.mcx_helpdesk.escalation.send_escalation_email",
		queue="short",
		ticket_name=ticket_name,
		target=target,
		level=level,
		changes=changes,
	)


def send_escalation_email(ticket_name: str, target: dict, level: int, changes: list[str]):
	doc = frappe.get_doc("HD Ticket", ticket_name)
	_send_escalation_email(doc, target, level, changes)


def _send_escalation_email(doc, target: dict, level: int, changes: list[str]):
	if not frappe.db.get_single_value("HD Settings", "send_acknowledgement_email"):
		# Still send escalation mails even if ack is off — use explicit send.
		pass

	subject = f"[SLA Breach] Ticket #{doc.name} escalated to {target['level']}"
	message = f"""
<p>Ticket <strong>{doc.name}</strong> has breached its SLA and has been escalated.</p>
<ul>
<li><strong>Subject:</strong> {frappe.utils.escape_html(doc.subject or "")}</li>
<li><strong>Department:</strong> {frappe.utils.escape_html(doc.agent_group or "—")}</li>
<li><strong>Priority:</strong> {frappe.utils.escape_html(doc.priority or "—")}</li>
<li><strong>SLA Status:</strong> Failed</li>
<li><strong>Escalation Level:</strong> {level} ({target['level']})</li>
</ul>
<p>{frappe.utils.escape_html(", ".join(changes))}</p>
<p>Please review and action this ticket promptly.</p>
"""
	try:
		frappe.sendmail(
			recipients=[target["email"]],
			subject=subject,
			message=message,
			reference_doctype="HD Ticket",
			reference_name=doc.name,
		)
	except Exception:
		frappe.log_error(title="MCX Escalation Email Failed", message=frappe.get_traceback())
