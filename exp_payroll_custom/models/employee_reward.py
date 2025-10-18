# -*- coding: utf-8 -*-

import calendar
from datetime import date, datetime

from odoo import models, fields, api, _, exceptions


class EmployeeReward(models.Model):
    _name = 'hr.employee.reward'
    _rec_name = 'allowance_name'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    line_ids_reward = fields.One2many(comodel_name='lines.ids.reward', inverse_name='employee_reward_id',
                                      string="Reward Line")
    date = fields.Date(default=lambda self: fields.Date.today(), string="Date Request",
                       required=True, tracking=True)
    date_from = fields.Date(string="Date From", tracking=True)
    date_to = fields.Date(string="Date To", tracking=True)
    allowance_reason = fields.Text(string="Reward Reason", required=True)
    allowance_name = fields.Many2one('hr.salary.rule', string="Allowance Name")
    percentage = fields.Float(string="Percentage%", default=100)
    amount = fields.Float(string="Amount")
    account_id = fields.Many2one('account.account')
    journal_id = fields.Many2one('account.journal', string='Payment Method')
    next_approve = fields.Text(string="Next Required Approval", compute="_get_nxt_approve")
    reward_type = fields.Selection(
        [('allowance', 'Allowance'), ('amount', 'Amount')], default='allowance')
    transfer_type = fields.Selection(
        [('accounting', 'Accounting'), ('payroll', 'Payroll')], default='accounting')
    state = fields.Selection(
        [('draft', 'Draft'), ('submitted', 'Submit'), ('hrm', 'HRM Approval'),
         ('done', 'GM Approval'), ('refused', 'Refused')], default='draft', tracking=True)
    benefits_discounts = fields.Many2one(comodel_name='hr.salary.rule', string='Rewards/Benefits')

    check_appraisal = fields.Boolean(string='Appraisal‏ Percentage', default=False)
    reward_once = fields.Boolean(string='Reward Once Yearly', default=False)

    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env.company)

    def action_add_employees(self):
        self.ensure_one()
        ctx = dict(self.env.context)
        if not self.id:
            ctx.update({
                'default_reward_vals': {
                    'name': self.name,
                }
            })
        else:
            ctx['default_employee_reward_id'] = self.id

        if self.percentage:
            ctx['default_percentage'] = self.percentage

        ctx['default_employee_id'] = self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)

        return {
            'name': _('Add Employees to Reward'),
            'view_mode': 'form',
            'res_model': 'employee.selection.wizard',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': ctx,
        }

    @api.onchange('amount')
    def chick_amount_positive(self):
        for item in self:
           if item.amount < 0:
              raise exceptions.Warning(_('The Amount Must Be Greater Than Zero'))


    @api.depends('state')
    def _get_nxt_approve(self):
        for record in self:
            if record.state == "draft":
                record.next_approve = "Submit"
                for line in record.line_ids_reward:
                    line.reward_state = "draft"
            elif record.state == "submitted":
                record.next_approve = "HRM Approval"
                for line in record.line_ids_reward:
                    line.reward_state = "submitted"
            elif record.state == "hrm":
                record.next_approve = "GM Approval"
                for line in record.line_ids_reward:
                    line.reward_state = "hrm"
            elif record.state == "done":
                for line in record.line_ids_reward:
                    line.reward_state = "done"
            elif record.state == "refused":
                for line in record.line_ids_reward:
                    line.reward_state = "refused"

    def action_submit(self):
        if not self.line_ids_reward:
            raise exceptions.Warning(_('Sorry, Can Not Request without The Employees'))
        self.state = "submitted"
        for line in self.line_ids_reward:
            line.check_reward_once()
            line.reward_state = "submitted"

    def recalculate(self):
        for line in self.line_ids_reward:
            # line.amount = line.amount
            # line.percentage = line.percentage
            line._compute_calculate_amount()

    def action_hrm(self):
        self.state = "hrm"
        for line in self.line_ids_reward:
            line.check_reward_once()
            line.reward_state = "hrm"

    def action_done(self):
        if self.transfer_type == 'accounting':
            for item in self:
                for record in item.line_ids_reward:
                    debit_line_vals = {
                        'name': record.employee_id.name,
                        'debit': record.amount,
                        'account_id': item.account_id.id,
                        'partner_id': record.employee_id.user_id.partner_id.id,
                        'analytic_account_id': record.employee_id.department_id.analytic_account_id.id
                    }
                    credit_line_vals = {
                        'name': record.employee_id.name,
                        'credit': record.amount,
                        'account_id': item.journal_id.default_account_id.id
                        #'partner_id': record.employee_id.user_id.partner_id.id
                    }
                    if not record.move_id:
                       move = record.env['account.move'].create({
                           'state': 'draft',
                           'journal_id': item.journal_id.id,
                           'date': item.date,
                           'ref': record.employee_id.name,
                           'line_ids': [(0, 0, debit_line_vals), (0, 0, credit_line_vals)],
                           'res_model': 'hr.employee.reward',
                           'res_id': self.id
                       })

                       record.move_id = move.id
            self.state = "done"
            for line in self.line_ids_reward:
                line.reward_state = "done"
        if self.transfer_type == 'payroll':
            last_day_of_current_month = date.today().replace(
                day=calendar.monthrange(date.today().year, date.today().month)[1])
            first_day_of_current_month = date.today().replace(day=1)
            for item in self:
                for record in item.line_ids_reward:
                    if record.employee_id.contract_id:

                        advantage_arc = record.env['contract.advantage'].create({
                            'benefits_discounts': item.benefits_discounts.id,
                            'type': 'customize',
                            'date_from': item.date_from,
                            'date_to': item.date_to,
                            'amount': record.amount,
                            'reward_id': True,
                            'employee_id': record.employee_id.id,
                            'contract_advantage_id': record.employee_id.contract_id.id,
                            'out_rule': True,
                            'state': 'confirm',
                            'comments': item.allowance_reason})
                        record.advantage_id = advantage_arc.id
                    else:
                        raise exceptions.Warning(_(
                            'Employee "%s" has no contract Please create contract to add line to advantages')
                                                 % record.employee_id.name)

            self.state = "done"
            for line in self.line_ids_reward:
                line.reward_state = "done"

    def action_refuse(self):
        self.state = "refused"
        for line in self.line_ids_reward:
            line.reward_state = "refused"

    def re_draft(self):
        # when redraft cancel the created account move
        if self.transfer_type == 'payroll':
            for record in self.line_ids_reward:
                record.advantage_id.draft()
                record.advantage_id.unlink()
                record.reward_state = "draft"
            self.state = "draft"

        if self.transfer_type == 'accounting':
            if self.transfer_type == 'accounting':
                if self.line_ids_reward and self.line_ids_reward[0].move_id:
                    move_id_not_draft = False
                    for line in self.line_ids_reward:
                        if line.move_id.state == 'posted':
                            move_id_not_draft_name = line.move_id.name
                            move_id_not_draft = True
                    if move_id_not_draft:
                        raise exceptions.Warning(_(
                            'You can not cancel account move "%s" in state not draft') % move_id_not_draft_name)
                    else:
                        for record in self.line_ids_reward:
                            # record.move_id.write({'state': 'canceled'})
                            record.move_id.unlink()
                            record.write({'move_id': False, })
                            #record.account_id = False
                            #record.journal_id = False
                            record.reward_state = "draft"
                        self.write({'state': 'draft'})
                        #self.account_id = False
                        #self.journal_id = False
                else:
                    self.write({
                        'state': 'draft',
                        #'account_id': False,
                        #'journal_id': False
                    })
                    for record in self.line_ids_reward:
                        record.write({
                            'move_id': False,
                            #'account_id': False,
                            #'journal_id': False,
                            'reward_state': 'draft'
                        })

    def unlink(self):
        for i in self:
            if i.state != 'draft':
                raise exceptions.Warning(_('You can not delete record in state not in draft'))
            i.line_ids_reward.unlink()
        return super(EmployeeReward, self).unlink()

    @api.onchange('transfer_type', 'account_id', 'journal_id', 'line_ids_reward')
    def onchange_transfer_type(self):
        if self.transfer_type == 'payroll':
            self.account_id = False
            self.journal_id = False
            for line in self.line_ids_reward:
                line.account_id = False
                line.journal_id = False
        if self.transfer_type == 'accounting':
            for line in self.line_ids_reward:
                if self.state == 'hrm':
                    if not line.account_id:
                        line.account_id = self.account_id
                    if not line.journal_id:
                        line.journal_id = self.journal_id
                else:
                    line.account_id = False
                    line.journal_id = False

    @api.onchange('account_id')
    def onchange_account_id(self):
        for line in self.line_ids_reward:
            self.recalculate()
            line.account_id = self.account_id

    @api.onchange('journal_id')
    def onchange_journal_id(self):
        for line in self.line_ids_reward:
            self.recalculate()
            line.journal_id = self.journal_id


class HrEmployee(models.Model):
    _name = 'lines.ids.reward'

    def _domain_get_employee(self):
        return [('id', '!=', self.employee_id.id), ('state', '=', 'open')]

    employee_reward_id = fields.Many2one('hr.employee.reward', string='Employee', required=True)
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True,
                                  domain=lambda self: self._domain_get_employee())
    amount = fields.Float(string="Amount", compute='_compute_calculate_amount', store=True)
    account_id = fields.Many2one('account.account', string='Account')
    journal_id = fields.Many2one('account.journal', string='Payment Method')
    percentage = fields.Float(string="Percentage%")
    move_id = fields.Many2one('account.move')
    contract_advantage_id = fields.Many2one('hr.contract')
    reward_state = fields.Selection(
        [('draft', 'Draft'), ('submitted', 'Submit'), ('hrm', 'HRM Approval'),
         ('done', 'GM Approval'), ('refused', 'Refused')], default='draft')

    amount_base = fields.Float(string="Amount Base", store=True)
    check_appraisal = fields.Boolean('Appraisal‏ Percentage', related='employee_reward_id.check_appraisal', store=True)
    transfer_type = fields.Selection(related='employee_reward_id.transfer_type', string='Transfer type')

    reward_once = fields.Boolean(related='employee_reward_id.reward_once', store=True)
    date = fields.Date(related='employee_reward_id.date', string='Reward Once Yearly', tracking=True, store=True)

    advantage_id = fields.Many2one(comodel_name='contract.advantage', string='Allowance Employee')

    reward_type = fields.Selection(related='employee_reward_id.reward_type', string='Reward Type', store=True)

    @api.onchange('amount_base')
    def chick_amount_base_positive(self):
        for item in self:
           if item.amount_base < 0:
              raise exceptions.Warning(_('The Employee %s Amount Must Be Greater Than Zero')% item.employee_id.name)


    # Select employee once in reward Line
    @api.onchange('employee_id')
    def select_employee_once(self):
        employee_ids = self.env['hr.employee'].search([('state', '=', 'open')]).ids

        for line in self.employee_reward_id.line_ids_reward:
            if line.employee_id:
                if line.employee_id.id in employee_ids:
                    employee_ids.remove(line.employee_id.id)

        return {'domain': {'employee_id': [('id', 'in', employee_ids)]}}

    def get_salary_rules_account(self, record_id, amount, items):
        record = self.env['hr.salary.rule.line'].create({
            'salary_rule_id': record_id.id,
            'amount': amount,
        })
        items.append(record.id)

    def compute_salary_rule(self, record_id, item, items):
        for record in self:
            if not record.employee_id.id: continue
            contract = self.env['hr.contract'].search([('employee_id', '=', record.employee_id.id)])
            localdict = dict(employee=record.employee_id.id, contract=contract)
            amount, total = 0.0, 0.0

            if item.amount_select == 'fix':
                if contract.advantages:
                    for con in contract.advantages:
                        if item.id == con.benefits_discounts.id:
                            if con.type == 'exception':
                                if con.amount > item._compute_rule(localdict)[0] or con.amount == \
                                        item._compute_rule(localdict)[0]:
                                    pass
                                elif con.amount < item._compute_rule(localdict)[0]:
                                    total = item._compute_rule(localdict)[0] - con.amount
                            elif con.type == 'customize':
                                total = con.amount
                            amount = 0
                            amount += total
                        else:
                            amount = 0
                            amount += item._compute_rule(localdict)[0]
                else:
                    amount += item._compute_rule(localdict)[0]

            elif item.amount_select == 'percentage':
                if contract and contract.advantages:
                    for con in contract.advantages:
                        if item.id == con.benefits_discounts.id:
                            if con.type == 'exception':
                                if con.amount > item._compute_rule(localdict)[0] or con.amount == \
                                        item._compute_rule(localdict)[0]:
                                    pass
                                elif con.amount < item._compute_rule(localdict)[0]:
                                    total = item._compute_rule(localdict)[0] - con.amount
                            elif con.type == 'customize':
                                total = con.amount
                            amount = 0
                            amount += total
                            break
                        else:
                            if amount:
                                pass
                            else:
                                amount += item._compute_rule(localdict)[0]
                else:
                    amount += item._compute_rule(localdict)[0]

            else:
                if contract.advantages:
                    for con in contract.advantages:
                        if item.id == con.benefits_discounts.id:
                            if con.type == 'exception':
                                if con.amount > item._compute_rule(localdict)[0] or con.amount == \
                                        item._compute_rule(localdict)[0]:
                                    pass
                                elif con.amount < item._compute_rule(localdict)[0]:
                                    total = item._compute_rule(localdict)[0] - con.amount
                            elif con.type == 'customize':
                                total = con.amount
                            amount = 0
                            amount += total
                        else:
                            if amount:
                                pass
                            else:
                                amount = 0
                                amount += item._compute_rule(localdict)[0]
                else:
                    amount += item._compute_rule(localdict)[0]

            return amount

    @api.depends('percentage', 'employee_reward_id', 'employee_id', 'account_id', 'journal_id','amount_base')
    def _compute_calculate_amount(self):
        for line in self:
            if line.check_appraisal == True:
                self.get_percentage_appraisal()
            percentage = line.percentage
            if line.employee_reward_id.reward_type == 'allowance':
                if line.employee_reward_id.allowance_name:
                    items = []
                    for item in line.employee_reward_id.allowance_name:
                        total = 0.0
                        record_id = self.env['hr.salary.rule'].search([('id', '=', item.id)])
                        total = self.compute_salary_rule(record_id, item, items) or 0
                    amount = (total * percentage) / 100
                    line.amount = amount
                    amount_base = total
                    line.amount_base = amount_base
            elif line.employee_reward_id.reward_type == 'amount':
                amount_up = line.employee_reward_id.amount
                if amount_up > 0:
                   amount = (amount_up * percentage) / 100
                   line.amount = amount
                   amount_base = amount_up 
                   line.amount_base = amount_base
                else:
                   line.amount = (line.amount_base * percentage) / 100

            else:
                line.amount = 0

    @api.model
    def default_get(self, fields):
        res = super(HrEmployee, self).default_get(fields)
        if self._context.get('percentage'):
            res['percentage'] = self._context.get('percentage')
        if self._context.get('account_id') and self._context.get('journal_id'):
            res['account_id'] = self._context.get('account_id')
            res['journal_id'] = self._context.get('journal_id')
        return res

    # get percentage from performance appraisal
    def get_percentage_appraisal(self):
        Module = self.env['ir.module.module'].sudo()
        modules = Module.search([('state', '=', 'installed'), ('name', '=', 'exp_hr_appraisal')])

        for line in self:
            if modules:
                emp_appraisal = self.env['hr.employee.appraisal'].search([('employee_id', '=', line.employee_id.id),
                                                                          ('state', '!=', 'draft'),
                                                                          ('appraisal_type', '=', 'performance')],
                                                                         order='appraisal_date desc', limit=1)
                level_achieved = emp_appraisal.level_achieved
                if line.check_appraisal:
                    if emp_appraisal:
                        line.percentage = level_achieved
                    else:
                        line.percentage = 0

    # To Cannot Take More Than Once Reward In The Same Year

    @api.constrains('employee_id', 'date', 'reward_once')
    def check_reward_once(self):
        for rec in self:
            if rec.date:
                current_year = datetime.strptime(str(rec.date), "%Y-%m-%d").date().year
                last_reward = rec.search([('id', '!=', rec.id), ('employee_id', '=', rec.employee_id.id),
                                          ('reward_state', 'not in', ('draft', 'refused')),
                                          ('reward_once', '=', True)], order='date desc', limit=1).date
                if last_reward:
                    last_year = datetime.strptime(str(last_reward), "%Y-%m-%d").date().year
                    if current_year == last_year and rec.reward_once:
                        raise exceptions.Warning(_('Sorry, The Employee %s Cannot be Taking More Than Once Reward '
                                                   'In The Same Year %s') % (rec.employee_id.name, current_year))

    def unlink(self):
        for i in self:
            if i.reward_state != 'draft':
                raise exceptions.Warning(_('You can not delete record in state not in draft'))
        return super(HrEmployee, self).unlink()
