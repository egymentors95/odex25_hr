# -*- coding: utf-8 -*-

from num2words import num2words
from datetime import datetime, timedelta
from odoo import api, fields, models,_


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    base_salary = fields.Float(compute="compute_base_salary")
    salary_in_words = fields.Char(compute="get_salary_amount")
    payslip_lines = fields.One2many(comodel_name="hr.payslip.line", compute="compute_base_salary")
    employee_dependant = fields.One2many(related='contract_id.employee_dependant',readonly=False, tracking=True)
    employee_type_id = fields.Many2one('hr.contract.type', string="Employee Type", ondelete='cascade', tracking=True)


    @api.depends("base_salary")
    def get_salary_amount(self):
        for item in self:
            item.salary_in_words = num2words(item.base_salary, lang=self.env.user.lang)

    def compute_base_salary(self):
        for item in self:
            last_day_of_prev_month = datetime.now().date().replace(day=1) - timedelta(days=1)
            start_day_of_prev_month = datetime.now().date().replace(day=1) - timedelta(days=last_day_of_prev_month.day)
            payroll = item.env["hr.payslip"].search(
                [
                    ("employee_id", "=", item.name),
                    ("date_from", "<=", datetime.now().date()),
                    ("date_to", ">=", datetime.now().date()),
                    ("contract_id", "=", item.contract_id.id),
                ],
                limit=1,
            )
            if not payroll:
                payroll = item.env["hr.payslip"].search(
                    [
                        ("employee_id", "=", item.name),
                        ("date_from", "<=", start_day_of_prev_month),
                        ("date_to", ">=", last_day_of_prev_month),
                        ("contract_id", "=", item.contract_id.id),
                    ],limit=1,
                )

            item.base_salary = payroll.total_allowances
            item.payslip_lines = payroll.allowance_ids.filtered(
                lambda r: r.salary_rule_id.rules_type in ("salary", "house")
            ).sorted(lambda b: b.name)
 
