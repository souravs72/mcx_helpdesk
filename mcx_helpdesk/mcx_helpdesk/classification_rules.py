# Copyright (c) 2026, Ascra Technologies LLP and contributors
# For license information, please see license.txt

"""Load ticket/customer keyword classification rules from desk (MCX Classification Rule)."""

from __future__ import annotations

import frappe

CACHE_KEY = "mcx_classification_rules"


def clear_classification_rules_cache():
	frappe.cache.delete_value(CACHE_KEY)


def get_classification_rules(rule_type: str | None = None) -> list[dict]:
	rules = frappe.cache.get_value(CACHE_KEY)
	if rules is None:
		rules = _load_rules_from_db()
		frappe.cache.set_value(CACHE_KEY, rules)

	if rule_type:
		return [r for r in rules if r.get("rule_type") == rule_type]
	return rules


def match_ticket_routing_rule(text: str) -> dict | None:
	"""Return first matching Ticket Routing rule for normalized text, or None."""
	normalized = (text or "").lower()
	for rule in get_classification_rules("Ticket Routing"):
		if _matches_keywords(normalized, rule.get("keywords") or []):
			return rule
	return None


def match_customer_rule(text: str) -> dict | None:
	normalized = (text or "").lower()
	for rule in get_classification_rules("Customer Match"):
		if _matches_keywords(normalized, rule.get("keywords") or []):
			return rule
	return None


def _matches_keywords(text: str, keywords: list[str]) -> bool:
	return any(keyword in text for keyword in keywords if keyword)


def _load_rules_from_db() -> list[dict]:
	if not frappe.db.exists("DocType", "MCX Classification Rule"):
		return []

	rows = frappe.get_all(
		"MCX Classification Rule",
		filters={"enabled": 1},
		fields=[
			"name",
			"rule_name",
			"rule_type",
			"priority",
			"keywords",
			"department",
			"issue_type",
			"sub_issue_type",
			"customer",
			"set_priority",
		],
		order_by="priority asc, rule_name asc",
	)

	for row in rows:
		row["keywords"] = _parse_keywords(row.get("keywords"))

	return rows


def _parse_keywords(raw: str | None) -> list[str]:
	if not raw:
		return []
	keywords = []
	for line in raw.splitlines():
		for part in line.split(","):
			keyword = part.strip().lower()
			if keyword:
				keywords.append(keyword)
	return keywords
