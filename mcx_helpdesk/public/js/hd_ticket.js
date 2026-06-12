frappe.ui.form.on("HD Ticket", {
	refresh(frm) {
		frm.set_query("sub_issue_type", () => ({
			filters: {
				issue_type: frm.doc.ticket_type || "",
			},
		}));
	},
	ticket_type(frm) {
		if (frm.doc.sub_issue_type) {
			frm.set_value("sub_issue_type", "");
		}
	},
});
