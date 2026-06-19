# Copyright (c) 2026, Ascra Technologies LLP and contributors
# For license information, please see license.txt

"""Override of helpdesk.helpdesk.doctype.hd_ticket.api.get_one.

Strips internal-only fields (agent comments, full activity log) from the
API response when the request comes from the customer portal, preventing
data leakage through the raw API payload.
"""

import frappe
from helpdesk.helpdesk.doctype.hd_ticket.api import get_one as _base_get_one


@frappe.whitelist()
def get_one(name: str, is_customer_portal: bool = False):
	result = _base_get_one(name=name, is_customer_portal=is_customer_portal)

	if is_customer_portal:
		# HD Ticket Comments are internal agent notes — never expose to customers.
		result.pop("comments", None)
		# The activity log (history) contains internal entries such as escalation
		# details, reassignment trails, and agent workflow notes.
		result.pop("history", None)
		# View logs (who opened the ticket and when) are internal audit data.
		result.pop("views", None)

	return result
