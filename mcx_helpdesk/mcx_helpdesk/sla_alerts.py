# Copyright (c) 2026, Ascra Technologies LLP and contributors
# For license information, please see license.txt

"""Proactive SLA risk monitoring — warn agents before breach (UNFYD-style)."""

from __future__ import annotations

import frappe
from frappe.utils import get_datetime, now_datetime, time_diff_in_seconds

from mcx_helpdesk.mcx_helpdesk.escalation_settings import get_l1_supervisor
from mcx_helpdesk.mcx_helpdesk.sla_settings import get_sla_alert_settings

SLA_RISK_NONE = "None"
SLA_RISK_WARNING = "Warning"
SLA_RISK_CRITICAL = "Critical"

SLA_RISK_LEVELS = (SLA_RISK_NONE, SLA_RISK_WARNING, SLA_RISK_CRITICAL)


def process_proactive_sla_alerts():
	"""Scheduled job: evaluate open tickets and fire warning/critical alerts."""
	settings = get_sla_alert_settings()
	if not settings.get("enabled"):
		return

	tickets = frappe.get_all(
		"HD Ticket",
		filters={
			"status_category": "Open",
			"agreement_status": ["in", ["First Response Due", "Resolution Due"]],
		},
		fields=[
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
	)
	for row in tickets:
		try:
			_evaluate_ticket(row, settings)
			frappe.db.commit()
		except Exception:
			frappe.db.rollback()
			frappe.log_error(title="MCX Proactive SLA Alert Failed", message=frappe.get_traceback())


def _evaluate_ticket(row: dict, settings: dict | None = None):
	settings = settings or get_sla_alert_settings()
	target = _active_sla_target(row)
	if not target:
		if row.get("mcx_sla_risk_level") and row.get("mcx_sla_risk_level") != SLA_RISK_NONE:
			_reset_risk(row["name"])
		return

	target_name, deadline, window_start = target
	pct = _elapsed_pct(window_start, deadline)
	new_level = _risk_level_for_pct(pct, settings)
	prev_level = row.get("mcx_sla_risk_level") or SLA_RISK_NONE
	notified_level = row.get("mcx_sla_risk_notified_level") or SLA_RISK_NONE

	updates = {
		"mcx_sla_risk_level": new_level,
		"mcx_sla_risk_target": target_name,
		"mcx_sla_risk_pct": round(pct, 1),
	}
	frappe.db.set_value("HD Ticket", row["name"], updates, update_modified=False)

	if new_level == SLA_RISK_NONE:
		if prev_level != SLA_RISK_NONE:
			frappe.db.set_value(
				"HD Ticket",
				row["name"],
				"mcx_sla_risk_notified_level",
				SLA_RISK_NONE,
				update_modified=False,
			)
		return

	if _level_rank(new_level) <= _level_rank(notified_level):
		return

	frappe.db.set_value(
		"HD Ticket",
		row["name"],
		"mcx_sla_risk_notified_level",
		new_level,
		update_modified=False,
	)
	_notify_risk(row["name"], new_level, target_name, deadline, pct, settings)
	_dispatch_workflow(row["name"], new_level)


def _active_sla_target(row: dict) -> tuple[str, object, object] | None:
	now = now_datetime()
	sla_start = get_datetime(row.get("service_level_agreement_creation") or row.get("creation"))

	if row.get("agreement_status") == "First Response Due" and row.get("response_by"):
		deadline = get_datetime(row["response_by"])
		if deadline <= now:
			return None
		return ("First Response", deadline, sla_start)

	if row.get("agreement_status") == "Resolution Due" and row.get("resolution_by"):
		deadline = get_datetime(row["resolution_by"])
		if deadline <= now:
			return None
		return ("Resolution", deadline, sla_start)

	return None


def _elapsed_pct(window_start, deadline) -> float:
	total = time_diff_in_seconds(deadline, window_start)
	if total <= 0:
		return 100.0
	elapsed = time_diff_in_seconds(now_datetime(), window_start)
	return min(max((elapsed / total) * 100, 0), 100)


def _risk_level_for_pct(pct: float, settings: dict | None = None) -> str:
	settings = settings or get_sla_alert_settings()
	warning = settings["warning_threshold_pct"]
	critical = settings["critical_threshold_pct"]
	if pct >= critical:
		return SLA_RISK_CRITICAL
	if pct >= warning:
		return SLA_RISK_WARNING
	return SLA_RISK_NONE


def _level_rank(level: str) -> int:
	return {SLA_RISK_NONE: 0, SLA_RISK_WARNING: 1, SLA_RISK_CRITICAL: 2}.get(level, 0)


def _reset_risk(ticket_name: str):
	frappe.db.set_value(
		"HD Ticket",
		ticket_name,
		{
			"mcx_sla_risk_level": SLA_RISK_NONE,
			"mcx_sla_risk_target": "",
			"mcx_sla_risk_pct": 0,
			"mcx_sla_risk_notified_level": SLA_RISK_NONE,
		},
		update_modified=False,
	)


def reset_risk_on_ticket_close(doc, method=None):
	"""Clear proactive SLA flags when ticket is no longer open."""
	if doc.status_category != "Open":
		_reset_risk(doc.name)


def _notify_risk(
	ticket_name: str,
	level: str,
	target_name: str,
	deadline,
	pct: float,
	settings: dict | None = None,
):
	settings = settings or get_sla_alert_settings()
	doc = frappe.get_doc("HD Ticket", ticket_name)
	recipients = _alert_recipients(doc, settings)
	if not recipients:
		return

	remaining_mins = max(int(time_diff_in_seconds(deadline, now_datetime()) / 60), 0)
	level_label = "approaching breach" if level == SLA_RISK_WARNING else "imminent breach"
	subject = f"[SLA {level}] Ticket #{doc.name} — {target_name} {level_label}"
	message = f"""
<p>Ticket <strong>{doc.name}</strong> is at <strong>{pct:.0f}%</strong> of its
{target_name.lower()} SLA window with approximately <strong>{remaining_mins} minutes</strong> remaining.</p>
<ul>
<li><strong>Subject:</strong> {frappe.utils.escape_html(doc.subject or "")}</li>
<li><strong>Department:</strong> {frappe.utils.escape_html(doc.agent_group or "—")}</li>
<li><strong>Priority:</strong> {frappe.utils.escape_html(doc.priority or "—")}</li>
<li><strong>Deadline:</strong> {frappe.utils.format_datetime(deadline)}</li>
</ul>
<p>Please action this ticket before the SLA fails.</p>
"""
	_log_activity(ticket_name, level, target_name, pct, remaining_mins)
	for email in recipients:
		_send_alert_email(email, subject, message, ticket_name)
		_send_desk_notification(email, subject, ticket_name)


def _alert_recipients(doc, settings: dict | None = None) -> list[str]:
	settings = settings or get_sla_alert_settings()
	recipients: list[str] = []
	if settings.get("notify_assignee"):
		for assignee in _get_assignees(doc.name):
			if frappe.db.exists("User", assignee):
				recipients.append(assignee)

	if settings.get("notify_supervisor") and doc.agent_group:
		l1 = get_l1_supervisor(doc.agent_group)
		if l1 and frappe.db.exists("User", l1):
			recipients.append(l1)

	# Deduplicate while preserving order.
	seen: set[str] = set()
	unique: list[str] = []
	for email in recipients:
		if email not in seen:
			seen.add(email)
			unique.append(email)
	return unique


def _get_assignees(ticket_name: str) -> list[str]:
	return frappe.get_all(
		"ToDo",
		filters={
			"reference_type": "HD Ticket",
			"reference_name": ticket_name,
			"status": "Open",
		},
		pluck="allocated_to",
	) or []


def _send_alert_email(recipient: str, subject: str, message: str, ticket_name: str):
	try:
		frappe.sendmail(
			recipients=[recipient],
			subject=subject,
			message=message,
			reference_doctype="HD Ticket",
			reference_name=ticket_name,
		)
	except Exception:
		frappe.log_error(title="MCX SLA Alert Email Failed", message=frappe.get_traceback())


def _send_desk_notification(recipient: str, subject: str, ticket_name: str):
	try:
		notification = frappe.get_doc(
			{
				"doctype": "Notification Log",
				"subject": subject,
				"email_content": subject,
				"for_user": recipient,
				"type": "Alert",
				"document_type": "HD Ticket",
				"document_name": ticket_name,
			}
		)
		notification.insert(ignore_permissions=True)
	except Exception:
		frappe.log_error(title="MCX SLA Desk Notification Failed", message=frappe.get_traceback())


def _log_activity(ticket_name: str, level: str, target_name: str, pct: float, remaining_mins: int):
	from helpdesk.helpdesk.doctype.hd_ticket_activity.hd_ticket_activity import log_ticket_activity

	log_ticket_activity(
		ticket_name,
		f"Proactive SLA alert ({level}): {target_name} at {pct:.0f}% — ~{remaining_mins} min remaining",
	)


def _dispatch_workflow(ticket_name: str, level: str):
	from mcx_helpdesk.mcx_helpdesk.workflow_engine import dispatch_workflow

	event = "SLA Warning" if level == SLA_RISK_WARNING else "SLA Critical"
	dispatch_workflow(ticket_name, event)
