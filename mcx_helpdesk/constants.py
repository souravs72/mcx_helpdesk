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

PRIORITY_LADDER = ["Low", "Medium", "High", "Urgent"]

# Hours before re-escalating to the next level while SLA remains breached.
REESCALATE_AFTER_HOURS = 4

# L1 = department supervisor, L2 = department head; L3 = country head (shared).
ESCALATION_SUPERVISORS = {
	"IT": [
		{"email": "souravsingh2609@gmail.com", "full_name": "IT Supervisor", "level": "L1"},
		{"email": "mcx.it.head@demo.com", "full_name": "IT Department Head", "level": "L2"},
	],
	"Trading": [
		{"email": "mcx.trading.supervisor@demo.com", "full_name": "Trading Supervisor", "level": "L1"},
		{"email": "mcx.trading.head@demo.com", "full_name": "Trading Department Head", "level": "L2"},
	],
	"Clearing": [
		{"email": "mcx.clearing.supervisor@demo.com", "full_name": "Clearing Supervisor", "level": "L1"},
		{"email": "mcx.clearing.head@demo.com", "full_name": "Clearing Department Head", "level": "L2"},
	],
	"Compliance": [
		{"email": "mcx.compliance.supervisor@demo.com", "full_name": "Compliance Supervisor", "level": "L1"},
		{"email": "mcx.compliance.head@demo.com", "full_name": "Compliance Department Head", "level": "L2"},
	],
}

COUNTRY_HEAD = {
	"email": "mcx.country.head@demo.com",
	"full_name": "MCX Country Head",
	"level": "L3",
}
