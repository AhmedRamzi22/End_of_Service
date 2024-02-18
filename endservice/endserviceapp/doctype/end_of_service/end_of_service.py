# Copyright (c) 2024, ahmed ramzi and contributors
# For license information, please see license.txt

import frappe
from datetime import datetime
from frappe import _
from frappe.query_builder import Order
from frappe.model.document import Document
from hrms.payroll.doctype.salary_structure.test_salary_structure import (
    make_salary_slip,
    make_salary_structure,
)
from frappe.utils import (
    add_days,
    cint,
    cstr,
    date_diff,
    flt,
    formatdate,
    get_first_day,
    getdate,
    money_in_words,
    rounded,
)
from datetime import date



class EndOfService(Document):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.whitelisted_globals = {
            "int": int,
            "float": float,
            "long": int,
            "round": round,
            "date": date,
            "getdate": getdate,
        }

    def validate(self):
        self.calc_work_period()
        if self.end_of_service_type=="With Reward":
            setting_row= self.get_applicable_type()
            self.get_employee_component()
            self.calc_end_of_service(setting_row)
        
    def calc_work_period(self):
        if self.date_of_joining:
            current_date = datetime.now()
            date_of_joining = datetime.strptime(str(self.date_of_joining), '%Y-%m-%d')
            period = current_date - date_of_joining
            years = period.days // 365
            months = (period.days % 365) // 30
            days = (period.days % 365) % 30

            self.work_period=f"Years: {years}, Months: {months}, Days: {days}"
            self.work_years=(years * 12 + months)/12
    
    def get_employee_component(self):
        salary_structure=self.get_employee_salary_structure()
        salay_slip=make_salary_slip(salary_structure, employee=self.employee, posting_date=self.posting_date)
        
        total_salary=0
        self.end_of_service_component=[]
        
        earnings_salary=self.add_earnings_component(salay_slip.earnings)
        deductions_salary=self.add_deductions_component(salay_slip.deductions)
        total_salary+=earnings_salary
        total_salary-=deductions_salary
        self.salary=total_salary
    
        
    def add_earnings_component(self,earnings):
        amount=0
        for component in earnings:

            if frappe.db.get_value("Salary Component",component.salary_component,"custom_end_of_service_included"):
                self.append("end_of_service_component",{
                    "salary_component":component.salary_component,
                    "salary_component_type":"Earning",
                    "amount":component.amount
                })
                amount+=component.amount
        return 	amount	
    
    def add_deductions_component(self,deductions):
        amount=0
        for component in deductions:

            if frappe.db.get_value("Salary Component",component.salary_component,"custom_end_of_service_included"):
                self.append("end_of_service_component",{
                    "salary_component":component.salary_component,
                    "salary_component_type":"Deductions",
                    "amount":component.amount
                })
                amount+=component.amount
        return 	amount	
    
    def get_employee_salary_structure(self):	
        ss = frappe.qb.DocType("Salary Structure")
        ssa = frappe.qb.DocType("Salary Structure Assignment")

        query = (
            frappe.qb.from_(ssa)
            .join(ss)
            .on(ssa.salary_structure == ss.name)
            .select(ssa.salary_structure)
            .where(
                (ssa.docstatus == 1)
                & (ss.docstatus == 1)
                & (ss.is_active == "Yes")
                & (ssa.employee == self.employee)
                & (
                    (ssa.from_date <= self.posting_date)
                    | (ssa.from_date <= self.posting_date)
                    | (ssa.from_date <= self.date_of_joining)
                )
            )
            .orderby(ssa.from_date, order=Order.desc)
            .limit(1)
        )


        st_name = query.run()

        if st_name:
            
            salary_structure= st_name[0][0]
            return salary_structure

        else:
            st_name = None
            frappe.msgprint(
                _("No active or default Salary Structure found for employee {0} for the given dates").format(
                    self.employee
                ),
                title=_("Salary Structure Missing"),
            ) 

    def get_applicable_type(self):

        if self.contract_type:
            setting_rows=frappe.db.get_all("End Of Service Setting Terms",filters={"parent":self.type,"acceptable_works_period":["<=",self.work_years],"docstatus":1,"contract_type":self.contract_type},order_by="acceptable_works_period",fields=["*"])
            
            if len(setting_rows):
                self.waring=0
                return setting_rows[-1]
            
            self.waring=1
            self.end_of_service_amount=0
        
    def calc_end_of_service(self,row):
        if row:
            data=self.as_dict()

            amount=self.calc_formula_amount(row,data)
            self.end_of_service_amount=amount
           
    def calc_formula_amount(self,row,data):
        total_amount=0

        if row["based_on"]=="Full Period":
            work_years=self.work_years
            amount=self.eval_condition_and_formula(row, data,work_years,"full_period_formula")
            return amount
        
        if row["based_on"]=="Full Period With Specified Period":
            
            amount=self.eval_condition_and_formula(row, data,row["for_firstyear"],"specified_period_formula")
           
            total_amount+=amount

            amount=self.eval_condition_and_formula(row, data,(self.work_years-row["for_firstyear"]),"full_period_formula")
           
            total_amount+=amount


        return total_amount
    
    def eval_condition_and_formula(self, row, data,work_years,field):
        try:
            formula = row[field].strip().replace("\n", " ") if row[field] else None
            if formula:
                salary = data.get('salary', 0)
                work_years = work_years
              
                
                # Replace placeholders with actual values
                formula = formula.replace('salary', str(salary)).replace('work_years', str(work_years))
                
                amount = frappe.safe_eval(formula, self.whitelisted_globals, data)
                

                if amount:
                    

                    return amount

        except NameError as err:
            frappe.throw(_("Name error: {0}").format(err))
        except SyntaxError as err:
            frappe.throw(_("Syntax error: {0}").format(err))
        except Exception as err:
            frappe.throw(_("Error in formula: {0}").format(err))



