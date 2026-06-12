# Copyright (c) 2026, Ascra Technologies LLP and contributors
# For license information, please see license.txt

from __future__ import annotations

from typing import Any

import frappe
from frappe.utils import add_days, nowdate

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


def _parse_dashboard_filters(filters: dict | None) -> dict:
	filters = frappe.parse_json(filters) if isinstance(filters, str) else (filters or {})
	from_date = filters.get("from_date") or add_days(nowdate(), -30)
	to_date = filters.get("to_date") or nowdate()
	agent = filters.get("agent")
	if agent == "@me":
		agent = frappe.session.user

	query_filters = {
		"creation": ["between", [from_date, to_date]],
		"sla": ["is", "set"],
	}
	if filters.get("team"):
		query_filters["agent_group"] = filters["team"]
	if agent:
		query_filters["_assign"] = ["like", f"%{agent}%"]
	return query_filters


def get_sla_compliance_chart(filters: dict | None = None) -> dict:
	"""Pie chart: SLA Compliant (Fulfilled) vs SLA Breached (Failed) as % of closed SLA tickets."""
	from helpdesk.api.dashboard import get_pie_chart_config

	query_filters = _parse_dashboard_filters(filters)
	compliant = frappe.db.count(
		"HD Ticket", {**query_filters, "agreement_status": "Fulfilled"}
	)
	breached = frappe.db.count("HD Ticket", {**query_filters, "agreement_status": "Failed"})

	result = [
		{"status": "SLA Compliant", "count": compliant},
		{"status": "SLA Breached", "count": breached},
	]

	return get_pie_chart_config(
		result,
		"SLA Compliance",
		"Percentage of SLA-tracked tickets that met vs breached SLA",
		"status",
		"count",
	)


@frappe.whitelist()
@agent_only
def get_dashboard_data(dashboard_type: str, filters: dict | None = None):
	"""MCX wrapper: relabel charts and append SLA compliance chart."""
	from helpdesk.api.dashboard import get_dashboard_data as helpdesk_get_dashboard_data

	data = helpdesk_get_dashboard_data(dashboard_type, filters)
	data = _relabel_value(data)

	if dashboard_type == "master" and isinstance(data, list):
		data = [*data, get_sla_compliance_chart(filters)]

	return data
