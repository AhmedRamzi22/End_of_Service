# Copyright (c) 2024, ahmed ramzi and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

class EndOfServiceSetting(Document):
		
	def validate(self):
		self.validate_specified_period()

	def validate_specified_period(self):
		for row in self.terms:
			if row.based_on =="Full Period With Specified Period" and row.for_firstyear >= row.acceptable_works_period:
				frappe.throw(_("<b>For First(Year)</b> Can't be greater or equal <b>Acceptable Works Period(Years)</b>"))