## -*- coding: utf-8 -*-
##############################################################################
#
#    LCT, Life Connection Technology
#    Copyright (C) 2019-2020 LCT 
#
##############################################################################
from datetime import date

from dateutil.relativedelta import relativedelta

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError


class PayslipMonthlyReport(models.TransientModel):
    _name = 'payslip.monthly.report'
    _description = "Payslips Monthly Report"

    date_from = fields.Date(string='Date From', required=True,
                            default=lambda self: date(date.today().year, date.today().month, 1))
    date_to = fields.Date(string='Date To', required=True,
                          default=lambda self: date(date.today().year, date.today().month, 1) + relativedelta(months=1,
                                                                                                              days=-1))
    detailed = fields.Boolean('Detail By Employees', default=False)
    listed = fields.Boolean('List By Rules', default=False)
    salary_ids = fields.Many2many('hr.payroll.structure', 'wiz_sal_rel', 'w_id', 'sal_id', string='Salary Structures')
    level_ids = fields.Many2many('hr.payroll.structure', 'wiz_lvl_rel', 'w_id', 'lvl_id', string='Salary Levels')
    group_ids = fields.Many2many('hr.payroll.structure', 'wiz_grp_rel', 'w_id', 'grp_id', string='Salary Groups')
    degree_ids = fields.Many2many('hr.payroll.structure', 'wiz_dgr_rel', 'w_id', 'dgr_id', string='Salary Degrees')
    rule_ids = fields.Many2many('hr.salary.rule', string='Rules')
    allow = fields.Boolean('Allowances')
    deduct = fields.Boolean('Deductions')
    employee_ids = fields.Many2many('hr.employee', string='Employees')
    no_rule = fields.Boolean('No Rules', default=False)

    @api.onchange('date_from')
    def onchange_date_from(self):
        if self.date_from:
            self.date_to = fields.Date.from_string(self.date_from) + relativedelta(months=+1, day=1, days=-1)

    @api.onchange('allow', 'deduct')
    def get_rule(self):
        domain = (self.allow and self.deduct) and [('category_id.rule_type', 'in', ('allowance', 'deduction')), ] or \
                 self.allow and [('category_id.rule_type', '=', 'allowance'), ] or \
                 self.deduct and [('category_id.rule_type', '=', 'deduction'), ] or []
        domain += [('appears_on_payslip', '=', True), ('active', '=', True)]
        return {'domain': {'rule_ids': [('id', 'in', self.env['hr.salary.rule'].search(domain).ids)]}}

    def get_payslip_line(self):
        domain = [('slip_id.date_from', '>=', self.date_from), ('slip_id.date_to', '<=', self.date_to),
                  ('slip_id.state', '!=', 'cancel'), ('appears_on_payslip', '=', True), ]
        if self.rule_ids:
            domain += [('salary_rule_id', 'in', self.rule_ids.ids)]
        if self.allow and self.deduct:
            domain += [('category_id.rule_type', 'in', ('allowance', 'deduction'))]
        elif self.deduct:
            domain += [('salary_rule_id.category_id.rule_type', '=', 'deduction')]
        elif self.allow:
            domain += [('salary_rule_id.category_id.rule_type', '=', 'allowance')]
        if self.employee_ids:
            domain += [('employee_id', 'in', self.employee_ids.ids)]
        if self.salary_ids:
            domain += [('slip_id.struct_id', 'in', self.salary_ids.ids)]
        if self.level_ids:
            domain += [('slip_id.level_id', 'in', self.level_ids.ids)]
        if self.group_ids:
            domain += [('slip_id.group_id', 'in', self.group_ids.ids)]
        if self.degree_ids:
            domain += [('slip_id.degree_id', 'in', self.degree_ids.ids)]
        return self.env['hr.payslip.line'].search(domain)

    def check_data(self):
        landscape = False
        if self.date_from > self.date_to:
            raise UserError(_('Date From must be less than or equal Date To'))
        payslip_lines = self.get_payslip_line()
        if not payslip_lines:
            raise ValidationError(_('Sorry No Data To Be Printed'))
        rule_ids = self.no_rule and [0, ] or self.rule_ids and self.rule_ids.ids or \
                   self.env['hr.salary.rule'].search([('appears_on_payslip', '=', True), ('active', '=', True)]).ids
        rule_ids = list(set(rule_ids) and set([r.id for r in payslip_lines.mapped('salary_rule_id')]))
        datas = {
            'ids': rule_ids,
            'model': 'hr.salary.rule',
            'payslip_line_ids': [pl.id for pl in payslip_lines],
            'form': (self.read()[0]),
            'rule_ids': rule_ids,
        }
        ctx = self.env.context.copy()
        ctx.update({'active_model': 'hr.salary.rule', 'active_ids': rule_ids, })
        if self.detailed and self.listed:
            delist = 'tt'
            emp_ids = self.employee_ids and self.employee_ids.ids or \
                      list(set(r['employee_id'][0] for r in self.env['hr.payslip'].search_read([
                          ('date_from', '>=', self.date_from), ('date_to', '<=', self.date_to),
                          ('state', '!=', 'cancel')], ['employee_id', ])))
            emp_ids = list(set(emp_ids) and set([emp.id for emp in payslip_lines.mapped('employee_id')]))
            datas['ids'] = emp_ids
            datas['model'] = 'hr.employee'
            ctx.update({'active_model': 'hr.employee', 'active_ids': emp_ids, })
            landscape = True
        elif self.detailed and not self.listed:
            delist = 'tf'
        else:
            delist = 'ff'
        datas['delist'] = delist
        return datas, ctx, landscape

    def print_report(self):
        datas, ctx, lndkp = self.check_data()
        return self.env.ref('exp_payroll_custom.act_payslip_monthly_report').with_context(
            ctx, landscape=lndkp).report_action(self, data=datas)

    def print_report_xlsx(self):
        datas, ctx, lndkp = self.check_data()
        return self.env.ref('exp_payroll_custom.payslip_monthly_report_xlsx').with_context(
            ctx).report_action(self, data=datas)
