# Copyright (c) 2026, Ascra Technologies LLP and contributors
# For license information, please see license.txt

"""Temporary regex/tag email classifier — replace with AI agent later."""

from __future__ import annotations

import re
from email.utils import parseaddr

import frappe
from frappe.desk.form.assign_to import add as assign

from mcx_helpdesk.constants import (
	CUSTOMER_KEYWORD_RULES,
	EMAIL_KEYWORD_RULES,
	ISSUE_TYPE_PRIORITY,
	TEAM_DEFAULT_AGENTS,
	TICKET_TYPE_TEAM,
)

# Subject/body tags — aliases in parentheses
TAG_RE = re.compile(
	r"\[(TEAM|DEPT|TYPE|SUB|CUSTOMER|CUST|ASSIGNEE|ASSIGN):([^\]]+)\]",
	re.I,
)

SYSTEM_SENDER_RE = re.compile(
	r"mailer-daemon|mail-daemon|postmaster|noreply|no-reply|donotreply",
	re.I,
)


def classify_ticket(doc, _method=None):
	"""Auto-set sidebar fields from email subject/body tags or keyword rules."""
	if doc.doctype != "HD Ticket":
		return
	if not doc.get("subject") and not doc.get("description"):
		return
	if _is_system_sender(doc.get("raised_by")) and not _has_classification_tags(doc):
		return

	subject = doc.subject or ""
	tag_source = _tag_source_text(subject, doc.description or "")
	text = _classification_text(subject, doc.description or "")

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
		for keywords, rule_issue, rule_team, rule_sub in EMAIL_KEYWORD_RULES:
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

	if not customer:
		customer = (
			_resolve_customer_from_email(doc.get("raised_by"))
			or _resolve_customer_from_keywords(text)
		)
	if customer:
		doc.customer = customer

	if assignee:
		doc.flags.mcx_assignee = assignee
	elif team and not doc.flags.get("mcx_assignee"):
		default_agent = TEAM_DEFAULT_AGENTS.get(team)
		if default_agent and frappe.db.exists("HD Agent", default_agent):
			doc.flags.mcx_assignee = default_agent

	if doc.ticket_type:
		doc.priority = ISSUE_TYPE_PRIORITY.get(doc.ticket_type) or doc.priority

	if TAG_RE.search(tag_source):
		doc.subject = _clean_subject(subject, tag_source)


def apply_classified_assignee(doc, _method=None):
	"""Assign agent after insert (assignment requires a saved ticket)."""
	assignee = doc.flags.get("mcx_assignee")
	if not assignee:
		return
	if not frappe.db.exists("HD Agent", assignee):
		return
	if _has_open_assignment(doc.name):
		return

	assign(
		{
			"assign_to": [assignee],
			"doctype": "HD Ticket",
			"name": doc.name,
			"description": "Assigned from email classification",
		},
		ignore_permissions=True,
	)


def _has_classification_tags(doc) -> bool:
	tag_source = _tag_source_text(doc.subject or "", doc.description or "")
	return bool(TAG_RE.search(tag_source))


def _is_system_sender(raised_by: str | None) -> bool:
	if not raised_by:
		return False
	email = parseaddr(raised_by)[1] or raised_by
	return bool(SYSTEM_SENDER_RE.search(email))


def _classification_text(subject: str, description: str) -> str:
	plain = frappe.utils.strip_html(description or "")
	return f"{subject} {plain}".lower()


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


def _resolve_customer_from_email(raised_by: str | None) -> str | None:
	if not raised_by:
		return None
	email = parseaddr(raised_by)[1] or raised_by
	if "@" not in email:
		return None
	domain = email.split("@", 1)[1].lower()
	if not domain or SYSTEM_SENDER_RE.search(domain):
		return None

	customer = frappe.db.get_value("HD Customer", {"domain": domain}, "name")
	if customer:
		return customer

	contact = frappe.db.get_value("Contact", {"email_id": email}, "name")
	if contact:
		from helpdesk.utils import get_customer

		linked = get_customer(contact)
		if len(linked) == 1:
			return linked[0]

	return _resolve_customer(domain.split(".")[0])


def _resolve_customer_from_keywords(text: str) -> str | None:
	for keywords, customer_name in CUSTOMER_KEYWORD_RULES:
		if any(word in text for word in keywords):
			resolved = _resolve_customer(customer_name)
			if resolved:
				return resolved
	return None


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


def _has_open_assignment(ticket_name: str) -> bool:
	return bool(
		frappe.get_all(
			"ToDo",
			filters={
				"reference_type": "HD Ticket",
				"reference_name": ticket_name,
				"status": "Open",
			},
			limit=1,
		)
	)


def _clean_subject(subject, tag_source):
	if not subject:
		return subject
	cleaned = TAG_RE.sub("", subject).strip()
	cleaned = re.sub(r"\s+", " ", cleaned)
	return cleaned or subject
