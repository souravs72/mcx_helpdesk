# Copyright (c) 2026, Ascra Technologies LLP and contributors
# For license information, please see license.txt

"""Read escalation matrix from MCX Escalation Settings (desk-configurable)."""

from __future__ import annotations

import frappe


def get_escalation_settings():
	if not frappe.db.exists("DocType", "MCX Escalation Settings"):
		return None
	return frappe.get_cached_doc("MCX Escalation Settings")


def get_l1_supervisor(team: str | None) -> str | None:
	"""L1 supervisor for proactive alerts / workflow notifications."""
	if not team:
		return None
	settings = get_escalation_settings()
	if not settings:
		return None
	row = next((r for r in settings.escalation_rules if r.team == team), None)
	return row.l1_user if row else None


def get_l2_supervisor(team: str | None) -> str | None:
	if not team:
		return None
	settings = get_escalation_settings()
	if not settings:
		return None
	row = next((r for r in settings.escalation_rules if r.team == team), None)
	return row.l2_user if row else None


def get_country_head() -> str | None:
	settings = get_escalation_settings()
	return settings.country_head_user if settings else None


def get_deputy_country_head() -> str | None:
	settings = get_escalation_settings()
	return settings.deputy_country_head_user if settings else None
