# Copyright (c) 2026, Ascra Technologies LLP and contributors
# For license information, please see license.txt

"""Desk API for AI-assisted resolution."""

from __future__ import annotations

import frappe
from helpdesk.utils import agent_only

from mcx_helpdesk.mcx_helpdesk.ai_assist import is_ai_enabled, suggest_reply, summarize_ticket


@frappe.whitelist()
@agent_only
def get_ai_status() -> dict:
	return {
		"enabled": is_ai_enabled(),
		"suggest_reply": is_ai_enabled("suggest_reply"),
		"summarize_ticket": is_ai_enabled("summarize_ticket"),
	}


@frappe.whitelist()
@agent_only
def get_suggested_reply(ticket_id: str) -> dict:
	frappe.has_permission("HD Ticket", doc=ticket_id, throw=True)
	return suggest_reply(ticket_id)


@frappe.whitelist()
@agent_only
def get_ticket_summary(ticket_id: str) -> dict:
	frappe.has_permission("HD Ticket", doc=ticket_id, throw=True)
	return summarize_ticket(ticket_id)
