# Copyright (c) 2026, Ascra Technologies LLP and contributors
# For license information, please see license.txt

import re

import frappe
from frappe.desk.form.assign_to import add as assign

from mcx_helpdesk.constants import ISSUE_TYPES

TICKET_TYPE_TEAM = {row[0]: row[2] for row in ISSUE_TYPES}

KEYWORD_RULES = [
	(["login", "password", "portal access", "unable to login"], "IT - Portal Access", "IT", "Login Issue"),
	(["system down", "outage", "downtime", "not working"], "IT - System Downtime", "IT", "System Outage"),
	(["payout", "payment pending"], "Clearing - Payout", "Clearing", "Payout Pending"),
	(["settlement", "clearing delay"], "Clearing - Settlement", "Clearing", "Settlement Delay"),
	(["order reject", "order entry", "trade reject"], "Trading - Order Entry", "Trading", "Order Rejection"),
	(["margin", "price mismatch"], "Trading - Margin Query", "Trading", "Price Mismatch"),
	(["kyc", "know your customer"], "Compliance - KYC", "Compliance", "KYC Update"),
	(["regulatory", "compliance report", "reporting"], "Compliance - Reporting", "Compliance", "Regulatory Filing"),
]

# Subject/body tags — aliases in parentheses
TAG_RE = re.compile(
	r"\[(TEAM|DEPT|TYPE|SUB|CUSTOMER|CUST|ASSIGNEE|ASSIGN):([^\]]+)\]",
	re.I,
)


def classify_ticket(doc, _method=None):
	"""Auto-set classification fields from email subject/body tags or keywords."""
	if doc.doctype != "HD Ticket":
		return
	if not doc.get("subject") and not doc.get("description"):
		return

	subject = doc.subject or ""
	tag_source = _tag_source_text(subject, doc.description or "")
	text = f"{subject} {frappe.utils.strip_html(doc.description or '')[:1000]}".lower()

	team = None
	issue_type = None
	sub_issue = None
	customer = None
	assignee = None

	for tag, value in TAG_RE.findall(tag_source):
		tag = tag.upper()
		value = value.strip()
		if tag in ("TEAM", "DEPT"):
			team = _resolve_team(value) or team
		elif tag == "TYPE":
			issue_type = _resolve_issue_type(value) or issue_type
		elif tag == "SUB":
			sub_issue = _resolve_sub_issue(value, issue_type) or sub_issue
		elif tag in ("CUSTOMER", "CUST"):
			customer = _resolve_customer(value) or customer
		elif tag in ("ASSIGNEE", "ASSIGN"):
			assignee = _resolve_assignee(value) or assignee

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
	if customer:
		doc.customer = customer
	if assignee:
		doc.flags.mcx_assignee = assignee

	if TAG_RE.search(tag_source):
		doc.subject = _clean_subject(subject, tag_source)


def apply_classified_assignee(doc, _method=None):
	"""Assign agent after insert (assignment requires a saved ticket)."""
	assignee = doc.flags.get("mcx_assignee")
	if not assignee:
		return
	if not frappe.db.exists("HD Agent", assignee):
		return

	assign(
		{
			"assign_to": [assignee],
			"doctype": "HD Ticket",
			"name": doc.name,
			"description": "Assigned from email classification tags",
		},
		ignore_permissions=True,
	)


def _tag_source_text(subject, description):
	"""Collect tags from subject and the first non-empty line of the email body."""
	parts = [subject or ""]
	if description:
		plain = frappe.utils.strip_html(description)
		for line in plain.splitlines():
			line = line.strip()
			if line:
				parts.append(line)
				break
	return " ".join(parts)


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


def _resolve_customer(value):
	value = (value or "").strip()
	if not value:
		return None
	if frappe.db.exists("HD Customer", value):
		return value
	matches = frappe.get_all(
		"HD Customer",
		filters=[
			["customer_name", "like", f"%{value}%"],
		],
		pluck="name",
		limit=1,
	)
	if matches:
		return matches[0]
	domain_matches = frappe.get_all(
		"HD Customer",
		filters={"domain": value},
		pluck="name",
		limit=1,
	)
	return domain_matches[0] if domain_matches else None


def _resolve_assignee(value):
	value = (value or "").strip()
	if not value:
		return None
	if "@" in value and frappe.db.exists("HD Agent", value):
		return value
	if frappe.db.exists("HD Agent", value):
		return value
	email_matches = frappe.get_all(
		"HD Agent",
		filters={"user": ["like", f"%{value}%"]},
		pluck="user",
		limit=1,
	)
	if email_matches:
		return email_matches[0]
	name_matches = frappe.get_all(
		"HD Agent",
		filters={"agent_name": ["like", f"%{value}%"]},
		pluck="user",
		limit=1,
	)
	return name_matches[0] if name_matches else None


def _clean_subject(subject, tag_source):
	if not subject:
		return subject
	# Only strip tags that appear in subject (keep body tags out of stored subject)
	cleaned = TAG_RE.sub("", subject).strip()
	cleaned = re.sub(r"\s+", " ", cleaned)
	return cleaned or subject
