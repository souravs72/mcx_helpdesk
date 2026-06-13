# Copyright (c) 2026, Ascra Technologies LLP and contributors
# For license information, please see license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from mcx_helpdesk.mcx_helpdesk.ticket_classifier import (
	TAG_RE,
	_clean_subject,
	_resolve_customer_from_email,
	_tag_source_text,
	classify_ticket,
)


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
		self.assertEqual(doc.priority, "High")
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
		self.assertEqual(doc.sub_issue_type, "Login Issue")
		self.assertEqual(doc.priority, "High")

	def test_classify_customer_from_sender_domain(self):
		if not frappe.db.exists("HD Customer", "Alpha Brokers"):
			self.skipTest("Demo customers not seeded")

		customer = _resolve_customer_from_email("Priya Sharma <priya@alphabrokers.com>")
		self.assertEqual(customer, "Alpha Brokers")

	def test_classify_trading_order_keywords(self):
		if not frappe.db.exists("HD Ticket Type", "Trading - Order Entry"):
			self.skipTest("MCX issue types not installed")

		doc = frappe.get_doc(
			{
				"doctype": "HD Ticket",
				"subject": "Order rejected for GOLDM contract",
				"description": "Silver Trading Co reports insufficient margin.",
				"raised_by": "rajesh@silvertrading.com",
			}
		)
		classify_ticket(doc)
		self.assertEqual(doc.agent_group, "Trading")
		self.assertEqual(doc.ticket_type, "Trading - Order Entry")
		self.assertEqual(doc.sub_issue_type, "Order Rejection")
		self.assertEqual(doc.customer, "Silver Trading Co")
		self.assertEqual(doc.priority, "Medium")

	def test_skip_mailer_daemon_without_tags(self):
		doc = frappe.get_doc(
			{
				"doctype": "HD Ticket",
				"subject": "Delivery Status Notification (Failure)",
				"description": "Address not found",
				"raised_by": "mailer-daemon@googlemail.com",
			}
		)
		classify_ticket(doc)
		self.assertFalse(doc.ticket_type)
		self.assertFalse(doc.agent_group)
