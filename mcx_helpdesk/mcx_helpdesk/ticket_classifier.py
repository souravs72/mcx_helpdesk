# Copyright (c) 2026, Ascra Technologies LLP and contributors
# For license information, please see license.txt

import re

import frappe

from mcx_helpdesk.constants import ISSUE_TYPES

TICKET_TYPE_TEAM = {row[0]: row[2] for row in ISSUE_TYPES}

KEYWORD_RULES = [
	(["login", "password", "portal access", "unable to login"], "IT - Portal Access", "IT", "Login Issue"),
	(["system down", "outage", "downtime", "not working"], "IT - System Downtime", "IT", "System Outage"),
	(["settlement", "clearing delay"], "Clearing - Settlement", "Clearing", "Settlement Delay"),
	(["payout", "payment pending"], "Clearing - Payout", "Clearing", "Payout Pending"),
	(["order reject", "order entry", "trade reject"], "Trading - Order Entry", "Trading", "Order Rejection"),
	(["margin", "price mismatch"], "Trading - Margin Query", "Trading", "Price Mismatch"),
	(["kyc", "know your customer"], "Compliance - KYC", "Compliance", "KYC Update"),
	(["regulatory", "compliance report", "reporting"], "Compliance - Reporting", "Compliance", "Regulatory Filing"),
]

TAG_RE = re.compile(r"\[(TEAM|DEPT|TYPE|SUB):([^\]]+)\]", re.I)


def classify_ticket(doc, _method=None):
	"""Auto-set Team, Issue Type, and Sub Issue Type from email subject/body."""
	if doc.doctype != "HD Ticket":
		return
	if not doc.get("subject") and not doc.get("description"):
		return

	subject = doc.subject or ""
	text = f"{subject} {frappe.utils.strip_html(doc.description or '')[:1000]}".lower()

	team = None
	issue_type = None
	sub_issue = None

	for tag, value in TAG_RE.findall(subject):
		tag = tag.upper()
		value = value.strip()
		if tag in ("TEAM", "DEPT"):
			team = _resolve_team(value) or team
		elif tag == "TYPE":
			issue_type = _resolve_issue_type(value) or issue_type
		elif tag == "SUB":
			sub_issue = _resolve_sub_issue(value, issue_type) or sub_issue

	if not issue_type or not team or not sub_issue:
		for keywords, rule_issue, rule_team, rule_sub in KEYWORD_RULES:
			if any(word in text for word in keywords):
				issue_type = issue_type or rule_issue
				team = team or rule_team
				sub_issue = sub_issue or rule_sub
				break

	if issue_type and not team:
		team = TICKET_TYPE_TEAM.get(issue_type)

	if team and not issue_type:
		for candidate, mapped_team in TICKET_TYPE_TEAM.items():
			if mapped_team == team:
				issue_type = candidate
				break

	if issue_type:
		doc.ticket_type = issue_type
	if team:
		doc.agent_group = team
	if sub_issue:
		resolved_sub = _resolve_sub_issue(sub_issue, doc.ticket_type)
		if resolved_sub:
			doc.sub_issue_type = resolved_sub

	if TAG_RE.search(subject):
		doc.subject = _clean_subject(subject)


def _resolve_issue_type(value):
	value = (value or "").strip()
	if not value:
		return None
	if frappe.db.exists("HD Ticket Type", value):
		return value
	matches = frappe.get_all(
		"HD Ticket Type",
		filters={"name": ["like", f"%{value}%"]},
		pluck="name",
		limit=1,
	)
	return matches[0] if matches else None


def _resolve_team(value):
	value = (value or "").strip()
	if not value:
		return None
	for team in frappe.get_all("HD Team", pluck="name"):
		if team.lower() == value.lower():
			return team
	return None


def _resolve_sub_issue(value, issue_type=None):
	value = (value or "").strip()
	if not value:
		return None
	if issue_type and frappe.db.exists("HD Sub Issue Type", {"sub_issue_name": value, "issue_type": issue_type}):
		return frappe.db.get_value(
			"HD Sub Issue Type",
			{"sub_issue_name": value, "issue_type": issue_type},
			"name",
		)
	if frappe.db.exists("HD Sub Issue Type", value):
		return value
	matches = frappe.get_all(
		"HD Sub Issue Type",
		filters={"sub_issue_name": ["like", f"%{value}%"]},
		pluck="name",
		limit=1,
	)
	return matches[0] if matches else None


def _clean_subject(subject):
	if not subject:
		return subject
	cleaned = TAG_RE.sub("", subject).strip()
	cleaned = re.sub(r"\s+", " ", cleaned)
	return cleaned or subject
