# Copyright (c) 2026, Ascra Technologies LLP and contributors
# For license information, please see license.txt

"""Read proactive SLA alert configuration from MCX SLA Alert Settings."""

from __future__ import annotations

import frappe

DEFAULT_WARNING_THRESHOLD_PCT = 75
DEFAULT_CRITICAL_THRESHOLD_PCT = 90
DEFAULT_BOARD_REFRESH_SECONDS = 30


def get_sla_alert_settings() -> dict:
	if not frappe.db.exists("DocType", "MCX SLA Alert Settings"):
		return _defaults()

	settings = frappe.get_single("MCX SLA Alert Settings")
	warning = frappe.utils.cint(settings.warning_threshold_pct) or DEFAULT_WARNING_THRESHOLD_PCT
	critical = frappe.utils.cint(settings.critical_threshold_pct) or DEFAULT_CRITICAL_THRESHOLD_PCT

	if warning >= critical:
		warning = DEFAULT_WARNING_THRESHOLD_PCT
		critical = DEFAULT_CRITICAL_THRESHOLD_PCT

	return {
		"enabled": bool(settings.enabled),
		"warning_threshold_pct": min(max(warning, 1), 99),
		"critical_threshold_pct": min(max(critical, 2), 100),
		"notify_assignee": bool(settings.get("notify_assignee", 1)),
		"notify_supervisor": bool(settings.get("notify_supervisor", 1)),
		"supervisor_board_refresh_seconds": max(
			frappe.utils.cint(settings.supervisor_board_refresh_seconds) or DEFAULT_BOARD_REFRESH_SECONDS,
			10,
		),
	}


def _defaults() -> dict:
	return {
		"enabled": True,
		"warning_threshold_pct": DEFAULT_WARNING_THRESHOLD_PCT,
		"critical_threshold_pct": DEFAULT_CRITICAL_THRESHOLD_PCT,
		"notify_assignee": True,
		"notify_supervisor": True,
		"supervisor_board_refresh_seconds": DEFAULT_BOARD_REFRESH_SECONDS,
	}
