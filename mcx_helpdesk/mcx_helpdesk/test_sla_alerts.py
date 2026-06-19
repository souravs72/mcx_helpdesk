# Copyright (c) 2026, Ascra Technologies LLP and contributors
# For license information, please see license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from mcx_helpdesk.mcx_helpdesk.sla_alerts import (
	SLA_RISK_CRITICAL,
	SLA_RISK_NONE,
	SLA_RISK_WARNING,
	_risk_level_for_pct,
)
from mcx_helpdesk.mcx_helpdesk.sla_settings import get_sla_alert_settings


class TestSlaAlerts(FrappeTestCase):
	def test_risk_level_thresholds(self):
		settings = {"warning_threshold_pct": 75, "critical_threshold_pct": 90}
		self.assertEqual(_risk_level_for_pct(50, settings), SLA_RISK_NONE)
		self.assertEqual(_risk_level_for_pct(75, settings), SLA_RISK_WARNING)
		self.assertEqual(_risk_level_for_pct(89, settings), SLA_RISK_WARNING)
		self.assertEqual(_risk_level_for_pct(90, settings), SLA_RISK_CRITICAL)
		self.assertEqual(_risk_level_for_pct(100, settings), SLA_RISK_CRITICAL)

	def test_settings_defaults(self):
		settings = get_sla_alert_settings()
		self.assertIn("warning_threshold_pct", settings)
		self.assertIn("critical_threshold_pct", settings)
		self.assertLess(settings["warning_threshold_pct"], settings["critical_threshold_pct"])
