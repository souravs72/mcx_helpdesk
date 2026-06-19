# Copyright (c) 2026, Ascra Technologies LLP and contributors
# For license information, please see license.txt

"""Setup proactive SLA fields, automation workflows, and AI settings."""

from __future__ import annotations

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def ensure_automation_custom_fields():
	create_custom_fields(
		{
			"HD Ticket": [
				{
					"fieldname": "mcx_sla_risk_level",
					"label": "SLA Risk Level",
					"fieldtype": "Select",
					"options": "None\nWarning\nCritical",
					"insert_after": "mcx_sla_breach_escalated",
					"read_only": 1,
					"default": "None",
					"in_standard_filter": 1,
				},
				{
					"fieldname": "mcx_sla_risk_target",
					"label": "SLA Risk Target",
					"fieldtype": "Data",
					"insert_after": "mcx_sla_risk_level",
					"read_only": 1,
				},
				{
					"fieldname": "mcx_sla_risk_pct",
					"label": "SLA Risk %",
					"fieldtype": "Float",
					"insert_after": "mcx_sla_risk_target",
					"read_only": 1,
					"precision": 1,
				},
				{
					"fieldname": "mcx_sla_risk_notified_level",
					"label": "SLA Risk Notified Level",
					"fieldtype": "Select",
					"options": "None\nWarning\nCritical",
					"insert_after": "mcx_sla_risk_pct",
					"hidden": 1,
					"default": "None",
					"read_only": 1,
				},
			]
		},
		ignore_validate=True,
	)


def ensure_default_workflows():
	if not frappe.db.exists("DocType", "MCX Service Workflow"):
		return

	_defaults = [
		{
			"workflow_name": "SLA Warning — Notify Assignee",
			"enabled": 1,
			"priority": 10,
			"trigger_event": "SLA Warning",
			"description": "Notify assignee when ticket reaches the configured SLA warning threshold.",
			"actions": [
				{
					"action_type": "Send Notification",
					"recipient_type": "Assignee",
					"message_template": "SLA warning: Ticket #{{ doc.name }} is approaching its deadline.",
				},
				{
					"action_type": "Add Internal Comment",
					"message_template": "Proactive SLA warning triggered at {{ doc.mcx_sla_risk_pct }}% of {{ doc.mcx_sla_risk_target }} window.",
				},
			],
		},
		{
			"workflow_name": "SLA Critical — Supervisor Alert",
			"enabled": 1,
			"priority": 20,
			"trigger_event": "SLA Critical",
			"description": "Alert department supervisor and bump priority at the configured SLA critical threshold.",
			"actions": [
				{
					"action_type": "Bump Priority",
				},
				{
					"action_type": "Send Notification",
					"recipient_type": "Department Supervisor",
					"message_template": "SLA critical: Ticket #{{ doc.name }} is near breach.",
				},
			],
		},
		{
			"workflow_name": "System Outage — Urgent IT",
			"enabled": 1,
			"priority": 30,
			"trigger_event": "Ticket Created",
			"condition": 'doc.ticket_type == "IT - System Downtime"',
			"description": "Auto-escalate system outage tickets to Urgent priority.",
			"actions": [
				{
					"action_type": "Set Field",
					"field_name": "priority",
					"value": "Urgent",
				},
				{
					"action_type": "Send Notification",
					"recipient_type": "Department Supervisor",
					"message_template": "System outage ticket #{{ doc.name }} created — priority set to Urgent.",
				},
			],
		},
		{
			"workflow_name": "KYC Update — Compliance Task",
			"enabled": 1,
			"priority": 40,
			"trigger_event": "Ticket Created",
			"condition": 'doc.sub_issue_type == "KYC Update"',
			"description": "Create compliance follow-up task for KYC tickets.",
			"actions": [
				{
					"action_type": "Create ToDo",
					"recipient_type": "Department Supervisor",
					"message_template": "Review KYC documents for ticket #{{ doc.name }}.",
				},
			],
		},
	]

	for spec in _defaults:
		if frappe.db.exists("MCX Service Workflow", spec["workflow_name"]):
			continue
		actions = spec.pop("actions")
		doc = frappe.get_doc({"doctype": "MCX Service Workflow", **spec})
		for action in actions:
			doc.append("actions", action)
		doc.insert(ignore_permissions=True)


def ensure_ai_settings():
	if not frappe.db.exists("DocType", "MCX AI Settings"):
		return
	if frappe.db.exists("MCX AI Settings", "MCX AI Settings"):
		settings = frappe.get_single("MCX AI Settings")
		changed = False
		if not settings.get("enable_customer_chatbot"):
			settings.enable_customer_chatbot = 1
			changed = True
		if not settings.get("chatbot_welcome_message"):
			settings.chatbot_welcome_message = (
				"Hi! I can help with common questions about MCX support, tickets, portal access, "
				"trading, and settlement. What would you like to know?"
			)
			changed = True
		if changed:
			settings.save(ignore_permissions=True)
		return
	frappe.get_doc(
		{
			"doctype": "MCX AI Settings",
			"enabled": 0,
			"provider": "OpenAI",
			"model": "gpt-4o-mini",
			"classify_on_create": 1,
			"suggest_reply": 1,
			"summarize_ticket": 1,
			"enable_customer_chatbot": 1,
			"chatbot_use_ai": 1,
			"chatbot_welcome_message": (
				"Hi! I can help with common questions about MCX support, tickets, portal access, "
				"trading, and settlement. What would you like to know?"
			),
			"max_tokens": 800,
			"temperature": 0.2,
		}
	).insert(ignore_permissions=True)


def ensure_sla_alert_settings():
	if not frappe.db.exists("DocType", "MCX SLA Alert Settings"):
		return
	if frappe.db.exists("MCX SLA Alert Settings", "MCX SLA Alert Settings"):
		return
	frappe.get_doc(
		{
			"doctype": "MCX SLA Alert Settings",
			"enabled": 1,
			"warning_threshold_pct": 75,
			"critical_threshold_pct": 90,
			"notify_assignee": 1,
			"notify_supervisor": 1,
			"supervisor_board_refresh_seconds": 30,
		}
	).insert(ignore_permissions=True)


def ensure_automation_setup():
	if "helpdesk" not in frappe.get_installed_apps():
		return
	ensure_automation_custom_fields()
	ensure_default_workflows()
	ensure_ai_settings()
	ensure_sla_alert_settings()
