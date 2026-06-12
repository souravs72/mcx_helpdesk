# Copyright (c) 2026, Ascra Technologies LLP and contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe

from mcx_helpdesk.setup.install import ensure_sub_issue_field_dependency, ensure_ticket_template_field


def execute():
	ensure_ticket_template_field()
	ensure_sub_issue_field_dependency()
	_update_custom_field()
	frappe.db.commit()


def _update_custom_field():
	name = "HD Ticket-sub_issue_type"
	if not frappe.db.exists("Custom Field", name):
		return
	frappe.db.set_value(
		"Custom Field",
		name,
		{
			"depends_on": "eval:doc.ticket_type",
			"link_filters": '[["HD Sub Issue Type","issue_type","=","eval:doc.ticket_type"]]',
			"module": "MCX Helpdesk",
		},
	)
