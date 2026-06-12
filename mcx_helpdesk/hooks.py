app_name = "mcx_helpdesk"
app_title = "MCX Helpdesk"
app_publisher = "Ascra Technologies LLP"
app_description = "MCX Helpdesk customizations for RFP demo (classification and routing)"
app_email = "info@ascra.com"
app_license = "mit"

required_apps = ["helpdesk"]

fixtures = [
	{
		"dt": "Custom Field",
		"filters": [["name", "in", ["HD Ticket-sub_issue_type"]]],
	},
	{
		"dt": "Property Setter",
		"filters": [
			[
				"name",
				"in",
				[
					"HD Ticket-ticket_type-label",
					"HD Ticket-agent_group-label",
					"HD Team-team_name-label",
				],
			]
		],
	},
	{
		"dt": "HD Form Script",
		"filters": [["name", "=", "Field Dependency-ticket_type-sub_issue_type"]],
	},
	{"dt": "HD Ticket Template", "filters": [["name", "=", "Default"]]},
	{"dt": "DocType", "filters": [["name", "=", "HD Sub Issue Type"]]},
	{"dt": "HD Sub Issue Type"},
	{
		"dt": "HD Ticket Type",
		"filters": [
			[
				"name",
				"in",
				[
					"Trading - Order Entry",
					"Trading - Margin Query",
					"Clearing - Settlement",
					"Clearing - Payout",
					"IT - Portal Access",
					"IT - System Downtime",
					"Compliance - Reporting",
					"Compliance - KYC",
				],
			]
		],
	},
	{
		"dt": "HD Team",
		"filters": [["name", "in", ["Trading", "Clearing", "IT", "Compliance"]]],
	},
	{
		"dt": "Translation",
		"filters": [
			[
				"source_text",
				"in",
				[
					"Team",
					"Teams",
					"Team Name",
					"Ticket Type",
					"Tickets by Team",
					"Tickets by Type",
					"No Team",
					"No team data",
					"Tickets will be grouped by team once available.",
					"No ticket type data",
					"Tickets will be categorized by type once created.",
					"Percentage of total tickets by team",
					"Total tickets by team",
					"Percentage of total tickets by type",
					"Total tickets by type",
				],
			]
		],
	},
]

after_install = "mcx_helpdesk.setup.install.after_install"

override_whitelisted_methods = {
	"helpdesk.api.dashboard.get_dashboard_data": "mcx_helpdesk.api.dashboard.get_dashboard_data",
}

doc_events = {
	"HD Ticket": {
		"before_validate": "mcx_helpdesk.mcx_helpdesk.ticket_classifier.classify_ticket",
	}
}

doctype_js = {"HD Ticket": "public/js/hd_ticket.js"}
