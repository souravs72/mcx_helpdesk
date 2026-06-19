# Copyright (c) 2026, Ascra Technologies LLP and contributors

import frappe

from mcx_helpdesk.setup.faq import ensure_faq_setup


def execute():
	ensure_faq_setup()
	frappe.db.commit()
