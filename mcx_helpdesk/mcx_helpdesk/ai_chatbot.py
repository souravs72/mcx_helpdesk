# Copyright (c) 2026, Ascra Technologies LLP and contributors
# For license information, please see license.txt

"""Customer FAQ chatbot — grounded in published HD Article knowledge base."""

from __future__ import annotations

import json
import re
from html import unescape as html_unescape

import frappe

from mcx_helpdesk.mcx_helpdesk.ai_assist import _chat_completion, _parse_json_response, is_ai_enabled


def _html_to_text(html: str) -> str:
	"""
	Convert article HTML to clean readable plain text.
	Handles tables (each row on its own line, cells separated by ' | '),
	block elements (headings, paragraphs, list items), and line breaks.
	Plain strip_html concatenates adjacent cells with no separator, making
	table headers unreadable (e.g. 'TermWhat it isExample').
	"""
	if not html:
		return ""

	text = html

	# ── Tables ─────────────────────────────────────────────────────────────
	# Join adjacent cells with ' | '
	text = re.sub(r"</t[dh]>\s*<t[dh][^>]*>", " | ", text, flags=re.IGNORECASE)
	# Each row starts on a new line
	text = re.sub(r"<tr[^>]*>", "\n", text, flags=re.IGNORECASE)
	text = re.sub(r"</tr>", "", text, flags=re.IGNORECASE)
	text = re.sub(r"</table>", "\n", text, flags=re.IGNORECASE)
	# Strip leftover td/th open/close tags
	text = re.sub(r"</?t[dh][^>]*>", "", text, flags=re.IGNORECASE)

	# ── Block elements ──────────────────────────────────────────────────────
	text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
	text = re.sub(r"</(p|div|h[1-6]|blockquote|pre|ul|ol)>", "\n", text, flags=re.IGNORECASE)
	text = re.sub(r"<li[^>]*>", "\n• ", text, flags=re.IGNORECASE)

	# ── Strip script/style content (not just the tags) ─────────────────────
	text = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", text, flags=re.IGNORECASE | re.DOTALL)

	# ── Strip remaining tags ────────────────────────────────────────────────
	text = re.sub(r"<[^>]+>", "", text)

	# ── Decode HTML entities (all named + numeric) ──────────────────────────
	text = html_unescape(text)

	# ── Normalise whitespace ────────────────────────────────────────────────
	text = re.sub(r"[ \t]+", " ", text)          # collapse horizontal whitespace
	text = re.sub(r"\n[ \t]+", "\n", text)        # trim leading spaces after newline
	text = re.sub(r"[ \t]+\n", "\n", text)        # trim trailing spaces before newline
	text = re.sub(r"\n{3,}", "\n\n", text)         # max one blank line between blocks
	return text.strip()

DEFAULT_WELCOME = (
	"Hi! I can help with common questions about MCX support, tickets, portal access, "
	"trading, and settlement. What would you like to know?"
)

FAQ_CATEGORY_PREFIX = "MCX FAQ"


def is_chatbot_enabled() -> bool:
	if not frappe.db.exists("DocType", "MCX AI Settings"):
		return True
	settings = frappe.get_single("MCX AI Settings")
	return bool(settings.get("enable_customer_chatbot"))


def use_ai_for_chatbot() -> bool:
	if not is_chatbot_enabled():
		return False
	if not is_ai_enabled():
		return False
	settings = frappe.get_single("MCX AI Settings")
	return bool(settings.get("chatbot_use_ai"))


def get_chatbot_config() -> dict:
	welcome = DEFAULT_WELCOME
	ai_mode = False
	if frappe.db.exists("DocType", "MCX AI Settings"):
		settings = frappe.get_single("MCX AI Settings")
		welcome = settings.get("chatbot_welcome_message") or DEFAULT_WELCOME
		ai_mode = use_ai_for_chatbot()

	return {
		"enabled": is_chatbot_enabled(),
		"ai_mode": ai_mode,
		"welcome_message": welcome,
		"suggested_questions": get_suggested_questions(),
	}


def get_suggested_questions(limit: int = 6) -> list[str]:
	if not frappe.db.exists("DocType", "HD Article"):
		return []

	categories = _faq_category_names()
	if not categories:
		return []

	return frappe.get_all(
		"HD Article",
		filters={"status": "Published", "category": ["in", categories]},
		fields=["title"],
		order_by="modified desc",
		limit=limit,
		pluck="title",
	)


def answer_faq_question(message: str, history: list | None = None) -> dict:
	if not is_chatbot_enabled():
		frappe.throw("The FAQ chatbot is not enabled.", frappe.PermissionError)

	message = (message or "").strip()
	if not message:
		frappe.throw("Please enter a question.")

	articles = search_faq_articles(message, limit=5)
	if use_ai_for_chatbot():
		return _answer_with_ai(message, articles, history or [])

	return _answer_from_articles(message, articles)


def search_faq_articles(query: str, limit: int = 5) -> list[dict]:
	query = (query or "").strip()
	if not query:
		return []

	results = _search_via_helpdesk(query, limit)
	if results:
		return results[:limit]

	return _search_via_database(query, limit)


def _search_via_helpdesk(query: str, limit: int) -> list[dict]:
	try:
		from helpdesk.api.article import search as article_search

		raw = article_search(query)[: limit * 2]
	except Exception:
		return []

	articles = []
	for item in raw:
		name = item.get("id") or item.get("name")
		if not name:
			continue
		row = frappe.db.get_value(
			"HD Article",
			name,
			["name", "title", "content", "category", "status"],
			as_dict=True,
		)
		if not row or row.status != "Published":
			continue
		articles.append(_article_payload(row))
		if len(articles) >= limit:
			break
	return articles


def _search_via_database(query: str, limit: int) -> list[dict]:
	categories = _faq_category_names()
	filters: dict = {"status": "Published"}
	if categories:
		filters["category"] = ["in", categories]

	rows = frappe.get_all(
		"HD Article",
		filters=filters,
		fields=["name", "title", "content", "category"],
		limit=200,
	)
	scored = [(row, _score_article(row, query)) for row in rows]
	scored = [(row, score) for row, score in scored if score > 0]
	scored.sort(key=lambda item: item[1], reverse=True)
	return [_article_payload(row) for row, _score in scored[:limit]]


def _score_article(row, query: str) -> int:
	q = query.lower()
	title = (row.title or "").lower()
	content = _html_to_text(row.content or "").lower()
	score = 0
	for token in re.findall(r"[a-z0-9]+", q):
		if len(token) < 3:
			continue
		if token in title:
			score += 12
		if token in content:
			score += 3
	# Boost phrase matches in title
	if len(q) >= 4 and q in title:
		score += 25
	return score


def _article_payload(row) -> dict:
	content = _html_to_text(row.content or "")
	return {
		"name": row.name,
		"title": row.title,
		"content": content,
		"category": row.category,
	}


def _faq_category_names() -> list[str]:
	if not frappe.db.exists("DocType", "HD Article Category"):
		return []
	return frappe.get_all(
		"HD Article Category",
		filters={"category_name": ["like", f"{FAQ_CATEGORY_PREFIX}%"]},
		pluck="name",
	)


def _answer_from_articles(message: str, articles: list[dict]) -> dict:
	if not articles:
		return {
			"answer": (
				"I couldn't find a direct answer in the FAQ. "
				"Please raise a support ticket and our team will assist you."
			),
			"sources": [],
			"confidence": 0.0,
			"suggest_ticket": True,
			"ai_mode": False,
		}

	best = articles[0]
	content = best.get("content") or ""
	excerpt = content[:600]
	if len(content) > 600:
		excerpt += "…"

	answer = excerpt
	confidence = min(0.90, 0.50 + (0.1 * len(articles)))
	return {
		"answer": answer,
		"sources": [{"name": a["name"], "title": a["title"]} for a in articles[:3]],
		"confidence": round(confidence, 2),
		"suggest_ticket": confidence < 0.60,
		"ai_mode": False,
	}


def _answer_with_ai(message: str, articles: list[dict], history: list) -> dict:
	context = _format_article_context(articles)
	history_text = _format_history(history)

	prompt = f"""You are an AI customer support assistant for MCX (Multi Commodity Exchange of India).

Your job: Answer customers' questions about their support tickets, trading, clearing & settlement, account management, and MCX portal access — using ONLY the FAQ articles provided.

Rules:
1. Base your answer ONLY on the FAQ articles below. Do not invent policies, fees, timelines, or contact details.
2. If the FAQ articles do not contain enough information to answer the question, say so honestly and set suggest_ticket to true.
3. Format answers clearly: use numbered steps for procedures, short paragraphs for explanations.
4. Be direct and concise — customers want quick answers, not long essays.
5. If the question is about a specific ticket or account, always set suggest_ticket to true (only agents can look up individual records).
6. Go straight to the answer — do NOT restate or echo the customer's question.

Return ONLY valid JSON (no markdown fences, no extra text) with exactly these keys:
{{
  "answer": "<your answer — use \\n for line breaks, numbered steps (1. 2. 3.) where appropriate>",
  "sources": ["<title of FAQ article you used>"],
  "confidence": <float 0.0 to 1.0 — how well the FAQs answer this question>,
  "suggest_ticket": <true if the customer needs agent help, false if FAQ fully answers>
}}

Customer question: {message}

Recent conversation:
{history_text or "None"}

FAQ articles:
{context or "No relevant FAQ articles found."}
"""
	raw = _chat_completion(
		prompt,
		system="You are a helpful MCX helpdesk FAQ assistant. Return valid JSON only.",
	)
	if not raw:
		return _answer_from_articles(message, articles)

	try:
		data = _parse_json_response(raw)
	except json.JSONDecodeError:
		return _answer_from_articles(message, articles)

	source_titles = data.get("sources") or []
	resolved_sources = _resolve_sources(source_titles, articles)

	return {
		"answer": data.get("answer") or "",
		"sources": resolved_sources,
		"confidence": float(data.get("confidence") or 0.5),
		"suggest_ticket": bool(data.get("suggest_ticket")),
		"ai_mode": True,
	}


def _format_article_context(articles: list[dict]) -> str:
	lines = []
	for article in articles:
		body = (article.get("content") or "")[:2500]
		lines.append(f"### {article.get('title')}\n{body}")
	return "\n\n".join(lines)


def _format_history(history: list) -> str:
	lines = []
	for item in history[-6:]:
		role = item.get("role") or "user"
		content = (item.get("content") or "").strip()
		if content:
			lines.append(f"{role}: {content}")
	return "\n".join(lines)


def _resolve_sources(source_titles: list, articles: list[dict]) -> list[dict]:
	title_map = {a["title"].lower(): a for a in articles}
	sources = []
	for title in source_titles:
		match = title_map.get(str(title).lower())
		if match:
			sources.append({"name": match["name"], "title": match["title"]})
	if not sources and articles:
		sources = [{"name": articles[0]["name"], "title": articles[0]["title"]}]
	return sources[:3]
