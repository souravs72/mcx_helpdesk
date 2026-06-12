# Copyright (c) 2026, Ascra Technologies LLP and contributors
# For license information, please see license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from mcx_helpdesk.mcx_helpdesk.ticket_classifier import TAG_RE, _clean_subject, _tag_source_text, classify_ticket


class TestTicketClassifier(FrappeTestCase):
	def test_subject_tag_parsing(self):
		subject = "[TEAM:IT][TYPE:Portal Access][SUB:Password Reset] Unable to login"
		tags = TAG_RE.findall(subject)
		self.assertEqual(len(tags), 3)
		self.assertEqual(tags[0][0].upper(), "TEAM")
		self.assertEqual(tags[0][1], "IT")

	def test_clean_subject_strips_tags(self):
		subject = "[DEPT:IT][TYPE:Portal Access] Login failed"
		cleaned = _clean_subject(subject, subject)
		self.assertNotIn("[", cleaned)
		self.assertIn("Login failed", cleaned)

	def test_body_first_line_tags(self):
		subject = "Help needed"
		description = "[DEPT:IT][TYPE:Portal Access][SUB:Login Issue]\n\nPlease help with login."
		tag_source = _tag_source_text(subject, description)
		self.assertIn("DEPT:IT", tag_source.upper())

	def test_classify_ticket_from_tags(self):
		if not frappe.db.exists("HD Ticket Type", "IT - Portal Access"):
			self.skipTest("MCX issue types not installed")

		doc = frappe.get_doc(
			{
				"doctype": "HD Ticket",
				"subject": "[TEAM:IT][TYPE:Portal Access][SUB:Password Reset] Reset request",
				"description": "Please reset my password",
				"raised_by": "test@example.com",
			}
		)
		classify_ticket(doc)
		self.assertEqual(doc.agent_group, "IT")
		self.assertEqual(doc.ticket_type, "IT - Portal Access")
		self.assertEqual(doc.subject, "Reset request")

	def test_classify_ticket_keyword_fallback(self):
		if not frappe.db.exists("HD Ticket Type", "IT - Portal Access"):
			self.skipTest("MCX issue types not installed")

		doc = frappe.get_doc(
			{
				"doctype": "HD Ticket",
				"subject": "Unable to login to portal",
				"description": "password not working",
				"raised_by": "test@example.com",
			}
		)
		classify_ticket(doc)
		self.assertEqual(doc.agent_group, "IT")
		self.assertEqual(doc.ticket_type, "IT - Portal Access")
