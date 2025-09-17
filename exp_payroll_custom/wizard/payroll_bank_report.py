# -*- coding:utf-8 -*-

from datetime import date, datetime
from dateutil.relativedelta import relativedelta
from odoo import models, fields, api, _
from odoo.tools import pytz
import datetime
import random

class BankPayslipReport(models.TransientModel):
    _name = 'payroll.bank.wiz'
    _description = "Bank Payslips Report"

    date_from = fields.Date(string='Date From',required=True,
                            default=lambda self: date(date.today().year, date.today().month, 1))
    date_to = fields.Date(string='Date To', required=True,
                          default=lambda self: date(date.today().year, date.today().month, 1)+relativedelta(months=1,days=-1))
    pay_date = fields.Date(
        string='Pay Date',
        required=False)
    salary_type= fields.Char(
        string='', 
        required=False)

    bank_ids = fields.Many2many('res.bank', string='Banks',required=True)
    salary_ids = fields.Many2many('hr.payroll.structure', 'hrpayroll_rel', 'salary_id', 'colum2_id',string='Salary Structures')
    level_ids = fields.Many2many('hr.payroll.structure','hrpayroll_rel_str', 'col1', 'col2', string='Salary Levels')
    group_ids = fields.Many2many('hr.payroll.structure','hrpayroll_rel3', 'col11', 'colid2', string='Salary Degrees')
    degree_ids = fields.Many2many('hr.payroll.structure','hrpayroll_rel4', 'colid1', 'col22' ,string='Salary Basice')
    company_id = fields.Many2one('res.company', string="Company", default=lambda self:self.env.company.id)
    employee_ids = fields.Many2many('hr.employee', string='Employees')
    no_details = fields.Boolean('No Details' ,default=False)
    report_type = fields.Selection(
        [('salary', 'Salary'),
         ('overtime', 'Overtime'),
         ('mission', 'Mission'),
         ('training', 'Training'),
         ('allowance', 'Allowance'),
         ],default='salary', string='Report Type')
    entry_type = fields.Selection(
        [('all', 'ALL'),
         ('posted', 'Post'),
         ('unposted', 'Un Post'),
         ], default='all', string='Entry Type')
    bank_type = fields.Selection(
        [('rajhi', 'Al-Rajhi Bank'),
         ('alahli', 'Al-Ahli Bank'),
         ('riyadh', 'Al-Riyadh Bank'),
         ], default='rajhi', string='Select Bank')

    @api.onchange('date_from')
    def onchange_date_from(self):
        if self.date_from :
            self.date_to = fields.Date.from_string(self.date_from)+relativedelta(months=+1, day=1, days=-1)



    def print_pdf_report(self):
        self.ensure_one()
        [data] = self.read()
        date_from = self.date_from
        date_to = self.date_to
        employees = self.env['hr.employee'].search([('id', 'in', self.employee_ids.ids)])
        banks = self.env['res.bank'].search([('id', 'in', self.bank_ids.ids)])
        salary = self.env['hr.payroll.structure'].search([('id', 'in', self.salary_ids.ids)])
        no_details =self.no_details
        report_type = self.report_type
        entry_type = self.entry_type
        bank_type = self.bank_type
        company_id = self.env['res.company'].search([('id', '=', self.company_id.id)])





        datas = {
            'employees': employees.ids,
            'banks': banks.ids,
            'salary': salary.ids,
            'form': data,
            'date_from': date_from,
            'date_to': date_to,
            'no_details': no_details,
            'report_type': report_type,
            'entry_type': entry_type,
            'bank_type': bank_type,
            'company_id': company_id,
        }

        return self.env.ref('exp_payroll_custom.bank_payslip_report').report_action(self, data=datas)



    def print_report(self):
        [data] = self.read()
        date_from = self.date_from
        date_to = self.date_to
        no_details=self.no_details
        report_type=self.report_type
        entry_type=self.entry_type
        bank_type=self.bank_type
        employees = self.env['hr.employee'].search([('id', 'in', self.employee_ids.ids)])
        banks = self.env['res.bank'].search([('id', 'in', self.bank_ids.ids)])
        salary = self.env['hr.payroll.structure'].search([('id', 'in', self.salary_ids.ids)])
        company_id = self.env['res.company'].search([('id', '=', self.company_id.id)])


        datas = {
            'employees': employees.ids,
            'banks': banks.ids,
            'salary': salary.ids,
            'form': data,
            'date_from': date_from,
            'date_to': date_to,
            'no_details': no_details,
            'report_type': report_type,
            'entry_type': entry_type,
            'bank_type': bank_type,
            'company_id': company_id.id,
        }

        return self.env.ref('exp_payroll_custom.report_payroll_bank_xlsx').report_action(self,data=datas)

    def print_report_text(self):
        self.ensure_one()
        [data] = self.read()
        date_from = self.date_from.strftime("%B")
        date_from = self.date_from
        date_to = self.date_to
        pay_slip =  self.date_from.strftime("%B %Y")
        employees = self.env['hr.employee'].search([('id', 'in', self.employee_ids.ids)])
        banks = self.env['res.bank'].search([('id', 'in', self.bank_ids.ids)])
        salary = self.env['hr.payroll.structure'].search([('id', 'in', self.salary_ids.ids)])
        no_details = self.no_details
        report_type = self.report_type
        entry_type = self.entry_type
        bank_type = self.bank_type
        company_id = self.env['res.company'].search([('id', '=', self.company_id.id)])
        company_hr_no = self.env['res.company'].search([('id', '=', self.company_id.id)]).company_hr_no
        phone = self.env['res.company'].search([('id', '=', self.company_id.id)]).phone
        company_pay_no = self.env['res.company'].search([('id', '=', self.company_id.id)]).company_pay_no
        company_registry = self.env['res.company'].search([('id', '=', self.company_id.id)]).company_registry
        datestamp =  datetime.datetime.now().strftime("%Y/%m/%d")
        timestamp =  datetime.datetime.now().strftime("%H:%M:%S")
        currency = self.env['res.company'].search([('id', '=', self.company_id.id)]).currency_id.name
        if self.pay_date:
           pay_date = self.pay_date
        else:
           pay_date = self.date_to
        if report_type == 'salary':
            self.salary_type = 'S'
        elif report_type=='overtime':
            self.salary_type = 'O'
        else:
            self.salary_type='B'
        salary_type = self.salary_type
        ## Ranom vlaues in report
        length_of_string = 5
        length_of_string2 = 4
        sample = "ABCDEFGHIJKLMNOPQURSTYWXZ0123456789"
        generated_string1 = ''.join(random.choice(sample) for _ in range(length_of_string))
        generated_string2 = ''.join(random.choice(sample) for _ in range(length_of_string2))
        random_char = str(generated_string1)
        random_char2 = str(generated_string2)

        datas = {
            'employees': employees.ids,
            'banks': banks.ids,
            'salary': salary.ids,
            'form': data,
            'date_from':date_from,
            'date_to': date_to,
            'no_details': no_details,
            'report_type': report_type,
            'entry_type': entry_type,
            'bank_type': bank_type,
            'company_id': company_id.english_name,
            'timestamp': timestamp,
            'datestamp': datestamp,
            'currency': currency,
            'pay_date': pay_date,
            'salary_type': salary_type,
            'company_hr_no': company_hr_no,
            'phone': phone,
            'company_pay_no': company_pay_no,
            'company_registry': company_registry,
            'pay_slip': pay_slip,
            'random_char': random_char,
            'random_char2': random_char2,

        }
        return self.env.ref('exp_payroll_custom.payroll_bank_wiz_report_docx').report_action(self, data=datas)



