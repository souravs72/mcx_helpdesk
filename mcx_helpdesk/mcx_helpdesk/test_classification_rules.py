# Copyright (c) 2026, Ascra Technologies LLP and contributors
# For license information, please see license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from mcx_helpdesk.mcx_helpdesk.classification_rules import (
	_parse_keywords,
	match_customer_rule,
	match_ticket_routing_rule,
)


class TestClassificationRules(FrappeTestCase):
	def test_parse_keywords_multiline(self):
		keywords = _parse_keywords("login\nunable to login\nsign in")
		self.assertEqual(keywords, ["login", "unable to login", "sign in"])

	def test_routing_rule_match_after_sync(self):
		from mcx_helpdesk.setup.sync import sync_mcx_helpdesk

		sync_mcx_helpdesk()
		if not frappe.db.exists("DocType", "MCX Classification Rule"):
			self.skipTest("MCX Classification Rule not migrated")

		rule = match_ticket_routing_rule("unable to login to portal")
		self.assertIsNotNone(rule)
		self.assertEqual(rule.get("issue_type"), "IT - Portal Access")

	def test_customer_rule_match_after_sync(self):
		from mcx_helpdesk.setup.sync import sync_mcx_helpdesk

		sync_mcx_helpdesk()
		if not frappe.db.exists("HD Customer", "Alpha Brokers"):
			self.skipTest("Demo customers not seeded")

		rule = match_customer_rule("message from alphabrokers.com team")
		self.assertIsNotNone(rule)
		self.assertEqual(rule.get("customer"), "Alpha Brokers")
