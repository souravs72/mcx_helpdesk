# Copyright (c) 2026, Ascra Technologies LLP and contributors
# For license information, please see license.txt

"""Production-safe idempotent sync — runs on install and every migrate."""

from __future__ import annotations

import frappe

from mcx_helpdesk.setup.dashboard_labels import ensure_dashboard_labels
from mcx_helpdesk.setup.data_cleanup import cleanup_helpdesk_data
from mcx_helpdesk.setup.demo import setup_demo_site
from mcx_helpdesk.setup.escalation import ensure_escalation_setup
from mcx_helpdesk.setup.install import (
	configure_email_account,
	configure_hd_settings,
	disable_legacy_teams,
	ensure_custom_field_metadata,
	ensure_custom_fields,
	ensure_default_sla,
	ensure_issue_types,
	ensure_labels,
	ensure_sub_issue_field_dependency,
	ensure_sub_issue_types,
	ensure_ticket_template_field,
)


def sync_mcx_helpdesk():
	"""Apply MCX Helpdesk configuration (safe for production; idempotent)."""
	if "helpdesk" not in frappe.get_installed_apps():
		return

	ensure_custom_fields()
	ensure_custom_field_metadata()
	ensure_labels()
	ensure_issue_types()
	ensure_sub_issue_types()
	ensure_ticket_template_field()
	ensure_sub_issue_field_dependency()
	disable_legacy_teams()
	ensure_dashboard_labels()
	cleanup_helpdesk_data()
	ensure_default_sla()
	configure_hd_settings()
	configure_email_account()
	ensure_escalation_setup()

	frappe.db.commit()
	_clear_caches()


def after_install():
	sync_mcx_helpdesk()
	setup_demo_site()
	frappe.db.commit()
	_clear_caches()


def after_migrate():
	sync_mcx_helpdesk()


def _clear_caches():
	frappe.clear_cache()
	try:
		from frappe.translate import clear_cache as clear_translation_cache

		clear_translation_cache()
	except Exception:
		pass
