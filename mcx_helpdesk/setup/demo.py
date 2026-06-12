# Copyright (c) 2026, Ascra Technologies LLP and contributors
# For license information, please see license.txt

"""Demo-site seed data. Not run on migrate unless demo mode is enabled."""

from __future__ import annotations

import frappe

from mcx_helpdesk.constants import DEMO_AGENTS, TEAMS
from mcx_helpdesk.setup.install import ensure_agent, ensure_team, ensure_user


def is_demo_mode_enabled() -> bool:
	"""Demo seed runs on install by default; disable via site_config.json."""
	return bool(frappe.local.conf.get("mcx_helpdesk_demo_mode", True))


def setup_demo_site():
	"""Seed demo users, departments, email, and HD Settings (install / demo sites only)."""
	if not is_demo_mode_enabled():
		return

	setup_demo_agents_and_teams()


def setup_demo_agents_and_teams():
	team_users: dict[str, list[str]] = {team: [] for team in TEAMS}

	for agent in DEMO_AGENTS:
		ensure_user(agent["email"], agent["full_name"])
		ensure_agent(agent["email"], agent["full_name"])
		team = agent["team"]
		if team in team_users:
			team_users[team].append(agent["email"])

	for team in TEAMS:
		users = team_users.get(team, [])
		if users:
			ensure_team(team, users)
		elif frappe.db.exists("HD Team", team):
			frappe.db.set_value("HD Team", team, "disabled", 1)
