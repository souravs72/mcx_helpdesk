# Copyright (c) 2026, Ascra Technologies LLP and contributors
# For license information, please see license.txt

"""Configurable service process automation for HD Ticket lifecycle events."""

from __future__ import annotations

import frappe
from frappe.desk.form.assign_to import add as assign_to
from frappe.desk.form.assign_to import clear as clear_assignments
from frappe.utils import now_datetime

from mcx_helpdesk.mcx_helpdesk.escalation_settings import get_l1_supervisor
from mcx_helpdesk.mcx_helpdesk.escalation import _bump_priority, apply_escalation


def on_ticket_created(doc, method=None):
	dispatch_workflow(doc.name, "Ticket Created")


def on_ticket_updated(doc, method=None):
	dispatch_workflow(doc.name, "Ticket Updated")
	if doc.has_value_changed("status"):
		dispatch_workflow(doc.name, "Status Changed")
	if doc.has_value_changed("first_responded_on") and doc.first_responded_on:
		dispatch_workflow(doc.name, "First Response")
	if doc.has_value_changed("resolution_date") and doc.resolution_date:
		dispatch_workflow(doc.name, "Resolved")
	if doc.has_value_changed("agreement_status") and doc.agreement_status == "Failed":
		dispatch_workflow(doc.name, "SLA Breached")


def dispatch_workflow(ticket_name: str, event: str, context: dict | None = None):
	if getattr(frappe.flags, "mcx_running_workflow", False):
		return

	frappe.flags.mcx_running_workflow = True
	try:
		_run_workflows(ticket_name, event, context or {})
	finally:
		frappe.flags.mcx_running_workflow = False


def _run_workflows(ticket_name: str, event: str, context: dict):
	if not frappe.db.exists("DocType", "MCX Service Workflow"):
		return

	workflows = frappe.get_all(
		"MCX Service Workflow",
		filters={"enabled": 1, "trigger_event": event},
		fields=["name"],
		order_by="priority asc",
	)
	if not workflows:
		return

	doc = frappe.get_doc("HD Ticket", ticket_name)
	eval_context = {"doc": doc, **context}

	for row in workflows:
		try:
			workflow = frappe.get_doc("MCX Service Workflow", row.name)
			if not _matches_condition(workflow, eval_context):
				continue
			for action in workflow.actions:
				_execute_action(doc, action, eval_context)
			frappe.db.commit()
		except Exception:
			frappe.db.rollback()
			frappe.log_error(
				title=f"MCX Workflow Failed: {row.name}",
				message=frappe.get_traceback(),
			)


def _matches_condition(workflow, context: dict) -> bool:
	if not workflow.condition:
		return True
	return bool(frappe.safe_eval(workflow.condition, None, context))


def _execute_action(doc, action, context: dict):
	action_type = action.action_type
	if action_type == "Assign Agent":
		_assign_agent(doc.name, action.value)
	elif action_type == "Assign Team":
		frappe.db.set_value("HD Ticket", doc.name, "agent_group", action.value, update_modified=False)
	elif action_type == "Set Field":
		if action.field_name:
			frappe.db.set_value(
				"HD Ticket", doc.name, action.field_name, action.value, update_modified=False
			)
	elif action_type == "Bump Priority":
		new_priority = _bump_priority(doc.priority)
		frappe.db.set_value("HD Ticket", doc.name, "priority", new_priority, update_modified=False)
	elif action_type == "Send Email":
		for recipient in _resolve_recipients(doc, action):
			_send_workflow_email(doc, recipient, action)
	elif action_type == "Send Notification":
		for recipient in _resolve_recipients(doc, action):
			_send_workflow_notification(doc, recipient, action)
	elif action_type == "Add Internal Comment":
		_add_internal_comment(doc.name, _render_template(action.message_template or action.value, doc))
	elif action_type == "Trigger Escalation":
		apply_escalation(doc.name)
	elif action_type == "Create ToDo":
		for recipient in _resolve_recipients(doc, action):
			frappe.get_doc(
				{
					"doctype": "ToDo",
					"description": _render_template(action.message_template or action.value, doc)
					or f"Workflow task for ticket {doc.name}",
					"reference_type": "HD Ticket",
					"reference_name": doc.name,
					"allocated_to": recipient,
					"assigned_by": frappe.session.user or "Administrator",
				}
			).insert(ignore_permissions=True)


def _assign_agent(ticket_name: str, agent_email: str):
	if not agent_email or not frappe.db.exists("HD Agent", agent_email):
		return
	clear_assignments("HD Ticket", ticket_name)
	assign_to(
		{
			"assign_to": [agent_email],
			"doctype": "HD Ticket",
			"name": ticket_name,
			"description": "Assigned by MCX workflow",
		},
		ignore_permissions=True,
	)


def _resolve_recipients(doc, action) -> list[str]:
	recipients: list[str] = []
	recipient_type = action.recipient_type or "Assignee"

	if recipient_type == "Specific User" and action.recipient:
		recipients.append(action.recipient)
	elif recipient_type == "Assignee":
		recipients.extend(_get_assignees(doc.name))
	elif recipient_type == "Raised By" and doc.raised_by:
		recipients.append(doc.raised_by)
	elif recipient_type == "Department Supervisor" and doc.agent_group:
		l1 = get_l1_supervisor(doc.agent_group)
		if l1:
			recipients.append(l1)

	return [r for r in dict.fromkeys(recipients) if r and frappe.db.exists("User", r)]


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


def _render_template(template: str | None, doc) -> str:
	if not template:
		return ""
	return frappe.render_template(
		template,
		{
			"doc": doc,
			"ticket": doc,
			"now": now_datetime(),
		},
	)


def _send_workflow_email(doc, recipient: str, action):
	subject = _render_template(action.value, doc) or f"Workflow alert: Ticket #{doc.name}"
	body = _render_template(action.message_template, doc) or subject
	try:
		frappe.sendmail(
			recipients=[recipient],
			subject=subject,
			message=body,
			reference_doctype="HD Ticket",
			reference_name=doc.name,
		)
	except Exception:
		frappe.log_error(title="MCX Workflow Email Failed", message=frappe.get_traceback())


def _send_workflow_notification(doc, recipient: str, action):
	subject = _render_template(action.message_template or action.value, doc) or (
		f"Workflow: Ticket #{doc.name}"
	)
	try:
		frappe.get_doc(
			{
				"doctype": "Notification Log",
				"subject": subject,
				"email_content": subject,
				"for_user": recipient,
				"type": "Alert",
				"document_type": "HD Ticket",
				"document_name": doc.name,
			}
		).insert(ignore_permissions=True)
	except Exception:
		frappe.log_error(title="MCX Workflow Notification Failed", message=frappe.get_traceback())


def _add_internal_comment(ticket_name: str, content: str):
	if not content:
		return
	frappe.get_doc(
		{
			"doctype": "HD Ticket Comment",
			"reference_ticket": ticket_name,
			"content": content,
			"commented_by": frappe.session.user or "Administrator",
		}
	).insert(ignore_permissions=True)
