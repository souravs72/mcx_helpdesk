# Copyright (c) 2026, Ascra Technologies LLP and contributors
# For license information, please see license.txt

"""Shared MCX Helpdesk master data and classification rules."""

TEAMS = ["Trading", "Clearing", "IT", "Compliance"]

ISSUE_TYPES = [
	("Trading - Order Entry", "Medium", "Trading"),
	("Trading - Margin Query", "Medium", "Trading"),
	("Clearing - Settlement", "High", "Clearing"),
	("Clearing - Payout", "High", "Clearing"),
	("IT - Portal Access", "High", "IT"),
	("IT - System Downtime", "Urgent", "IT"),
	("Compliance - Reporting", "Medium", "Compliance"),
	("Compliance - KYC", "High", "Compliance"),
]

SUB_ISSUE_TYPES = [
	("Order Rejection", "Trading - Order Entry"),
	("Price Mismatch", "Trading - Margin Query"),
	("Settlement Delay", "Clearing - Settlement"),
	("Payout Pending", "Clearing - Payout"),
	("Login Issue", "IT - Portal Access"),
	("Password Reset", "IT - Portal Access"),
	("System Outage", "IT - System Downtime"),
	("Regulatory Filing", "Compliance - Reporting"),
	("KYC Update", "Compliance - KYC"),
]

SUB_ISSUE_TYPE_NAMES = [row[0] for row in SUB_ISSUE_TYPES]
ISSUE_TYPE_NAMES = [row[0] for row in ISSUE_TYPES]

DEMO_AGENTS = [
	{"email": "souravsingh2609@gmail.com", "full_name": "Sourav Singh", "team": "IT"},
	{"email": "mcx.trading.agent@demo.com", "full_name": "MCX Trading Agent", "team": "Trading"},
	{"email": "mcx.clearing.agent@demo.com", "full_name": "MCX Clearing Agent", "team": "Clearing"},
	{"email": "mcx.compliance.agent@demo.com", "full_name": "MCX Compliance Agent", "team": "Compliance"},
]

LEGACY_TEAMS = ["Billing", "Product Experts"]
