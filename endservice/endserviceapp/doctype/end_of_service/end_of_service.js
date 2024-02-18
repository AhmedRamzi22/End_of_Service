// Copyright (c) 2024, ahmed ramzi and contributors
// For license information, please see license.txt

frappe.ui.form.on('End Of Service', {
	refresh: function(frm) {

		frm.events.waring_message(frm)
		frm.events.set_type_filter(frm)
	
	},
	set_type_filter:function(frm){
		frm.set_query("type", function () {
			return {
			  filters:{"docstatus":1}
			};
		  });
	   
	},
	
	waring_message:function(frm){
		if(!frm.is_new()) {
			frm.set_intro("");
			if (frm.doc.end_of_service_type=="With Reward"  && frm.doc.waring) {
				frm.set_intro(
					`
					 Waring:There are no suitable settings for calculating service efficiency. Please add appropriate settings >> <a href=${frappe.urllib.get_full_url('/app/' + "end-of-service-setting" )}> 
					Setting</a> </b>
					`,
					"yellow"
				  );
			  }}
	}

});
