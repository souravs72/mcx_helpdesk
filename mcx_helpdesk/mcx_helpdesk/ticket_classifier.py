# Copyright (c) 2026, Ascra Technologies LLP and contributors
# For license information, please see license.txt

"""Email/tag keyword classifier — rules loaded from MCX Classification Rule (desk)."""

from __future__ import annotations

import re
from email.utils import parseaddr

import frappe
from frappe.desk.form.assign_to import add as assign

from mcx_helpdesk.mcx_helpdesk.classification_rules import match_customer_rule, match_ticket_routing_rule
from mcx_helpdesk.setup.escalation import _fallback_team_agent_email

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

	if not _has_classification_tags(doc) and _apply_ai_classification(doc):
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
		rule = match_ticket_routing_rule(text)
		if rule:
			issue_type = issue_type or rule.get("issue_type")
			team = team or rule.get("department")
			sub_issue = sub_issue or rule.get("sub_issue_type")
			if rule.get("set_priority"):
				doc.flags.mcx_rule_priority = rule["set_priority"]

	if issue_type and not team:
		team = _default_department_for_issue_type(issue_type)

	if team and not issue_type:
		issue_type = _first_issue_type_for_department(team)

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
		default_agent = _fallback_team_agent_email(team)
		if default_agent:
			doc.flags.mcx_assignee = default_agent

	if doc.ticket_type:
		doc.priority = (
			doc.flags.get("mcx_rule_priority")
			or _priority_for_issue_type(doc.ticket_type)
			or doc.priority
		)

	if TAG_RE.search(tag_source):
		doc.subject = _clean_subject(subject, tag_source)


def apply_classified_assignee(doc, _method=None):
	"""Assign agent after insert (assignment requires a saved ticket)."""
	assignee = doc.flags.get("mcx_assignee")
	if assignee and frappe.db.exists("HD Agent", assignee) and not _has_open_assignment(doc.name):
		assign(
			{
				"assign_to": [assignee],
				"doctype": "HD Ticket",
				"name": doc.name,
				"description": "Assigned from email classification",
			},
			ignore_permissions=True,
		)

	# Base helpdesk skips ack for portal tickets; send an SLA-aware one instead.
	if (
		doc.via_customer_portal
		and doc.raised_by
		and not frappe.flags.initial_sync
		and frappe.db.get_single_value("HD Settings", "send_acknowledgement_email")
	):
		_send_portal_acknowledgement(doc)


def _send_portal_acknowledgement(doc):
	from frappe.utils import format_datetime

	sla_lines = []
	if doc.response_by:
		sla_lines.append(f"<li><strong>First response by:</strong> {format_datetime(doc.response_by)}</li>")
	if doc.resolution_by:
		sla_lines.append(f"<li><strong>Resolution target:</strong> {format_datetime(doc.resolution_by)}</li>")

	sla_block = (
		f"<p>Our service commitments for this ticket:</p><ul>{''.join(sla_lines)}</ul>"
		if sla_lines
		else ""
	)

	message = f"""
<p>Dear Customer,</p>
<p>Thank you for contacting MCX Support. We have received your request and created ticket
<strong>#{frappe.utils.escape_html(doc.name)}</strong>.</p>
<ul>
<li><strong>Subject:</strong> {frappe.utils.escape_html(doc.subject or "")}</li>
</ul>
{sla_block}
<p>Our team will be in touch shortly. You can track your ticket status at any time through the
support portal.</p>
"""
	try:
		frappe.sendmail(
			recipients=[doc.raised_by],
			subject=f"Ticket #{doc.name}: We've received your request",
			message=message,
			reference_doctype="HD Ticket",
			reference_name=doc.name,
			email_headers={"X-Auto-Generated": "mcx-hd-acknowledgement"},
		)
	except Exception:
		frappe.log_error(title="MCX Portal Ack Email Failed", message=frappe.get_traceback())


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
	rule = match_customer_rule(text)
	if not rule or not rule.get("customer"):
		return None
	if frappe.db.exists("HD Customer", rule["customer"]):
		return rule["customer"]
	return None


def _default_department_for_issue_type(issue_type: str) -> str | None:
	return frappe.db.get_value("HD Ticket Type", issue_type, "default_department")


def _first_issue_type_for_department(team: str) -> str | None:
	types = frappe.get_all(
		"HD Ticket Type",
		filters={"default_department": team, "disabled": 0},
		pluck="name",
		limit=1,
		order_by="name asc",
	)
	return types[0] if types else None


def _priority_for_issue_type(issue_type: str) -> str | None:
	return frappe.db.get_value("HD Ticket Type", issue_type, "priority")


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


def _apply_ai_classification(doc) -> bool:
	"""Use AI classifier when enabled. Returns True if fields were set."""
	try:
		from mcx_helpdesk.mcx_helpdesk.ai_assist import classify_with_ai

		result = classify_with_ai(doc)
	except Exception:
		frappe.logger().debug("AI classification skipped", exc_info=True)
		return False

	if not result:
		return False

	if result.get("ticket_type"):
		doc.ticket_type = result["ticket_type"]
	if result.get("agent_group"):
		doc.agent_group = result["agent_group"]
	if result.get("sub_issue_type"):
		resolved_sub = _resolve_sub_issue(result["sub_issue_type"], doc.ticket_type)
		if resolved_sub:
			doc.sub_issue_type = resolved_sub
	if result.get("priority"):
		doc.priority = result["priority"]

	doc.flags.mcx_ai_classified = True
	return bool(result.get("ticket_type") or result.get("agent_group"))
