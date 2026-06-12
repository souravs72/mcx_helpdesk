# Copyright (c) 2026, Ascra Technologies LLP and contributors
# For license information, please see license.txt

from __future__ import annotations

from typing import Any

import frappe

from helpdesk.utils import agent_only

# Exact-string replacements for dashboard API responses (charts, axes, empty labels).
DASHBOARD_LABEL_MAP = {
	"No Team": "No Department",
	"Tickets by Team": "Tickets by Department",
	"Percentage of total tickets by team": "Percentage of total tickets by department",
	"Total tickets by team": "Total tickets by department",
	"Tickets by Type": "Tickets by Issue Type",
	"Percentage of total tickets by type": "Percentage of total tickets by issue type",
	"Total tickets by type": "Total tickets by issue type",
	"Team": "Department",
	"Type": "Issue Type",
}


def _relabel_value(value: Any) -> Any:
	if isinstance(value, str):
		return DASHBOARD_LABEL_MAP.get(value, value)
	if isinstance(value, dict):
		return {key: _relabel_value(item) for key, item in value.items()}
	if isinstance(value, list):
		return [_relabel_value(item) for item in value]
	return value


@frappe.whitelist()
@agent_only
def get_dashboard_data(dashboard_type: str, filters: dict | None = None):
	"""MCX wrapper: relabel Team/Type chart titles for Department/Issue Type."""
	from helpdesk.api.dashboard import get_dashboard_data as helpdesk_get_dashboard_data

	data = helpdesk_get_dashboard_data(dashboard_type, filters)
	return _relabel_value(data)
