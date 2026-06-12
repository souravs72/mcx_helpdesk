# Copyright (c) 2026, Ascra Technologies LLP and contributors
# For license information, please see license.txt

from __future__ import annotations

import json

import frappe

# Helpdesk UI strings → MCX terminology (English site overrides via Translation doctype).
UI_TRANSLATIONS = [
	("Team", "Department"),
	("Teams", "Departments"),
	("Team Name", "Department Name"),
	("Ticket Type", "Issue Type"),
	("Tickets by Team", "Tickets by Department"),
	("Tickets by Type", "Tickets by Issue Type"),
	("No Team", "No Department"),
	("No team data", "No department data"),
	("Tickets will be grouped by team once available.", "Tickets will be grouped by department once available."),
	("No ticket type data", "No issue type data"),
	("Tickets will be categorized by type once created.", "Tickets will be categorized by issue type once created."),
	("Percentage of total tickets by team", "Percentage of total tickets by department"),
	("Total tickets by team", "Total tickets by department"),
	("Percentage of total tickets by type", "Percentage of total tickets by issue type"),
	("Total tickets by type", "Total tickets by issue type"),
]


def ensure_ui_translations(language: str | None = None):
	language = language or frappe.db.get_single_value("System Settings", "language") or "en"
	for source_text, translated_text in UI_TRANSLATIONS:
		name = frappe.db.exists(
			"Translation", {"language": language, "source_text": source_text}
		)
		if name:
			frappe.db.set_value("Translation", name, "translated_text", translated_text)
			continue
		frappe.get_doc(
			{
				"doctype": "Translation",
				"language": language,
				"source_text": source_text,
				"translated_text": translated_text,
			}
		).insert(ignore_permissions=True)


def ensure_hd_view_column_labels():
	"""Rename Team/Type columns on ticket list views (Helpdesk desk)."""
	for view_name in frappe.get_all("HD View", filters={"dt": "HD Ticket"}, pluck="name"):
		doc = frappe.get_doc("HD View", view_name)
		changed = False

		if doc.columns:
			columns = json.loads(doc.columns)
			if _relabel_view_columns(columns):
				doc.columns = json.dumps(columns)
				changed = True

		if doc.rows:
			rows = json.loads(doc.rows) if isinstance(doc.rows, str) else doc.rows
			# rows is a field list — no label change needed
			_ = rows

		if changed:
			doc.save(ignore_permissions=True)


def _relabel_view_columns(columns: list[dict]) -> bool:
	changed = False
	for col in columns:
		key = col.get("key")
		label = col.get("label")
		if key == "agent_group" and label == "Team":
			col["label"] = "Department"
			changed = True
		elif key == "ticket_type" and label in ("Type", "Ticket Type"):
			col["label"] = "Issue Type"
			changed = True
		elif key == "sub_issue_type" and label != "Sub Issue Type":
			col["label"] = "Sub Issue Type"
			changed = True
	return changed


def ensure_dashboard_labels():
	ensure_ui_translations()
	ensure_hd_view_column_labels()
