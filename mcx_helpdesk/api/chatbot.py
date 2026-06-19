# Copyright (c) 2026, Ascra Technologies LLP and contributors
# For license information, please see license.txt

"""Customer-facing FAQ chatbot API."""

from __future__ import annotations

import json

import frappe
from frappe.rate_limiter import rate_limit

from mcx_helpdesk.mcx_helpdesk.ai_chatbot import answer_faq_question, get_chatbot_config


@frappe.whitelist(allow_guest=True)
def get_config() -> dict:
	return get_chatbot_config()


@frappe.whitelist(allow_guest=True)
@rate_limit(key="mcx_faq_chatbot", limit=30, seconds=60 * 60)
def ask(message: str, history: str | None = None) -> dict:
	parsed_history = []
	if history:
		try:
			parsed_history = json.loads(history)
			if not isinstance(parsed_history, list):
				parsed_history = []
		except json.JSONDecodeError:
			parsed_history = []
	return answer_faq_question(message, parsed_history)
