# Copyright (c) 2026, Ascra Technologies LLP and contributors
# For license information, please see license.txt

"""SLA breach detection and multi-level ticket escalation."""

from __future__ import annotations

import frappe
from frappe.desk.form.assign_to import add as assign_to
from frappe.desk.form.assign_to import clear as clear_assignments
from frappe.utils import add_to_date, now_datetime

from mcx_helpdesk.constants import PRIORITY_LADDER


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
	"""Periodic job: escalate newly failed tickets and re-escalate stale breaches."""
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
	settings = _escalation_settings()
	reescalate_hours = settings.reescalate_after_hours or 4
	cutoff = add_to_date(now_datetime(), hours=-reescalate_hours, as_datetime=True)
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
		max_level = _max_escalation_level()
		if (row.mcx_escalation_level or 0) >= max_level:
			# Already at max level and still unresolved — alert, don't silently skip.
			try:
				_alert_max_level_reached(row.name)
				frappe.db.commit()
			except Exception:
				frappe.db.rollback()
				frappe.log_error(
					title="MCX Max Level Alert Failed", message=frappe.get_traceback()
				)
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
	_queue_escalation_emails(ticket_name, target, next_level, changes)


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


def _escalation_settings():
	return frappe.get_cached_doc("MCX Escalation Settings")


def _get_escalation_target(team: str | None, level: int) -> dict | None:
	"""
	Return the configured escalation target for the given team and level.
	Raises a descriptive error if users are not configured or do not exist.
	All escalation targets must be set in MCX Escalation Settings.
	"""
	settings = _escalation_settings()

	if level == 3:
		user = settings.country_head_user
		if not user:
			frappe.throw(
				"No Country Head configured for L3 escalation. "
				"Set Country Head (L3) in MCX Escalation Settings."
			)
		if not frappe.db.exists("User", user):
			frappe.throw(
				f"Country Head user '{user}' does not exist in the system. "
				f"Update MCX Escalation Settings."
			)
		return {
			"email": user,
			"full_name": frappe.db.get_value("User", user, "full_name") or "Country Head",
			"level": "L3",
		}

	rule = next((r for r in settings.escalation_rules if r.team == (team or "")), None)
	if not rule:
		frappe.throw(
			f"No escalation rule found for team '{team}'. "
			f"Add a row for this team in MCX Escalation Settings → Team Escalation Rules."
		)

	if level == 1:
		user, label = rule.l1_user, "L1"
	elif level == 2:
		user, label = rule.l2_user, "L2"
	else:
		return None

	if not user:
		frappe.throw(
			f"No {label} user configured for team '{team}'. "
			f"Update MCX Escalation Settings."
		)
	if not frappe.db.exists("User", user):
		frappe.throw(
			f"{label} user '{user}' for team '{team}' does not exist in the system. "
			f"Update MCX Escalation Settings."
		)
	return {
		"email": user,
		"full_name": frappe.db.get_value("User", user, "full_name") or user,
		"level": label,
	}


def _max_escalation_level() -> int:
	# Always 3: L1 (team supervisor) → L2 (dept head) → L3 (country head).
	return 3


def _log_escalation(ticket_name: str, target: dict, level: int, changes: list[str]):
	from helpdesk.helpdesk.doctype.hd_ticket_activity.hd_ticket_activity import log_ticket_activity

	detail = ", ".join(changes) if changes else "no field changes"
	log_ticket_activity(
		ticket_name,
		f"SLA breach escalation (Level {level} — {target['level']}): {detail}",
	)


def _queue_escalation_emails(ticket_name: str, target: dict, level: int, changes: list[str]):
	frappe.enqueue(
		"mcx_helpdesk.mcx_helpdesk.escalation.send_escalation_emails",
		queue="short",
		ticket_name=ticket_name,
		target=target,
		level=level,
		changes=changes,
	)


def send_escalation_emails(ticket_name: str, target: dict, level: int, changes: list[str]):
	"""Enqueue target: send internal + customer emails after reloading the doc."""
	doc = frappe.get_doc("HD Ticket", ticket_name)
	_send_escalation_email(doc, target, level, changes)
	_send_customer_notification_email(doc, target, level)


# Backward-compat alias: jobs enqueued before the rename still reference the old path.
send_escalation_email = send_escalation_emails


def _send_escalation_email(doc, target: dict, level: int, changes: list[str]):
	"""Internal escalation email to the assigned L1/L2/L3 supervisor."""
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


def _send_customer_notification_email(doc, target: dict, level: int):
	"""Customer-facing update at each escalation step — no internal L-level jargon."""
	if not doc.raised_by:
		return

	contact_name = frappe.utils.escape_html(doc.contact_display or "Customer")
	subject = f"Update on your ticket #{doc.name} — Being handled by senior team"
	message = f"""
<p>Dear {contact_name},</p>
<p>We wanted to keep you informed about your support request <strong>#{doc.name}</strong>
&mdash; &ldquo;{frappe.utils.escape_html(doc.subject or "")}&rdquo;.</p>
<p>Your ticket has been escalated to a senior team member who will be giving it priority
attention. We sincerely apologise for the delay and assure you we are actively working
to resolve your issue as soon as possible.</p>
<ul>
<li><strong>Ticket ID:</strong> {doc.name}</li>
<li><strong>Department:</strong> {frappe.utils.escape_html(doc.agent_group or "—")}</li>
<li><strong>Priority:</strong> {frappe.utils.escape_html(doc.priority or "—")}</li>
</ul>
<p>You do not need to take any action. We will update you as soon as the issue is
resolved. If you have additional information to share, please reply to this email or
add a comment on your ticket.</p>
<p>Thank you for your patience.</p>
"""
	try:
		frappe.sendmail(
			recipients=[doc.raised_by],
			subject=subject,
			message=message,
			reference_doctype="HD Ticket",
			reference_name=doc.name,
		)
	except Exception:
		frappe.log_error(
			title="MCX Customer Escalation Email Failed", message=frappe.get_traceback()
		)


def _alert_max_level_reached(ticket_name: str):
	"""
	Send a CRITICAL alert when a ticket is still unresolved at max escalation level.
	Notifies Country Head + Deputy Country Head and the customer.
	Updates mcx_last_escalated_on to throttle repeat alerts to the re-escalation window.
	"""
	doc = frappe.get_doc("HD Ticket", ticket_name)
	settings = _escalation_settings()
	reescalate_hours = settings.reescalate_after_hours or 4

	mgmt_recipients = []
	if settings.country_head_user and frappe.db.exists("User", settings.country_head_user):
		mgmt_recipients.append(settings.country_head_user)
	if settings.deputy_country_head_user and frappe.db.exists("User", settings.deputy_country_head_user):
		mgmt_recipients.append(settings.deputy_country_head_user)

	email_sent = False

	if mgmt_recipients:
		subject = f"[CRITICAL] Ticket #{doc.name} — Unresolved at Maximum Escalation Level"
		message = f"""
<p>Ticket <strong>{doc.name}</strong> remains <strong>unresolved</strong> and has reached
the maximum escalation level (L3). Immediate manual intervention is required.</p>
<ul>
<li><strong>Subject:</strong> {frappe.utils.escape_html(doc.subject or "")}</li>
<li><strong>Department:</strong> {frappe.utils.escape_html(doc.agent_group or "—")}</li>
<li><strong>Priority:</strong> {frappe.utils.escape_html(doc.priority or "—")}</li>
<li><strong>SLA Status:</strong> Failed</li>
<li><strong>Escalation Level:</strong> L3 (Maximum)</li>
</ul>
<p>This alert will repeat every {reescalate_hours} hours until the ticket is resolved.</p>
"""
		try:
			frappe.sendmail(
				recipients=mgmt_recipients,
				subject=subject,
				message=message,
				reference_doctype="HD Ticket",
				reference_name=doc.name,
			)
			email_sent = True
		except Exception:
			frappe.log_error(
				title="MCX Max Level Alert Email Failed", message=frappe.get_traceback()
			)

	if doc.raised_by:
		contact_name = frappe.utils.escape_html(doc.contact_display or "Customer")
		customer_subject = f"Important update on your ticket #{doc.name}"
		customer_message = f"""
<p>Dear {contact_name},</p>
<p>We sincerely apologise for the ongoing delay with your support request
<strong>#{doc.name}</strong> &mdash;
&ldquo;{frappe.utils.escape_html(doc.subject or "")}&rdquo;.</p>
<p>Your case has been escalated to our senior leadership team and is being treated as
a priority. We are committed to resolving this as quickly as possible and appreciate
your continued patience.</p>
<p>A senior team member will be in touch with you directly. If you need to reach us
urgently, please reply to this email.</p>
<p>Thank you for your understanding.</p>
"""
		try:
			frappe.sendmail(
				recipients=[doc.raised_by],
				subject=customer_subject,
				message=customer_message,
				reference_doctype="HD Ticket",
				reference_name=doc.name,
			)
			email_sent = True
		except Exception:
			frappe.log_error(
				title="MCX Max Level Customer Email Failed", message=frappe.get_traceback()
			)

	# Only advance the throttle timestamp when at least one email was queued.
	# If both sends failed (e.g. SMTP down), leave the timestamp unchanged so the
	# next scheduler run retries the alert rather than silently suppressing it.
	if email_sent:
		frappe.db.set_value(
			"HD Ticket",
			ticket_name,
			"mcx_last_escalated_on",
			now_datetime(),
			update_modified=False,
		)
