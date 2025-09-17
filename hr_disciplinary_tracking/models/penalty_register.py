# -*- coding:utf-8 -*-

from odoo import models, fields, api, _, exceptions
from odoo.exceptions import UserError
from odoo.tools.safe_eval import safe_eval


class penalty_register(models.Model):
    _name = 'hr.penalty.register'
    _rec_name = 'employee_id'
    _description = 'Penalty'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    start_date = fields.Date()
    end_date = fields.Date()
    date = fields.Date()
    date_to = fields.Date()
    deduction_date = fields.Date()
    deduction_value = fields.Selection(
        selection=[('of_salary', _('Deduction From Salary')), ('extra_salary', _('Direct Payment Deduction'))],default='of_salary')
    deduction_amount = fields.Float()
    note = fields.Text()
    state = fields.Selection(selection=[
        ('draft', _('Draft')),
        ('officer', _('Wait HR Manager')),
        ('manager', _('Wait Services Manager')),
        ('gm', _('Wait CEO Manager')),
        ('done', _('Approved')),
        ('refuse', _('Refused')),
    ], default='draft', tracking=True)
    penalty_number = fields.Selection(selection=[('first_time', _('First Time')),
                                                 ('second_time', _('Second Time')),
                                                 ('third_time', _('Third Time')),
                                                 ('fourth_time', _('Fourth Time')),
                                                 ('fifth_time', _('Fifth Time'))])
    decision = fields.Text()

    # relational fields

    employee_id = fields.Many2one('hr.employee', 'Employee', default=lambda item: item.get_user_id(),
                                  domain=[('state', '=', 'open')])
    employee_no = fields.Char(related='employee_id.emp_no', readonly=True,string='Employee Number', store=True)
    job_id = fields.Many2one(comodel_name='hr.job', related='employee_id.job_id', readonly=True)
    department_id = fields.Many2one(comodel_name='hr.department', related='employee_id.department_id', readonly=True, store=True)
    penalty_id = fields.Many2one(comodel_name='hr.penalty.ss', tracking=True)
    punishment_id = fields.Many2many(comodel_name='hr.punishment', tracking=True)
    accounting_committee = fields.Many2many(comodel_name='hr.employee')
    deduction_id = fields.Many2one('hr.salary.rule', domain=['|', '|', ('category_id.rule_type', '=', 'deduction'),
                                                             ('category_id.name', '=', 'Deduction'),
                                                             ('special', '=', True)])
    # contract_advantage_ids = fields.Many2many('contract.advantage',string='Deduction Employee')
    termination_id = fields.Many2many('hr.termination')

    advantage_id = fields.Many2one(comodel_name='contract.advantage', string='Deduction Employee')
    last_penalty = fields.Many2one(comodel_name='hr.penalty.register', string='Last Penalty')

    resolution_number = fields.Char(string='Resolution Number')
    company_id = fields.Many2one('res.company', string='Company',default=lambda self: self.env.company)

    def get_user_id(self):
        employee_id = self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)
        if employee_id:
            return employee_id.id
        else:
            return False

    @api.onchange('date')
    def chick_date_day(self):
        for item in self:
            today = fields.Date.from_string(fields.Date.today())
            datee = item.date
            if datee:
                deff_days = (today - fields.Date.from_string(datee)).days
                if deff_days < 0:
                    raise exceptions.Warning(_('You Can Not Add Penalty With Later Date'))

    def name_get(self):
        return [(rec.id, '%s - %s -%s' % (rec.employee_id.name, rec.penalty_id.name, rec.date)) for rec in self]

    def draft(self):
        if self.state == 'done':
            if self.advantage_id:
                self.advantage_id.draft()
                self.advantage_id.unlink()

            if self.termination_id:
                for rec in self.termination_id:
                    if rec.state == 'draft':
                        rec.unlink()
                    else:
                        raise exceptions.Warning(_('You can set to draft when like termination in state not in draft'))

        self.state = 'draft'

    def officer(self):
        for rec in self:
            manager = rec.sudo().employee_id.parent_id
            hr_manager = rec.sudo().employee_id.company_id.hr_manager_id
            if manager:
               if manager.user_id.id == rec.env.uid or hr_manager.user_id.id == rec.env.uid:
                  rec.write({'state': 'officer'})
               else:
                  raise exceptions.Warning(_("Sorry, The Approval For The Direct Manager '%s' Only OR HR Manager!")%(rec.employee_id.parent_id.name))
            else:
                rec.write({'state': 'officer'})

    def manager(self):
        self.state = 'manager'

    def gm(self):
        self.state = 'gm'

    def confirm_state(self):
        self.state = 'confirm'

    def refuse_state(self):
        self.state = 'refuse'

    def done(self):
        termination_move = []
        for item in self:
            if item.deduction_amount > 0.0 and item.employee_id.contract_id and item.deduction_value == 'of_salary':
                contract_move_id = item.env['contract.advantage'].create({
                    'benefits_discounts': item.deduction_id.id,
                    'amount': item.deduction_amount,
                    'date_from': item.start_date,
                    'date_to': item.end_date,
                    'type': 'customize',
                    'employee_id': item.employee_id.id,
                    'contract_advantage_id': item.employee_id.contract_id.id,
                    'penalty_id': True,
                    'out_rule': True,
                    'state': 'confirm',
                    'comments': self.decision
                })
                item.advantage_id = contract_move_id.id

            for punishment_line in item.punishment_id:
                if punishment_line.type == 'termination':
                    termination_move_id = self.env['hr.termination'].create({
                        'employee_id': item.employee_id.id,
                        'calculation_method': item.deduction_id.ids,
                        'cause_type': punishment_line.termination_type.id,
                    })
                    termination_move.append(termination_move_id.id)

        self.termination_id = termination_move
        self.state = 'done'

    # dynamic domain get punishment_id

    @api.onchange('penalty_id')
    def _get_punishment_domain(self):
        list_items = self.penalty_id.first_time.ids
        list_items.extend(self.penalty_id.second_time.ids)
        list_items.extend(self.penalty_id.third_time.ids)
        list_items.extend(self.penalty_id.fourth_time.ids)
        list_items.extend(self.penalty_id.fifth_time.ids)
        domain = list(set(list_items))

        return {'domain': {'punishment_id': [('id', 'in', domain)]}}

    # dynamic domain get penalty_number
    @api.onchange('penalty_id', 'employee_id')
    def _get_penalty_number_domain(self):
        for rec in self:
            rec.punishment_id = False
            penalty_id = rec.search([('penalty_id', '=', rec.penalty_id.id), ('employee_id', '=', rec.employee_id.id),
                                     ('state', 'not in', ('refuse', 'draft'))], order='penalty_number desc', limit=1)
            penalty = penalty_id.penalty_number
            rec.last_penalty = penalty_id.id
            if penalty == 'first_time':
                rec.penalty_number = 'second_time'
                rec.punishment_id = self.penalty_id.second_time.ids

            elif penalty == 'second_time':
                rec.penalty_number = 'third_time'
                rec.punishment_id = self.penalty_id.third_time.ids

            elif penalty == 'third_time':
                rec.penalty_number = 'fourth_time'
                rec.punishment_id = self.penalty_id.fourth_time.ids

            elif penalty == 'fourth_time':
                rec.penalty_number = 'fifth_time'
                rec.punishment_id = self.penalty_id.fifth_time.ids
            else:
                rec.penalty_number = 'first_time'
                rec.punishment_id = self.penalty_id.first_time.ids

    # constrain on punishment_id

    @api.onchange('punishment_id')
    def compute_deduction_amount_from_penalty_punishment(self):
        total_number = 0.0
        for item in self.punishment_id:
            if item.type == 'penalty':
                if item.punishment_type == 'fixed_amount':
                    total_number += item.amount

                elif item.punishment_type == 'depend_on_salary' and item.allowance:
                    # initialize values
                    duration_amount = 0.0

                    for rule in item.allowance:
                        if item.duration > 0 and item.punishment_type_amount == 'duration':
                            duration = 30 / item.duration

                            # if self._compute_rule(line, self.employee_id) != None:
                            duration_amount += self._compute_rule(rule, self.employee_id.contract_id)
                            if duration_amount > 0.0:
                                total_number = duration_amount / duration

                        elif item.percentage > 0 and item.punishment_type_amount == 'percentage':
                            percentage = item.percentage / 100

                            # if self._compute_rule(line, self.employee_id) != None:
                            duration_amount += self._compute_rule(rule, self.employee_id.contract_id)

                            if duration_amount > 0.0:
                                total_number = duration_amount * percentage

        self.deduction_amount = total_number

    # Compute salary rules

    def _compute_rule(self, rule, contract):

        baselocaldict = {'categories': {}, 'rules': {}, 'payslip': {}, 'worked_days': {},
                         'inputs': {}}
        localdict = dict(baselocaldict, employee=contract.employee_id, contract=contract)

        if rule.amount_select == 'percentage':
            total_percent = 0
            if rule.related_benefits_discounts:
                for line in rule.related_benefits_discounts:
                    if line.amount_select == 'fix':
                        total_percent += self._compute_rule(line, contract)
                    elif line.amount_select == 'percentage':
                        total_percent += self._compute_rule(line, contract)
                    else:
                        total_percent += self._compute_rule(line, contract)
            if total_percent:
                if rule.salary_type == 'fixed':
                    try:
                        return float(total_percent * rule.amount_percentage / 100)
                    except:
                        raise UserError(
                            _('Wrong percentage base or quantity defined for salary rule %s (%s).') % (
                                rule.name, rule.code))
                elif rule.salary_type == 'related_levels':
                    levels_ids = rule.salary_amount_ids.filtered(
                        lambda item: item.salary_scale_level.id == contract.salary_level.id)
                    if levels_ids:
                        for l in levels_ids:
                            try:
                                return float(l.salary * total_percent / 100)
                            except:
                                raise UserError(
                                    _('Wrong quantity defined for salary rule %s (%s).') % (
                                        rule.name, rule.code))
                    else:
                        return 0
                elif rule.salary_type == 'related_groups':
                    groups_ids = rule.salary_amount_ids.filtered(
                        lambda item: item.salary_scale_group.id == contract.salary_group.id)
                    if groups_ids:
                        for g in groups_ids:
                            try:
                                return float(g.salary * total_percent / 100)
                            except:
                                raise UserError(
                                    _('Wrong quantity defined for salary rule %s (%s).') % (
                                        rule.name, rule.code))
                    else:
                        return 0
                elif rule.salary_type == 'related_degrees':
                    degrees_ids = rule.salary_amount_ids.filtered(
                        lambda item: item.salary_scale_degree.id == contract.salary_degree.id)
                    if degrees_ids:
                        for d in degrees_ids:
                            try:
                                return float(d.salary * total_percent / 100)
                            except:
                                raise UserError(
                                    _('Wrong quantity defined for salary rule %s (%s).') % (
                                        rule.name, rule.code))
                    else:
                        return 0
            else:
                try:
                    return 0
                except:
                    raise Warning(_('There is no total for rule : %s') % (rule.name))

        elif rule.amount_select == 'fix':
            if rule.salary_type == 'fixed':
                try:
                    return rule.fixed_amount
                except:
                    raise UserError(_('Wrong quantity defined for salary rule %s (%s).') % (rule.name, rule.code))
            elif rule.salary_type == 'related_levels':
                levels_ids = rule.salary_amount_ids.filtered(
                    lambda item: item.salary_scale_level.id == contract.salary_level.id)
                if levels_ids:
                    for l in levels_ids:
                        try:
                            return l.salary
                        except:
                            raise UserError(
                                _('Wrong quantity defined for salary rule %s (%s).') % (rule.name, rule.code))
                else:
                    return 0
            elif rule.salary_type == 'related_groups':
                groups_ids = rule.salary_amount_ids.filtered(
                    lambda item: item.salary_scale_group.id == contract.salary_group.id)
                if groups_ids:
                    for g in groups_ids:
                        try:
                            return g.salary
                        except:
                            raise UserError(
                                _('Wrong quantity defined for salary rule %s (%s).') % (rule.name, rule.code))
                else:
                    return 0
            elif rule.salary_type == 'related_degrees':
                degrees_ids = rule.salary_amount_ids.filtered(
                    lambda item: item.salary_scale_degree.id == contract.salary_degree.id)
                if degrees_ids:
                    for d in degrees_ids:
                        try:
                            return d.salary
                        except:
                            raise UserError(
                                _('Wrong quantity defined for salary rule %s (%s).') % (rule.name, rule.code))
                else:
                    return 0
            else:
                raise UserError(_('Error'))

        else:
            try:
                safe_eval(rule.amount_python_compute, localdict, mode='exec', nocopy=True)
                paython_code = float(localdict['result']), 'result_qty' in localdict and localdict[
                    'result_qty'] or 1.0, 'result_rate' in localdict and localdict['result_rate'] or 100.0
                return float(localdict['result'])
            except:
                raise UserError(_('Wrong python code defined for salary rule %s (%s).') % (rule.name, rule.code))

    # Override unlink function
    def unlink(self):
        for i in self:
            if i.state != 'draft':
                raise exceptions.Warning(_('You can not delete record in state not in draft'))

        return super(penalty_register, self).unlink()


class Employee(models.Model):
    _inherit = 'hr.employee'

    penalty_history_ids = fields.One2many(comodel_name='hr.penalty.register', inverse_name='employee_id')
