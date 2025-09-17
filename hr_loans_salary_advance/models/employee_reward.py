# -*- coding: utf-8 -*-

import calendar
from datetime import date

from odoo import models, fields, api, _, exceptions


class HrEmployeeReward(models.Model):
    _inherit = 'hr.employee.reward'

    def action_done(self):
        super(HrEmployeeReward, self).action_done()
        installment = self.env['loan.installment.line']
        if self.transfer_type == 'accounting':
            for line in self.line_ids_reward:
                installment.search([('reward_line_id', '=', line.id),
                                    ('paid', '=', False)]).write({'paid': True})
                if line.move_id and line.installment > 0:
                    line.move_id.write({'line_ids': [(2, ml.id, False) for ml in line.move_id.line_ids]})
                    lines = [(0, 0, {'name': line.employee_id.name,
                                     'credit': line.amount,
                                     'account_id': line.journal_id.default_account_id.id,
                                     'partner_id': line.employee_id.user_id.partner_id.id
                                     }),
                             (0, 0, {'name': line.employee_id.name,
                                     'debit': line.gross_amount,
                                     'account_id': line.account_id.id,
                                     'partner_id': line.employee_id.user_id.partner_id.id
                                     })]
                    for loan in line.loan_ids:
                        lines.append((0, 0, {'name': line.employee_id.name,
                                             'credit': loan.loan_amount,
                                             'account_id': loan.loan_id.request_type.account_id.id,
                                             'partner_id': line.employee_id.user_id.partner_id.id
                                             }), )
                        loan.loan_id.state = 'closed'
                    line.move_id.write({'line_ids': lines})
        elif self.transfer_type == 'payroll':
            for line in self.line_ids_reward:
                installment.search([('reward_line_id', '=', line.id),
                                    ('paid', '=', False)]).write({'paid': True})
                if line.installment > 0:
                    if line.employee_id.contract_id:
                        for loan in line.loan_ids:
                            if not loan.loan_id.request_type.loan_deduction_id:
                                raise exceptions.Warning(_(
                                    'Please set a deduction for loan %s ') % loan.loan_id.request_type.name)
                            df = date.today().replace(day=1)
                            dt = date.today().replace(day=calendar.monthrange(date.today().year, date.today().month)[1])
                            advantage = line.employee_id.contract_id.advantages.filtered(
                                lambda a: a.reward_id == self.id
                                          and a.benefits_discounts.id == self.benefits_discounts.id
                                          and a.date_from == str(df) and a.date_to == str(dt))[0]
                            line.employee_id.contract_id.write({
                                'advantages': [
                                    (0, 0, {'benefits_discounts': loan.loan_id.request_type.loan_deduction_id.id,
                                            'type': 'customize',
                                            'date_from': df,
                                            'date_to': dt,
                                            'amount': loan.loan_amount,
                                            'reward_id': self.id}),
                                    (1, advantage.id, {'amount': line.gross_amount})
                                ]
                            })
                            loan.loan_id.state = 'closed'

    def re_draft(self):
        super(HrEmployeeReward, self).re_draft()
        installment = self.env['loan.installment.line']
        for line in self.line_ids_reward:
            if line.loan_ids:
                for loan in line.loan_ids:
                    loan.loan_id.state = 'pay'
                    installment.search([('reward_line_id', '=', line.id),
                                        ('paid', '=', True)]).write({'paid': False, 'reward_line_id': False})
        self.recalculate()

    def action_refuse(self):
        super(HrEmployeeReward, self).action_refuse()
        installment = self.env['loan.installment.line']
        for line in self.line_ids_reward:
            if line.loan_ids:
                for loan in line.loan_ids:
                    loan.loan_id.state = 'pay'
                    installment.search([('reward_line_id', '=', line.id),
                                        ('paid', '=', True)]).write({'paid': False, 'reward_line_id': False})
        self.recalculate()

    @api.constrains('allowance_name', 'line_ids_reward')
    def check_due_loan(self):
        msg = ''
        for line in self.line_ids_reward:
            if line.due_loan:
                msg += line.employee_id.name + '\n'
        if msg:
            raise exceptions.Warning(
                _('The bonuses for Following Employees do not cover their due loans \n %s ') % msg)


class HrEmployeeRewardLine(models.Model):
    _inherit = 'lines.ids.reward'

    gross_amount = fields.Float(string="Reward Gross Amount", default=0)
    amount = fields.Float(string="Amount", compute='_compute_calculate_amount', store=True)
    installment = fields.Float(string="Loan Amount")
    due_loan = fields.Boolean(string='Due Loan', default=False)
    loan_ids = fields.One2many('employee.reward.loan', 'reward_id', string='Employee Loans')

    @api.depends('percentage', 'employee_reward_id', 'employee_id', 'account_id', 'journal_id')
    def _compute_calculate_amount(self):
        super(HrEmployeeRewardLine, self)._compute_calculate_amount()
        for line in self:
            if line.employee_reward_id.reward_type == 'allowance':
                line.gross_amount = line.amount and line.amount or 0
                line.installment, line.due_loan = 0, False
                emp_loans = self.env['hr.loan.salary.advance'].search([('employee_id', '=', line.employee_id.id),
                                                                       ('remaining_loan_amount', '>', 0),
                                                                       ('request_type.bonus_id', '=',
                                                                        line.employee_reward_id.allowance_name.id),
                                                                       ('request_type.refund_from', '=', 'bonus'),
                                                                       ('state', '=', 'pay')])
                for loan in emp_loans:
                    if loan.remaining_loan_amount > line.gross_amount or loan.remaining_loan_amount > line.amount:
                        line.due_loan = True
                        continue
                    loan_amount = 0
                    for instl in loan.deduction_lines.filtered(lambda l: l.paid == False):
                        instl.write({'reward_line_id': line.id})
                        line.amount -= instl.installment_amount
                        loan_amount += instl.installment_amount
                        line.installment += instl.installment_amount
                    l2u = line.loan_ids.filtered(lambda l: l.loan_id.id == loan.id)
                    loan_list = l2u and [(1, l2u[0].id, {'loan_amount': loan_amount})] \
                                or [(0, 0, {'loan_id': loan.id, 'loan_amount': loan_amount, 'reward_id': line.id})]
                    line.write({'loan_ids': loan_list})


class HrEmployeeRewardLoan(models.Model):
    _name = 'employee.reward.loan'

    reward_id = fields.Many2one('lines.ids.reward', string='Employee Reward')
    loan_id = fields.Many2one('hr.loan.salary.advance', string='Loan')
    loan_amount = fields.Float(string='Loan Amount')
