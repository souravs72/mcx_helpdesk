# Copyright (c) 2026, Ascra Technologies LLP and contributors
# For license information, please see license.txt

"""AI-assisted ticket classification, reply suggestions, and summaries."""

from __future__ import annotations

import json
import re

import frappe
import requests
from frappe.utils import strip_html


def _ai_master_lists() -> tuple[list[str], list[str], list[str]]:
	"""Load classifier options from desk masters (not hardcoded constants)."""
	teams = frappe.get_all("HD Team", filters={"disabled": 0}, pluck="name", order_by="name asc")
	issue_types = frappe.get_all("HD Ticket Type", pluck="name", order_by="name asc")
	sub_issues = frappe.get_all("HD Sub Issue Type", pluck="sub_issue_name", order_by="name asc")
	return teams, issue_types, sub_issues


def is_ai_enabled(feature: str | None = None) -> bool:
	if not frappe.db.exists("DocType", "MCX AI Settings"):
		return False
	settings = frappe.get_single("MCX AI Settings")
	if not settings.enabled or not settings.get_password("api_key"):
		return False
	if not feature:
		return True
	return bool(settings.get(feature))


def classify_with_ai(doc) -> dict | None:
	"""Return {agent_group, ticket_type, sub_issue_type, priority} or None."""
	if not is_ai_enabled("classify_on_create"):
		return None

	subject = doc.subject or ""
	description = strip_html(doc.description or "")
	if not subject and not description:
		return None

	teams, issue_types, sub_issues = _ai_master_lists()
	if not teams or not issue_types:
		return None

	prompt = f"""You are an MCX commodity exchange helpdesk classifier.
Given a support ticket, return JSON with exactly these keys:
- department: one of {json.dumps(teams)}
- issue_type: one of {json.dumps(issue_types)}
- sub_issue_type: one of {json.dumps(sub_issues)}
- priority: one of ["Low", "Medium", "High", "Urgent"]
- confidence: float 0-1

Subject: {subject}
Description: {description[:2000]}
"""
	raw = _chat_completion(prompt, system="Return valid JSON only.")
	if not raw:
		return None

	try:
		data = _parse_json_response(raw)
	except json.JSONDecodeError:
		return None

	if float(data.get("confidence") or 0) < 0.55:
		return None

	return {
		"agent_group": _resolve_department(data.get("department"), teams),
		"ticket_type": data.get("issue_type") if data.get("issue_type") in issue_types else None,
		"sub_issue_type": data.get("sub_issue_type"),
		"priority": data.get("priority"),
	}


def suggest_reply(ticket_name: str) -> dict:
	"""Suggest a reply for agents based on ticket context and KB articles."""
	if not is_ai_enabled("suggest_reply"):
		frappe.throw("AI reply suggestions are not enabled.", frappe.PermissionError)

	doc = frappe.get_doc("HD Ticket", ticket_name)
	thread = _ticket_thread(doc)
	articles = _related_articles(doc)

	prompt = f"""You are an MCX support agent assistant. Draft a professional, empathetic reply.
Use the knowledge base excerpts when relevant. Do not invent policy details.
Return JSON: {{"reply": "...", "articles_used": ["title1"], "confidence": 0.0-1.0}}

Ticket #{doc.name}
Department: {doc.agent_group or "—"}
Issue Type: {doc.ticket_type or "—"}
Sub Issue: {doc.get("sub_issue_type") or "—"}
Priority: {doc.priority or "—"}
Subject: {doc.subject or ""}

Conversation:
{thread[:6000]}

Knowledge base:
{articles[:4000]}
"""
	raw = _chat_completion(prompt, system="Return valid JSON only.")
	if not raw:
		frappe.throw("AI service unavailable. Check MCX AI Settings.")

	try:
		return _parse_json_response(raw)
	except json.JSONDecodeError as exc:
		frappe.throw(f"AI returned an invalid response: {exc}")


def summarize_ticket(ticket_name: str) -> dict:
	if not is_ai_enabled("summarize_ticket"):
		frappe.throw("AI summaries are not enabled.", frappe.PermissionError)

	doc = frappe.get_doc("HD Ticket", ticket_name)
	thread = _ticket_thread(doc)
	prompt = f"""Summarize this support ticket for a supervisor handoff.
Return JSON: {{"summary": "...", "next_steps": ["..."], "sentiment": "positive|neutral|negative"}}

Ticket #{doc.name} — {doc.subject or ""}
Department: {doc.agent_group or "—"}
Status: {doc.status}
SLA: {doc.agreement_status}

{thread[:6000]}
"""
	raw = _chat_completion(prompt, system="Return valid JSON only.")
	if not raw:
		frappe.throw("AI service unavailable. Check MCX AI Settings.")
	try:
		return _parse_json_response(raw)
	except json.JSONDecodeError as exc:
		frappe.throw(f"AI returned an invalid response: {exc}")


def _ticket_thread(doc) -> str:
	parts = [f"Customer: {strip_html(doc.description or '')}"]
	for comm in frappe.get_all(
		"Communication",
		filters={
			"reference_doctype": "HD Ticket",
			"reference_name": doc.name,
			"communication_type": ["in", ["Communication", "Automated Message"]],
		},
		fields=["sender", "content", "creation"],
		order_by="creation asc",
		limit=20,
	):
		sender = comm.sender or "Unknown"
		parts.append(f"{sender}: {strip_html(comm.content or '')}")
	return "\n".join(parts)


def _related_articles(doc) -> str:
	query = " ".join(filter(None, [doc.subject, strip_html(doc.description or ""), doc.ticket_type]))
	if not query.strip():
		return ""
	try:
		from helpdesk.api.article import search as article_search

		results = article_search(query)[:5]
	except Exception:
		return ""

	lines = []
	for article in results:
		title = article.get("title") or article.get("name")
		content = strip_html(article.get("content") or "")[:500]
		lines.append(f"- {title}: {content}")
	return "\n".join(lines)


def _chat_completion(prompt: str, system: str = "") -> str | None:
	settings = frappe.get_single("MCX AI Settings")
	api_key = settings.get_password("api_key")
	if not api_key:
		return None

	base_url = (settings.api_base_url or "https://api.openai.com/v1").rstrip("/")
	url = f"{base_url}/chat/completions"
	messages = []
	if system:
		messages.append({"role": "system", "content": system})
	messages.append({"role": "user", "content": prompt})

	payload = {
		"model": settings.model or "gpt-4o-mini",
		"messages": messages,
		"temperature": float(settings.temperature or 0.2),
		"max_tokens": int(settings.max_tokens or 800),
	}

	try:
		response = requests.post(
			url,
			headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
			json=payload,
			timeout=45,
		)
		response.raise_for_status()
		data = response.json()
		return data["choices"][0]["message"]["content"]
	except Exception:
		frappe.log_error(title="MCX AI Request Failed", message=frappe.get_traceback())
		return None


def _parse_json_response(raw: str) -> dict:
	cleaned = raw.strip()
	if cleaned.startswith("```"):
		cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
		cleaned = re.sub(r"\s*```$", "", cleaned)
	return json.loads(cleaned)


def _resolve_department(value: str | None, teams: list[str] | None = None) -> str | None:
	if not value:
		return None
	candidates = teams or frappe.get_all("HD Team", filters={"disabled": 0}, pluck="name")
	for team in candidates:
		if team.lower() == str(value).lower():
			return team
	return None
