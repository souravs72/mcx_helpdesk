# Copyright (c) 2026, Ascra Technologies LLP and contributors
"""Safe article search when Redis RediSearch (FT.SEARCH) is unavailable."""

from __future__ import annotations

import frappe


@frappe.whitelist()
def search(query: str) -> list:
	try:
		from helpdesk.api.article import search as _search

		return _search(query)
	except Exception:
		return []
