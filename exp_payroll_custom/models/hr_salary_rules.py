# -*- coding: utf-8 -*-

from datetime import datetime

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.exceptions import Warning
from odoo.tools.safe_eval import safe_eval

class HrSalaryRuleAccount(models.Model):
    _name = 'hr.salary.rule.account'
    _description = 'Salary Rule Account Mapping'

    rule_id = fields.Many2one('hr.salary.rule', string="Salary Rule", required=True, ondelete="cascade")
    emp_type_id = fields.Many2one('hr.contract.type', string="Employee Type", required=True)
    credit_account_id = fields.Many2one('account.account', string="Credit Account", required=True)
    debit_account_id = fields.Many2one('account.account', string="Debit Account", required=True)



class HrSalaryRules(models.Model):
    _inherit = 'hr.salary.rule'

    start_date = fields.Date(string='Start Date', default=fields.date.today())
    end_date = fields.Date(string='End Date')
    salary_type = fields.Selection([('fixed', _('Fixed for all')),
                                    ('related_levels', _('Related with Levels')),
                                    ('related_groups', _('Related with Groups')),
                                    ('related_degrees', _('Related with Degrees'))], default="fixed",
                                   string='Type Scale')
    related_qualifications = fields.Boolean(string='Related with qualifications')
    special = fields.Boolean(string='Special')
    company_id = fields.Many2one(comodel_name='res.company', string='Company', required=True,
                                 default=lambda self: self.env.user.company_id)
    discount_absence = fields.Selection([('by_day', _('By Day')),
                                         ('by_hour', _('By Hour')),
                                         ('no_discount', _('No discount'))],
                                        default="no_discount", string='Discount Absence')
    fixed_amount = fields.Integer(string='Fixed Amount')

    # relational fields
    related_benefits_discounts = fields.Many2many(comodel_name='hr.salary.rule',
                                                  relation='salary_rule_benefit_discount_rel',
                                                  column1='rule_id', column2='sub_rule_id',
                                                  string='Related Benefits and Discount')
    salary_amount_ids = fields.One2many('related.salary.amount', 'salary_rule_id')
    rule_credit_account_id = fields.Many2one('account.account')
    rule_debit_account_id = fields.Many2one('account.account')
    rules_type = fields.Selection([('salary', _('Salary Allowance')),
                                   ('house', _('House Allowance')),
                                   ('overtime', _('Overtime Allowance')),
                                   ('mandate', _('Mandate Allowance')),
                                   ('transport', _('Transport Allowance')),
                                   ('termination', _('End Of Services')),
                                   ('insurnce', _('Insurnce Deduction')),
                                   ('other', _('Other'))
                                   ], string='Rules Type')

    account_ids = fields.One2many('hr.salary.rule.account', 'rule_id')
    transfer_by_emp_type = fields.Boolean('Transfer By Employee Type')

    def get_debit_account_id(self, emp_type):
        if not self.transfer_by_emp_type:  return self.rule_debit_account_id.id
        account_mapping = self.sudo().account_ids.filtered(lambda a: a.emp_type_id.id == emp_type)
        return account_mapping[0].debit_account_id.id if account_mapping else False

    def get_credit_account_id(self, emp_type):
        if not self.transfer_by_emp_type:  return self.rule_credit_account_id.id
        account_mapping = self.sudo().account_ids.filtered(lambda a: a.emp_type_id.id == emp_type)
        return account_mapping[0].credit_account_id.id if account_mapping else False

    @api.constrains('rules_type', 'category_id')
    def _check_dates(self):
        for rec in self:
            if rec.category_id.rule_type != 'deduction' and rec.rules_type == 'insurnce':
                raise UserError(_("The Salary Rule is Not Deduction"))

    # Override function compute rule in hr salary rule

    def _compute_rule(self, localdict):
        payslip = localdict.get('payslip')
        contract = localdict.get('contract')
        if self.amount_select == 'percentage':
            total_percent, total = 0, 0
            if self.related_benefits_discounts:
                for line in self.related_benefits_discounts:
                    calc_line = line._compute_rule(localdict)[0]

                    if line.amount_select == 'fix':
                        if contract.advantages:
                            for con in contract.advantages:
                                if line.id == con.benefits_discounts.id:
                                    if payslip:
                                        if con.date_from > payslip.date_from:
                                            total_percent = calc_line
                                        elif con.date_to is not None and str(
                                                con.date_to) >= payslip.date_to or con.date_to is None:
                                            if con.type == 'exception':
                                                if con.amount > calc_line or con.amount == calc_line:
                                                    pass
                                                elif con.amount < calc_line:
                                                    total = calc_line - con.amount
                                            elif con.type == 'customize':
                                                total = con.amount
                                            total_percent += total
                                    else:
                                        if str(con.date_from) < str(datetime.now().date()):
                                            if con.date_to:
                                                if datetime.strptime(str(con.date_to), "%Y-%m-%d").date().month \
                                                        >= datetime.now().date().month or not con.date_to:
                                                    if con.type == 'exception':
                                                        if con.amount > calc_line or con.amount == calc_line:
                                                            pass
                                                        elif con.amount < calc_line:
                                                            total = calc_line - con.amount
                                                    elif con.type == 'customize':
                                                        total = con.amount
                                                    total_percent += total
                                else:
                                    total_percent = calc_line
                        else:
                            total_percent += calc_line

                    elif line.amount_select == 'percentage':
                        if contract.advantages:
                            for con in contract.advantages:
                                if line.id == con.benefits_discounts.id:
                                    if payslip:
                                        if con.date_from > payslip.date_from:
                                            total_percent = calc_line
                                        elif con.date_to is not None and str(
                                                con.date_to) >= payslip.date_to or con.date_to is None:
                                            if con.type == 'exception':
                                                if con.amount > calc_line or con.amount == calc_line:
                                                    pass
                                                elif con.amount < calc_line:
                                                    total = calc_line - con.amount
                                            elif con.type == 'customize':
                                                total = con.amount
                                            total_percent -= calc_line
                                            total_percent += total
                                    else:
                                        if str(con.date_from) < str(datetime.now().date()):
                                            if con.date_to:
                                                if datetime.strptime(str(con.date_to), "%Y-%m-%d").date().month \
                                                        >= datetime.now().date().month or not con.date_to:
                                                    if con.type == 'exception':
                                                        if con.amount > calc_line or con.amount == calc_line:
                                                            pass
                                                        elif con.amount < calc_line:
                                                            total = calc_line - con.amount
                                                    elif con.type == 'customize':
                                                        total = con.amount
                                                    total_percent -= calc_line
                                                    total_percent += total
                                else:
                                    if con.type != 'exception':
                                        total_percent += calc_line
                                        break
                        else:
                            total_percent += calc_line

                    else:
                        if contract.advantages:
                            for con in contract.advantages:
                                if line.id == con.benefits_discounts.id:
                                    if payslip:
                                        if con.date_from > payslip.date_from:
                                            total_percent = calc_line
                                        elif con.date_to is not None and  con.date_to >= payslip.date_to or con.date_to is None:
                                            if con.type == 'exception':
                                                if con.amount > calc_line or con.amount == calc_line:
                                                    pass
                                                elif con.amount < calc_line:
                                                    total = calc_line - con.amount
                                            elif con.type == 'customize':
                                                total = con.amount
                                            total_percent = 0
                                            total_percent += total
                                    else:
                                        if con.date_from < (datetime.now().date()):
                                            if con.date_to:
                                                if datetime.strptime(str(con.date_to), "%Y-%m-%d").date().month \
                                                        >= datetime.now().date().month or not con.date_to:
                                                    if con.type == 'exception':
                                                        if con.amount > calc_line or con.amount == calc_line:
                                                            pass
                                                        elif con.amount < calc_line:
                                                            total = calc_line - con.amount
                                                    elif con.type == 'customize':
                                                        total = con.amount
                                                    total_percent = 0
                                                    total_percent += total
                                            else:
                                                if datetime.strptime(str(con.date_from),
                                                                     "%Y-%m-%d").date().month >= datetime.now().date().month:
                                                    if con.type == 'exception':
                                                        if con.amount > calc_line or con.amount == calc_line:
                                                            pass
                                                        elif con.amount < calc_line:
                                                            total = calc_line - con.amount
                                                    elif con.type == 'customize':
                                                        total = con.amount + calc_line
                                                    total_percent = 0
                                                    total_percent += total

                                else:
                                    if not total_percent:
                                        total_percent = calc_line
                        else:
                            total_percent += calc_line
            if total_percent:
                if self.salary_type == 'fixed':
                    try:
                        return float(total_percent * self.amount_percentage / 100), \
                               float(safe_eval(self.quantity, localdict)), self.amount_percentage
                    except:
                        raise UserError(
                            _('Wrong percentage base or quantity defined for salary rule %s (%s).') % (
                                self.name, self.code))
                elif self.salary_type == 'related_levels':
                    levels_ids = self.salary_amount_ids.filtered(
                        lambda item: item.salary_scale_level.id == contract.salary_level.id)
                    if levels_ids:
                        for l in levels_ids:
                            try:
                                return float(l.salary * total_percent / 100), float(
                                    safe_eval(self.quantity, localdict)), 100.0
                            except:
                                raise UserError(
                                    _('Wrong quantity defined for salary rule %s (%s).') % (
                                        self.name, self.code))
                    else:
                        return 0, 0, 0
                elif self.salary_type == 'related_groups':
                    groups_ids = self.salary_amount_ids.filtered(
                        lambda item: item.salary_scale_group.id == contract.salary_group.id)
                    if groups_ids:
                        for g in groups_ids:
                            try:
                                return float(g.salary * total_percent / 100), float(
                                    safe_eval(self.quantity, localdict)), 100.0
                            except:
                                raise UserError(
                                    _('Wrong quantity defined for salary rule %s (%s).') % (
                                        self.name, self.code))
                    else:
                        return 0, 0, 0
                elif self.salary_type == 'related_degrees':
                    degrees_ids = self.salary_amount_ids.filtered(
                        lambda item: item.salary_scale_degree.id == contract.salary_degree.id)
                    if degrees_ids:
                        for d in degrees_ids:
                            try:
                                return float(d.salary * total_percent / 100), float(
                                    safe_eval(self.quantity, localdict)), 100.0
                            except:
                                raise UserError(
                                    _('Wrong quantity defined for salary rule %s (%s).') % (
                                        self.name, self.code))
                    else:
                        return 0, 0, 0
            else:
                try:
                    return 0, 0, 0
                except:
                    raise Warning(_('There is no total for rule : %s') % self.name)

        elif self.amount_select == 'fix':
            if self.salary_type == 'fixed':
                try:
                    return self.fixed_amount, float(safe_eval(self.quantity, localdict)), 100.0
                except:
                    raise UserError(_('Wrong quantity defined for salary rule %s (%s).') % (self.name, self.code))
            elif self.salary_type == 'related_levels':
                levels_ids = self.salary_amount_ids.filtered(
                    lambda item: item.salary_scale_level.id == contract.salary_level.id)
                if levels_ids:
                    for l in levels_ids:
                        try:
                            return l.salary, float(safe_eval(self.quantity, localdict)), 100.0
                        except:
                            raise UserError(
                                _('Wrong quantity defined for salary rule %s (%s).') % (self.name, self.code))
                else:
                    return 0, 0, 0
            elif self.salary_type == 'related_groups':
                groups_ids = self.salary_amount_ids.filtered(
                    lambda item: item.salary_scale_group.id == contract.salary_group.id)
                if groups_ids:
                    for g in groups_ids:
                        try:
                            return g.salary, float(safe_eval(self.quantity, localdict)), 100.0
                        except:
                            raise UserError(
                                _('Wrong quantity defined for salary rule %s (%s).') % (self.name, self.code))
                else:
                    return 0, 0, 0
            elif self.salary_type == 'related_degrees':
                degrees_ids = self.salary_amount_ids.filtered(
                    lambda item: item.salary_scale_degree.id == contract.salary_degree.id)
                if degrees_ids:
                    for d in degrees_ids:
                        try:
                            return d.salary, float(safe_eval(self.quantity, localdict)), 100.0
                        except:
                            raise UserError(
                                _('Wrong quantity defined for salary rule %s (%s).') % (self.name, self.code))
                else:
                    return 0, 0, 0
            else:
                raise UserError(_('Error, Select Salary type to calculate rule'))

        else:
            try:
                safe_eval(self.amount_python_compute, localdict, mode='exec', nocopy=True)
                return float(localdict['result']), 'result_qty' in localdict and localdict[
                    'result_qty'] or 1.0, 'result_rate' in localdict and localdict['result_rate'] or 100.0
            except:
                raise UserError(_('Wrong python code defined for salary rule %s (%s).') % (self.name, self.code))


class SalaryConfig(models.Model):
    _name = 'related.salary.amount'

    salary_scale = fields.Many2one('hr.payroll.structure')
    salary_scale_level = fields.Many2one('hr.payroll.structure')
    salary_scale_group = fields.Many2one('hr.payroll.structure')
    salary_scale_degree = fields.Many2one('hr.payroll.structure')
    salary = fields.Float(string='Salary / Percentage')

    # relations fields
    salary_rule_id = fields.Many2one(comodel_name='hr.salary.rule')

    # filter salary_level,salary_group,salary_degree

    @api.onchange('salary_scale')
    def onchange_salary_scale(self):
        for item in self:
            if item.salary_scale:
                level_ids = self.env['hr.payroll.structure'].search(
                    [('salary_scale_id', '=', item.salary_scale.id), ('type', '=', 'level')])
                group_ids = self.env['hr.payroll.structure'].search(
                    [('salary_scale_id', '=', item.salary_scale.id), ('type', '=', 'group')])
                degree_ids = self.env['hr.payroll.structure'].search(
                    [('salary_scale_id', '=', item.salary_scale.id), ('type', '=', 'degree')])
                return {'domain': {'salary_scale_level': [('id', 'in', level_ids.ids)],
                                   'salary_scale_group': [('id', 'in', group_ids.ids)],
                                   'salary_scale_degree': [('id', 'in', degree_ids.ids)]}}
            else:
                return {'domain': {'salary_scale_level': [('id', 'in', [])],
                                   'salary_scale_group': [('id', 'in', [])],
                                   'salary_scale_degree': [('id', 'in', [])]}}

    # filter depend on salary_level

    @api.onchange('salary_scale_level')
    def onchange_salary_level(self):
        for item in self:
            if item.salary_scale_level:
                group_ids = self.env['hr.payroll.structure'].search(
                    [('salary_scale_level_id', '=', item.salary_scale_level.id), ('type', '=', 'group')])
                return {'domain': {'salary_scale_group': [('id', 'in', group_ids.ids)],
                                   'salary_scale_degree': [('id', 'in', [])]}}
            else:
                return {'domain': {'salary_scale_group': [('id', 'in', [])],
                                   'salary_scale_degree': [('id', 'in', [])]}}

    # filter depend on salary_group

    @api.onchange('salary_scale_group')
    def onchange_salary_group(self):
        for item in self:
            if item.salary_scale_group:
                degree_ids = self.env['hr.payroll.structure'].search(
                    [('salary_scale_group_id', '=', item.salary_scale_group.id), ('type', '=', 'degree')])
                return {'domain': {'salary_scale_degree': [('id', 'in', degree_ids.ids)]}}
            else:
                return {'domain': {'salary_scale_degree': [('id', 'in', [])]}}


class SalaryRuleCategory(models.Model):
    _inherit = 'hr.salary.rule.category'

    rule_type = fields.Selection(selection=[('allowance', _('Allowance')), ('deduction', _('Deduction')),
                                            ('base', _('Base')), ('gross', _('Gross')),
                                            ('net', _('Net')), ('end_of_service', _('End of Service'))], string='Type')
