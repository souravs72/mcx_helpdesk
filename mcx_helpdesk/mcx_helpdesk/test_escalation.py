# Copyright (c) 2026, Ascra Technologies LLP and contributors
# For license information, please see license.txt

import frappe
from frappe.tests.utils import FrappeTestCase


class TestEscalation(FrappeTestCase):
	def test_bump_priority(self):
		from mcx_helpdesk.mcx_helpdesk.escalation import _bump_priority

		self.assertEqual(_bump_priority("Medium"), "High")
		self.assertEqual(_bump_priority("Urgent"), "Urgent")
		self.assertEqual(_bump_priority(None), "High")

	def test_escalation_target_fallback(self):
		from mcx_helpdesk.mcx_helpdesk.escalation import _get_escalation_target

		target = _get_escalation_target("IT", 1)
		self.assertIsNotNone(target)
		self.assertIn("email", target)

	def test_escalation_rules_exist_after_sync(self):
		from mcx_helpdesk.setup.sync import sync_mcx_helpdesk

		sync_mcx_helpdesk()
		rules = frappe.get_all("HD Escalation Rule", filters={"is_enabled": 1, "team": "IT"})
		self.assertTrue(rules)
