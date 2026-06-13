# Copyright (c) 2026, Ascra Technologies LLP and contributors
# For license information, please see license.txt

from __future__ import annotations

import operator
from functools import reduce
from typing import Any

import frappe
from frappe.query_builder import DocType
from frappe.query_builder.functions import Avg, Count, Function
from frappe.utils import add_days, getdate, nowdate
from pypika import Case

from helpdesk.utils import agent_only

# Exact-string replacements for dashboard API responses (charts, axes, empty labels).
DASHBOARD_LABEL_MAP = {
	"No Team": "No Department",
	"Team": "Department",
	"Tickets by Team": "Tickets by Department",
	"Percentage of total tickets by team": "Percentage of total tickets by department",
	"Total tickets by team": "Total tickets by department",
	"Tickets by Type": "Tickets by Issue Type",
	"Percentage of total tickets by type": "Percentage of total tickets by issue type",
	"Total tickets by type": "Total tickets by issue type",
	"Type": "Issue Type",
}


def _relabel_department_name(value: str | None) -> str:
	if not value:
		return "No Department"
	if value in ("No Team", "No Department"):
		return "No Department"
	if value.endswith(" Team"):
		return value[:-5].strip() or value
	return DASHBOARD_LABEL_MAP.get(value, value)


TICKET_LIST_FIELDS = [
	"name",
	"subject",
	"status",
	"priority",
	"priority.integer_value as priority_integer_value",
	"agent_group",
	"agreement_status",
	"creation",
]

DEFAULT_PAGE_LENGTH = 20
MAX_PAGE_LENGTH = 100
PAGE_LENGTH_OPTIONS = [20, 50, 100]


def _normalize_page_length(limit) -> int:
	return min(max(frappe.utils.cint(limit) or DEFAULT_PAGE_LENGTH, 1), MAX_PAGE_LENGTH)


def _paginate_rows(rows: list, limit) -> dict:
	limit = _normalize_page_length(limit)
	page = rows[:limit]
	return {
		"rows": page,
		"total_count": len(rows),
		"row_count": len(page),
		"page_length_options": PAGE_LENGTH_OPTIONS,
	}


def _relabel_value(value: Any) -> Any:
	if isinstance(value, str):
		return DASHBOARD_LABEL_MAP.get(value, value)
	if isinstance(value, dict):
		return {key: _relabel_value(item) for key, item in value.items()}
	if isinstance(value, list):
		return [_relabel_value(item) for item in value]
	return value


def _clean_chart(chart: dict) -> dict:
	"""Normalize MCX labels and drop empty pie slices."""
	if not chart or not isinstance(chart, dict):
		return chart

	chart = _relabel_value(chart)
	category_col = chart.get("categoryColumn")
	value_col = chart.get("valueColumn") or "count"

	if chart.get("data") and category_col:
		for row in chart["data"]:
			if isinstance(row.get(category_col), str):
				if category_col in ("team", "dept", "agent_group"):
					row[category_col] = _relabel_department_name(row[category_col])
				else:
					row[category_col] = DASHBOARD_LABEL_MAP.get(row[category_col], row[category_col])
		if chart.get("type") == "pie":
			chart["data"] = [
				row for row in chart["data"]
				if float(row.get(value_col) or 0) > 0
			]

	x_axis = chart.get("xAxis")
	if isinstance(x_axis, dict):
		key = x_axis.get("key")
		if x_axis.get("title") == "Team":
			x_axis["title"] = "Department"
		if key == "team":
			for row in chart.get("data") or []:
				if "team" in row and isinstance(row["team"], str):
					row["team"] = _relabel_department_name(row["team"])

	return chart


def _parse_filters(filters: dict | str | None) -> dict:
	if isinstance(filters, str):
		filters = frappe.parse_json(filters)
	return filters or {}


def _require_manager():
	user = frappe.session.user
	if "Agent Manager" not in frappe.get_roles(user):
		frappe.throw("Only managers can access this resource.", frappe.PermissionError)


def _status_lists():
	resolved = frappe.get_all("HD Ticket Status", filters={"category": "Resolved"}, pluck="name")
	open_statuses = frappe.get_all("HD Ticket Status", filters={"category": "Open"}, pluck="name")
	return resolved, open_statuses


def _agent_assign_cond(ticket, agent_email):
	return Function("JSON_SEARCH", ticket._assign, "one", agent_email).isnotnull()


def _period_end(to_date):
	"""Exclusive upper bound = start of the day after to_date.

	Matches the upstream Helpdesk dashboard (``creation < add_days(to_date, 1)``)
	so a bare ``to_date`` includes tickets created any time on that day.
	"""
	return add_days(getdate(to_date), 1)


def _period_cond(ticket, from_date, to_date):
	return (ticket.creation >= getdate(from_date)) & (ticket.creation < _period_end(to_date))


def _unassigned_cond(ticket):
	"""Open ticket has no assignee: _assign is NULL or empty (Frappe writes ``""``)."""
	return ticket._assign.isnull() | (ticket._assign == "")


def _assign_emails(raw) -> list[str]:
	"""Parse HD Ticket ``_assign`` JSON the same way Frappe desk does."""
	if not raw:
		return []
	try:
		parsed = frappe.parse_json(raw)
	except Exception:
		return []
	if isinstance(parsed, list):
		return [e for e in parsed if e]
	return []


def _team_cond(ticket, team: str | None):
	if not team:
		return None
	return ticket.agent_group == team


def _combine_conditions(*conds):
	active = [c for c in conds if c is not None]
	if not active:
		return None
	return reduce(operator.and_, active)


def _sla_rate_pct(fulfilled: int, failed_base: int) -> float:
	return round(fulfilled / failed_base * 100, 1) if failed_base else 0.0


def _count_where(ticket, cond):
	if cond is None:
		return 0
	return (
		frappe.qb.from_(ticket).select(Count(ticket.name).as_("n")).where(cond).run(pluck="n") or [0]
	)[0]


def _agent_emails_for_team(team: str | None) -> list[str] | None:
	"""Return team member emails, or None when no team filter is applied."""
	if not team:
		return None
	members = frappe.db.get_all(
		"HD Team Member",
		filters={"parent": team},
		pluck="user",
		ignore_permissions=True,
	)
	return [email for email in members if email]


def _build_resource_cards(team: str | None = None) -> list[dict]:
	"""Current workload snapshot for the By Department view (ticket-based, not availability status)."""
	member_emails = _agent_emails_for_team(team)
	if team and not member_emails:
		return _empty_resource_cards(team)

	agent_filters: dict | list = {"is_active": 1}
	if member_emails is not None:
		agent_filters = [["is_active", "=", 1], ["user", "in", member_emails]]

	agents = frappe.get_all(
		"HD Agent",
		filters=agent_filters,
		fields=["user"],
		ignore_permissions=True,
	)
	total_agents = len(agents)

	_, open_statuses = _status_lists()
	ticket = DocType("HD Ticket")
	open_cond = _combine_conditions(
		ticket.status.isin(open_statuses) if open_statuses else None,
		_team_cond(ticket, team),
	)
	open_tickets = _count_where(ticket, open_cond)

	unassigned_cond = _combine_conditions(open_cond, _unassigned_cond(ticket))
	unassigned = _count_where(ticket, unassigned_cond)

	# Distinct active agents currently assigned to an open ticket — single query, parsed in Python.
	assigned_agents = 0
	if open_statuses:
		active_emails = {a.user for a in agents if a.user}
		open_assigns = (
			frappe.qb.from_(ticket).select(ticket._assign).where(open_cond).run(pluck=True)
		)
		assigned_set: set[str] = set()
		for raw in open_assigns:
			assigned_set.update(_assign_emails(raw))
		assigned_agents = len(assigned_set & active_emails)

	scope = f" in {team}" if team else ""
	return [
		{
			"title": "Total Agents",
			"value": total_agents,
			"tooltip": f"Active agents{scope}",
			"section": "resource",
		},
		{
			"title": "Open Tickets",
			"value": open_tickets,
			"tooltip": f"Tickets currently open{scope}",
			"section": "resource",
			"accent": "amber" if open_tickets else "default",
		},
		{
			"title": "Assigned Agents",
			"value": assigned_agents,
			"tooltip": f"Agents with at least one open ticket{scope}",
			"section": "resource",
		},
		{
			"title": "Unassigned Tickets",
			"value": unassigned,
			"tooltip": f"Open tickets with no assignee{scope}",
			"section": "resource",
			"accent": "red" if unassigned else "default",
		},
	]


def _empty_resource_cards(team: str | None = None) -> list[dict]:
	scope = f" in {team}" if team else ""
	return [
		{"title": "Total Agents", "value": 0, "tooltip": f"Active agents{scope}", "section": "resource"},
		{
			"title": "Open Tickets",
			"value": 0,
			"tooltip": f"Tickets currently open{scope}",
			"section": "resource",
		},
		{
			"title": "Assigned Agents",
			"value": 0,
			"tooltip": f"Agents with at least one open ticket{scope}",
			"section": "resource",
		},
		{
			"title": "Unassigned Tickets",
			"value": 0,
			"tooltip": f"Open tickets with no assignee{scope}",
			"section": "resource",
		},
	]

@frappe.whitelist()
@agent_only
def get_dashboard_data(dashboard_type: str, filters: dict | None = None):
	"""MCX wrapper: relabel charts and unify SLA % on number cards."""
	from helpdesk.api.dashboard import get_dashboard_data as helpdesk_get_dashboard_data

	filters = _parse_filters(filters)
	data = helpdesk_get_dashboard_data(dashboard_type, filters)
	data = _relabel_value(data)

	if dashboard_type == "number_card" and isinstance(data, list):
		data = _patch_number_cards(data, filters)
	elif dashboard_type == "master" and isinstance(data, list):
		data = [_clean_chart(chart) for chart in _filter_master_charts(data)]
	elif dashboard_type == "trend" and isinstance(data, list):
		data = [_clean_chart(chart) for chart in data if not _is_feedback_trend_empty(chart)]

	return data


def _patch_number_cards(cards: list[dict], filters: dict) -> list[dict]:
	"""Recalculate SLA % using fulfilled / (fulfilled + failed) for consistency."""
	from_date = filters.get("from_date") or add_days(nowdate(), -30)
	to_date = filters.get("to_date") or nowdate()
	team = filters.get("team")

	ticket = DocType("HD Ticket")
	period = _period_cond(ticket, from_date, to_date)
	team_filter = _team_cond(ticket, team)
	base = _combine_conditions(period, team_filter)

	fulfilled = _count_where(ticket, base & (ticket.agreement_status == "Fulfilled"))
	sla_base = _count_where(
		ticket, base & ticket.agreement_status.isin(["Fulfilled", "Failed"])
	)
	sla_pct = _sla_rate_pct(fulfilled, sla_base)
	closed_cond = _combine_conditions(
		ticket.resolution_date.isnotnull(),
		ticket.resolution_date >= getdate(from_date),
		ticket.resolution_date < _period_end(to_date),
		team_filter,
	)
	closed_count = _count_where(ticket, closed_cond)

	patched = []
	for card in cards:
		title = card.get("title", "")
		value = card.get("value") or 0

		if title == "Tickets":
			card = {
				**card,
				"title": "New Tickets",
				"tooltip": "Tickets created in the selected date range",
			}
		elif "% SLA Fulfilled" in title or title == "% SLA Fulfilled":
			card = {
				**card,
				"title": "% SLA Fulfilled",
				"value": sla_pct,
				"suffix": "%",
				"tooltip": "% of SLA-tracked tickets fulfilled (not breached)",
			}
		elif title == "Avg. Feedback Rating" and not value:
			continue

		patched.append(card)
		if card.get("title") == "New Tickets":
			patched.append(
				{
					"title": "Closed Tickets",
					"value": closed_count,
					"tooltip": "Tickets resolved in the selected date range",
					"section": "period",
				}
			)

	for card in patched:
		card["section"] = "period"
	return patched


def _filter_master_charts(charts: list[dict]) -> list[dict]:
	"""Drop empty pie charts; order by ticketing relevance."""
	filtered = []
	for chart in charts:
		title = (chart.get("title") or "").lower()
		if _is_pie_single_or_empty(chart) and not any(
			k in title for k in ("department", "issue type", "priority", "channel", "team")
		):
			continue
		filtered.append(chart)

	def _rank(chart: dict) -> int:
		title = (chart.get("title") or "").lower()
		if "department" in title or "team" in title:
			return 0
		if "issue type" in title or "type" in title:
			return 1
		if "priority" in title:
			return 2
		if "channel" in title:
			return 3
		return 4

	filtered.sort(key=_rank)
	return filtered


def _is_pie_single_or_empty(chart: dict) -> bool:
	if chart.get("type") != "pie":
		return False
	data = chart.get("data") or []
	col = chart.get("valueColumn") or "count"
	non_zero = [r for r in data if Number(r.get(col)) > 0]
	return len(non_zero) <= 1


def _is_feedback_trend_empty(chart: dict) -> bool:
	title = (chart.get("title") or "").lower()
	if "feedback" not in title:
		return False
	data = chart.get("data") or []
	if not data:
		return True
	return all(
		(r.get("Rated Tickets") or 0) == 0 and (r.get("Rating") or 0) == 0 for r in data
	)


def Number(val):
	try:
		return float(val or 0)
	except (TypeError, ValueError):
		return 0


@frappe.whitelist()
@agent_only
def get_team_list() -> list[dict]:
	"""Manager-only: all active HD Teams as autocomplete options."""
	_require_manager()
	teams = frappe.db.get_all(
		"HD Team",
		fields=["name", "team_name"],
		order_by="team_name asc",
		ignore_permissions=True,
	)
	return [{"value": t.name, "label": t.team_name or t.name} for t in teams]


@frappe.whitelist()
@agent_only
def get_agent_list(team: str | None = None) -> list[dict]:
	"""Manager-only: active agents as autocomplete options, optionally filtered by team."""
	_require_manager()

	if team:
		# Fetch users who are members of this team
		members = frappe.db.get_all(
			"HD Team Member",
			filters={"parent": team},
			fields=["user"],
			ignore_permissions=True,
		)
		user_emails = {m.user for m in members if m.user}
		if not user_emails:
			return []
		agents = frappe.db.get_all(
			"HD Agent",
			filters=[["is_active", "=", 1], ["user", "in", list(user_emails)]],
			fields=["user", "agent_name"],
			order_by="agent_name asc",
			ignore_permissions=True,
		)
	else:
		agents = frappe.db.get_all(
			"HD Agent",
			filters={"is_active": 1},
			fields=["user", "agent_name"],
			order_by="agent_name asc",
			ignore_permissions=True,
		)
	return [
		{"value": a.user, "label": a.agent_name or a.user}
		for a in agents
		if a.user
	]


def _build_agent_period_cond(ticket, agent_email, from_date, to_date):
	return _combine_conditions(
		_period_cond(ticket, from_date, to_date),
		_agent_assign_cond(ticket, agent_email),
	)


def _build_agent_open_cond(ticket, agent_email, open_statuses):
	if not open_statuses:
		return None
	return _combine_conditions(
		_agent_assign_cond(ticket, agent_email),
		ticket.status.isin(open_statuses),
	)


@frappe.whitelist()
@agent_only
def get_agent_stats(agent_email: str | None = None, filters: dict | None = None) -> dict:
	"""
	Personal KPIs for a single agent.
	Open workload uses current assignments; historical metrics use the date range.
	"""
	filters = _parse_filters(filters)

	user = frappe.session.user
	is_manager = "Agent Manager" in frappe.get_roles(user)

	if not agent_email or agent_email == "@me":
		agent_email = user
	if not is_manager and agent_email != user:
		frappe.throw("You are not allowed to view another agent's stats.", frappe.PermissionError)

	from_date = filters.get("from_date") or add_days(nowdate(), -30)
	to_date = filters.get("to_date") or nowdate()
	team = filters.get("team")

	ticket = DocType("HD Ticket")
	resolved_statuses, open_statuses = _status_lists()

	period_cond = _build_agent_period_cond(ticket, agent_email, from_date, to_date)
	open_cond = _build_agent_open_cond(ticket, agent_email, open_statuses)
	if team:
		period_cond = _combine_conditions(period_cond, _team_cond(ticket, team))
		open_cond = _combine_conditions(open_cond, _team_cond(ticket, team))

	def _count_period(extra_cond=None):
		cond = _combine_conditions(period_cond, extra_cond)
		return _count_where(ticket, cond)

	def _count_open(extra_cond=None):
		cond = _combine_conditions(open_cond, extra_cond)
		return _count_where(ticket, cond)

	total = _count_period()
	open_tickets = _count_open()
	resolved = _count_period(ticket.status.isin(resolved_statuses)) if resolved_statuses else 0
	escalated_open = _count_open(ticket.mcx_sla_breach_escalated == 1)
	escalated_period = _count_period(ticket.mcx_sla_breach_escalated == 1)

	awaiting_response = _count_open(ticket.first_responded_on.isnull())
	sla_at_risk = _count_open(
		ticket.agreement_status.isin(["First Response Due", "Resolution Due"])
	)
	breached_open = _count_open(ticket.agreement_status == "Failed")

	fulfilled = _count_period(ticket.agreement_status == "Fulfilled")
	sla_base = _count_period(ticket.agreement_status.isin(["Fulfilled", "Failed"]))
	sla_rate_pct = _sla_rate_pct(fulfilled, sla_base)

	avg_resp_result = (
		frappe.qb.from_(ticket)
		.select((Avg(ticket.first_response_time) / 3600).as_("hrs"))
		.where(_combine_conditions(period_cond, ticket.first_responded_on.isnotnull()))
		.run(pluck="hrs")
		or [None]
	)[0]
	avg_first_response_hrs = round(float(avg_resp_result), 1) if avg_resp_result else None

	if resolved_statuses:
		avg_resol_result = (
			frappe.qb.from_(ticket)
			.select(Avg(Function("CEIL", ticket.resolution_time / 86400)).as_("days"))
			.where(_combine_conditions(period_cond, ticket.status.isin(resolved_statuses)))
			.run(pluck="days")
			or [None]
		)[0]
	else:
		avg_resol_result = None
	avg_resolution_days = round(float(avg_resol_result), 1) if avg_resol_result else None

	avg_fb_result = (
		frappe.qb.from_(ticket)
		.select((Avg(ticket.feedback_rating) * 5).as_("fb"))
		.where(_combine_conditions(period_cond, ticket.feedback_rating > 0))
		.run(pluck="fb")
		or [None]
	)[0]
	avg_feedback = round(float(avg_fb_result), 1) if avg_fb_result else None

	trend_rows = (
		frappe.qb.from_(ticket)
		.select(
			Function("DATE", ticket.creation).as_("date"),
			Count(Case().when(ticket.status.isin(open_statuses), ticket.name).else_(None)).as_(
				"Open"
			),
			Count(
				Case().when(ticket.status.isin(resolved_statuses), ticket.name).else_(None)
			).as_("Resolved"),
			Count(Case().when(ticket.agreement_status == "Fulfilled", ticket.name).else_(None)).as_(
				"_fulfilled"
			),
			Count(
				Case()
				.when(ticket.agreement_status.isin(["Fulfilled", "Failed"]), ticket.name)
				.else_(None)
			).as_("_sla_base"),
		)
		.where(period_cond)
		.groupby(Function("DATE", ticket.creation))
		.orderby(Function("DATE", ticket.creation))
		.run(as_dict=True)
	)
	ticket_trend = []
	for row in trend_rows:
		base = row.pop("_sla_base", 0) or 0
		ful = row.pop("_fulfilled", 0) or 0
		row["SLA %"] = round(ful / base * 100, 1) if base else 0
		ticket_trend.append(row)

	by_type = (
		frappe.qb.from_(ticket)
		.select(ticket.ticket_type.as_("type"), Count(ticket.name).as_("count"))
		.where(period_cond)
		.groupby(ticket.ticket_type)
		.orderby(Count(ticket.name), order=frappe.qb.desc)
		.run(as_dict=True)
	)
	for r in by_type:
		if not r.get("type"):
			r["type"] = "Unclassified"

	by_priority = (
		frappe.qb.from_(ticket)
		.select(ticket.priority.as_("priority"), Count(ticket.name).as_("count"))
		.where(period_cond)
		.groupby(ticket.priority)
		.orderby(Count(ticket.name), order=frappe.qb.desc)
		.run(as_dict=True)
	)
	for r in by_priority:
		if not r.get("priority"):
			r["priority"] = "None"

	return {
		"agent_email": agent_email,
		"total_tickets": total,
		"open_tickets": open_tickets,
		"awaiting_response": awaiting_response,
		"sla_at_risk": sla_at_risk,
		"breached_open": breached_open,
		"resolved_tickets": resolved,
		"escalated_tickets": escalated_period,
		"escalated_open": escalated_open,
		"sla_rate_pct": sla_rate_pct,
		"avg_first_response_hrs": avg_first_response_hrs,
		"avg_resolution_days": avg_resolution_days,
		"avg_feedback": avg_feedback,
		"ticket_trend": ticket_trend,
		"by_type": by_type,
		"by_priority": by_priority,
	}


@frappe.whitelist()
@agent_only
def get_department_stats(filters: dict | None = None, limit: int = DEFAULT_PAGE_LENGTH) -> dict:
	"""Manager-only: per-department summary rows."""
	_require_manager()

	filters = _parse_filters(filters)
	from_date = filters.get("from_date") or add_days(nowdate(), -30)
	to_date = filters.get("to_date") or nowdate()
	team = filters.get("team")

	ticket = DocType("HD Ticket")
	resolved_statuses, open_statuses = _status_lists()
	base_cond = _combine_conditions(_period_cond(ticket, from_date, to_date), _team_cond(ticket, team))

	rows = (
		frappe.qb.from_(ticket)
		.select(
			ticket.agent_group.as_("dept"),
			Count(ticket.name).as_("total"),
			Count(Case().when(ticket.status.isin(open_statuses), ticket.name).else_(None)).as_(
				"open"
			),
			Count(
				Case().when(ticket.status.isin(resolved_statuses), ticket.name).else_(None)
			).as_("resolved"),
			Count(Case().when(ticket.agreement_status == "Fulfilled", ticket.name).else_(None)).as_(
				"fulfilled"
			),
			Count(
				Case()
				.when(ticket.agreement_status.isin(["Fulfilled", "Failed"]), ticket.name)
				.else_(None)
			).as_("sla_total"),
			Avg(
				Case()
				.when(
					ticket.status.isin(resolved_statuses),
					Function("CEIL", ticket.resolution_time / 86400),
				)
				.else_(None)
			).as_("avg_resolution_days"),
			Count(Case().when(ticket.mcx_sla_breach_escalated == 1, ticket.name).else_(None)).as_(
				"escalated"
			),
		)
		.where(base_cond)
		.groupby(ticket.agent_group)
		.orderby(Count(ticket.name), order=frappe.qb.desc)
		.run(as_dict=True)
	)

	result = []
	for r in rows:
		result.append(
			{
				"dept": r.dept or "Unassigned",
				"total": r.total,
				"open": r.open,
				"resolved": r.resolved,
				"sla_rate_pct": _sla_rate_pct(r.fulfilled, r.sla_total),
				"avg_resolution_days": round(float(r.avg_resolution_days or 0), 1),
				"escalated": r.escalated,
			}
		)
	paginated = _paginate_rows(result, limit)
	paginated["chart_rows"] = result
	paginated["resource_cards"] = _build_resource_cards(team)
	return paginated


@frappe.whitelist()
@agent_only
def get_agent_leaderboard(filters: dict | None = None, limit: int = DEFAULT_PAGE_LENGTH) -> dict:
	"""Manager-only: ranked agent performance list."""
	_require_manager()

	filters = _parse_filters(filters)
	from_date = filters.get("from_date") or add_days(nowdate(), -30)
	to_date = filters.get("to_date") or nowdate()
	team = filters.get("team")

	agent_filters: dict | list = {"is_active": 1}
	if team:
		member_emails = _agent_emails_for_team(team)
		if not member_emails:
			return _paginate_rows([], limit)
		agent_filters = [["is_active", "=", 1], ["user", "in", member_emails]]

	agents = frappe.get_all(
		"HD Agent",
		fields=["name", "agent_name", "user"],
		filters=agent_filters,
		ignore_permissions=True,
	)
	resolved_statuses, open_statuses = _status_lists()
	ticket = DocType("HD Ticket")
	board = []

	for agent in agents:
		email = agent.user
		if not email:
			continue

		period_cond = _combine_conditions(
			_period_cond(ticket, from_date, to_date),
			_agent_assign_cond(ticket, email),
			_team_cond(ticket, team),
		)
		open_cond = _combine_conditions(
			_agent_assign_cond(ticket, email),
			ticket.status.isin(open_statuses) if open_statuses else None,
			_team_cond(ticket, team),
		)

		total = _count_where(ticket, period_cond)
		if total == 0 and _count_where(ticket, open_cond) == 0:
			continue

		resolved = (
			_count_where(ticket, _combine_conditions(period_cond, ticket.status.isin(resolved_statuses)))
			if resolved_statuses
			else 0
		)
		open_load = _count_where(ticket, open_cond)
		fulfilled = _count_where(ticket, _combine_conditions(period_cond, ticket.agreement_status == "Fulfilled"))
		sla_base = _count_where(
			ticket,
			_combine_conditions(period_cond, ticket.agreement_status.isin(["Fulfilled", "Failed"])),
		)
		breached_open = _count_where(
			ticket,
			_combine_conditions(open_cond, ticket.agreement_status == "Failed"),
		)

		avg_res = (
			frappe.qb.from_(ticket)
			.select(Avg(Function("CEIL", ticket.resolution_time / 86400)).as_("d"))
			.where(_combine_conditions(period_cond, ticket.status.isin(resolved_statuses)))
			.run(pluck="d")
			or [None]
		)[0] if resolved_statuses else None

		avg_fb = (
			frappe.qb.from_(ticket)
			.select((Avg(ticket.feedback_rating) * 5).as_("fb"))
			.where(_combine_conditions(period_cond, ticket.feedback_rating > 0))
			.run(pluck="fb")
			or [None]
		)[0]

		board.append(
			{
				"agent_name": agent.agent_name or email,
				"agent_email": email,
				"total": total,
				"open": open_load,
				"resolved": resolved,
				"breached_open": breached_open,
				"sla_rate_pct": _sla_rate_pct(fulfilled, sla_base),
				"avg_resolution_days": round(float(avg_res), 1) if avg_res else 0,
				"avg_feedback": round(float(avg_fb), 1) if avg_fb else 0,
			}
		)

	board.sort(key=lambda x: (-x["open"], -x["resolved"], -x["sla_rate_pct"]))
	return _paginate_rows(board, limit)


@frappe.whitelist()
@agent_only
def get_action_tickets(
	list_type: str = "upcoming_sla",
	filters: dict | None = None,
	agent_email: str | None = None,
	limit: int = DEFAULT_PAGE_LENGTH,
) -> dict:
	"""
	Actionable ticket lists for dashboard.
	Agents: upcoming_sla | new_tickets | pending | my_open
	Managers: unassigned | breached | escalated
	"""
	filters = _parse_filters(filters)
	user = frappe.session.user
	is_manager = "Agent Manager" in frappe.get_roles(user)

	if list_type in ("unassigned", "breached", "escalated"):
		if not is_manager:
			frappe.throw("Only managers can view org-wide action lists.", frappe.PermissionError)
		return _get_manager_action_tickets(list_type, filters, limit)

	if list_type in ("upcoming_sla", "new_tickets", "pending"):
		target = user
		if is_manager and agent_email:
			target = agent_email
		return _get_agent_pending_tickets(list_type, target, limit)

	if list_type == "my_open":
		target = agent_email or user
		if not is_manager and target != user:
			frappe.throw("You are not allowed to view another agent's tickets.", frappe.PermissionError)
		return _get_agent_open_tickets(target, limit)

	frappe.throw(f"Unknown list type: {list_type}", frappe.ValidationError)


def _ticket_list_response(tickets: list, total: int, list_type: str, **extra) -> dict:
	return {
		"tickets": tickets,
		"total_count": total,
		"row_count": len(tickets),
		"list_type": list_type,
		"page_length_options": PAGE_LENGTH_OPTIONS,
		**extra,
	}


def _get_manager_action_tickets(list_type: str, filters: dict | None = None, limit: int = DEFAULT_PAGE_LENGTH) -> dict:
	_require_manager()
	filters = filters or {}
	team = filters.get("team")
	limit = _normalize_page_length(limit)

	ticket = DocType("HD Ticket")
	cond = ticket.status_category == "Open"
	if team:
		cond = cond & (ticket.agent_group == team)

	if list_type == "unassigned":
		cond = cond & _unassigned_cond(ticket)
		reason_type, reason_text = "unassigned", "No assignee"
	elif list_type == "breached":
		cond = cond & (ticket.agreement_status == "Failed")
		reason_type, reason_text = "breached", "SLA breached"
	elif list_type == "escalated":
		cond = cond & (ticket.mcx_sla_breach_escalated == 1)
		reason_type, reason_text = "escalated", "Escalated"
	else:
		frappe.throw(f"Unknown manager list type: {list_type}")

	total = _count_where(ticket, cond)
	names = (
		frappe.qb.from_(ticket)
		.select(ticket.name)
		.where(cond)
		.orderby(ticket.modified, order=frappe.qb.desc)
		.limit(limit)
		.run(pluck=True)
	)
	tickets = (
		frappe.get_list(
			"HD Ticket",
			fields=TICKET_LIST_FIELDS,
			filters=[["name", "in", names]],
			order_by="modified desc",
			ignore_permissions=True,
		)
		if names
		else []
	)
	for t in tickets:
		t["reason"] = {"type": reason_type, "text": reason_text}

	return _ticket_list_response(tickets, total, list_type)


def _get_agent_pending_tickets(list_type: str, agent_email: str, limit: int = DEFAULT_PAGE_LENGTH) -> dict:
	"""Paginated pending-ticket lists for an agent (self or manager drilldown)."""
	from frappe.utils import add_months, add_to_date, now_datetime, today

	from helpdesk.api.agent_home.agent_home import (
		_get_priority_range,
		format_time_difference,
		get_ticket_count,
	)

	limit = _normalize_page_length(limit)

	if list_type == "upcoming_sla":
		filters = [
			["sla", "is", "set"],
			["agreement_status", "in", ["First Response Due", "Resolution Due"]],
			["status_category", "=", "Open"],
			["_assign", "like", f"%{agent_email}%"],
			["creation", "between", [add_months(today(), -6), today()]],
		]
		tickets = frappe.get_list(
			"HD Ticket",
			fields=TICKET_LIST_FIELDS + ["response_by", "resolution_by"],
			filters=filters,
			order_by="response_by asc",
			limit=limit,
		)
		for ticket in tickets:
			agreement_status = ticket.get("agreement_status", "")
			due_time = ticket.get("resolution_by") if agreement_status == "Resolution Due" else ticket.get("response_by")
			time_until = format_time_difference(due_time, context="until")
			if agreement_status == "Resolution Due":
				text = f"Resolution due in {time_until}" if time_until != "overdue" else "Resolution overdue"
			else:
				text = f"Response due in {time_until}" if time_until != "overdue" else "Response overdue"
			ticket["reason"] = {"type": "upcoming_sla", "text": text}
		total = get_ticket_count(filters)
	elif list_type == "new_tickets":
		one_week_ago = add_to_date(now_datetime(), days=-7)
		ToDo = DocType("ToDo")
		assigned = (
			frappe.qb.from_(ToDo)
			.select(ToDo.reference_name)
			.distinct()
			.where(ToDo.reference_type == "HD Ticket")
			.where(ToDo.allocated_to == agent_email)
			.where(ToDo.creation >= one_week_ago)
			.where(ToDo.status == "Open")
			.run(as_dict=False)
		)
		ticket_names = [row[0] for row in assigned]
		if not ticket_names:
			min_priority, max_priority = _get_priority_range()
			return _ticket_list_response(
				[],
				0,
				list_type,
				total_pending_tickets=0,
				min_priority=min_priority,
				max_priority=max_priority,
			)
		filters = [
			["name", "in", ticket_names],
			["_assign", "like", f"%{agent_email}%"],
			["status_category", "=", "Open"],
		]
		tickets = frappe.get_list(
			"HD Ticket",
			fields=TICKET_LIST_FIELDS,
			filters=filters,
			order_by="creation desc",
			limit=limit,
		)
		for ticket in tickets:
			ticket["reason"] = {"type": "new_tickets", "text": "Recently assigned"}
		total = get_ticket_count(filters=filters)
	elif list_type == "pending":
		filters = [
			["_assign", "like", f"%{agent_email}%"],
			["status_category", "=", "Open"],
			["last_customer_response", "is", "set"],
		]
		tickets = frappe.get_list(
			"HD Ticket",
			fields=TICKET_LIST_FIELDS + ["last_customer_response"],
			filters=filters,
			order_by="last_customer_response asc",
			limit=limit,
		)
		for ticket in tickets:
			time_ago = format_time_difference(ticket.get("last_customer_response"))
			ticket["reason"] = {"type": "pending", "text": f"Pending for {time_ago}"}
		total = get_ticket_count(filters)
	else:
		frappe.throw(f"Unknown list type: {list_type}")

	min_priority, max_priority = _get_priority_range()
	return _ticket_list_response(
		tickets,
		total,
		list_type,
		total_pending_tickets=total,
		min_priority=min_priority,
		max_priority=max_priority,
	)


def _get_agent_open_tickets(agent_email: str, limit: int = DEFAULT_PAGE_LENGTH) -> dict:
	_, open_statuses = _status_lists()
	if not open_statuses:
		return _ticket_list_response([], 0, "my_open")

	filters = [
		["status_category", "=", "Open"],
		["_assign", "like", f"%{agent_email}%"],
	]
	limit = _normalize_page_length(limit)
	total = frappe.db.count("HD Ticket", filters=filters)
	tickets = frappe.get_list(
		"HD Ticket",
		fields=TICKET_LIST_FIELDS,
		filters=filters,
		order_by="modified desc",
		limit=limit,
	)
	for ticket in tickets:
		ticket["reason"] = {"type": "my_open", "text": "Open"}

	return _ticket_list_response(tickets, total, "my_open")
