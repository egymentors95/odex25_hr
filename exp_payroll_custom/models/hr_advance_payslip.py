# -*- coding: utf-8 -*-

import itertools as it
import time
from datetime import datetime, timedelta
from operator import itemgetter

import babel
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, tools, _, exceptions
from odoo.exceptions import UserError, except_orm

# solve Python uses "round half to even" by default 
from decimal import Decimal, ROUND_HALF_UP 

# New object for loans lines in payslip
class PayslipLoans(models.Model):
    _name = 'payslip.loans'

    name = fields.Char(string='Name')
    code = fields.Char(string='Code')
    amount = fields.Float(string='Amount')
    date = fields.Date(string='Installment Date')
    paid = fields.Boolean()

    # Relational field
    payslip_loan = fields.Many2one('hr.payslip', ondelete='cascade')
    account_id = fields.Many2one('account.account')


class SalaryRuleInput(models.Model):
    _inherit = 'hr.payslip'

    total_allowances = fields.Float(string='Total Allowance', compute='compute_totals')
    total_deductions = fields.Float(string='Total Deduction', compute='compute_totals')
    total_loans = fields.Float(string='Total Loans', compute='compute_totals')
    total_sum = fields.Float(string='Total Net', compute='compute_totals')
    state = fields.Selection(selection_add=[('computed', 'Computed'), ('confirmed', 'Confirmed'),
                                            ('transfered', 'Transfer'), ('close', 'Close')], tracking=True)
    level_id = fields.Many2one('hr.payroll.structure', string='Level', readonly=1)
    group_id = fields.Many2one('hr.payroll.structure', string='Group', readonly=1)
    degree_id = fields.Many2one('hr.payroll.structure', string='Degree', readonly=1)

    # Relational fields
    allowance_ids = fields.One2many('hr.payslip.line', 'payslip_allowance', string='Allowances', index=True)
    deduction_ids = fields.One2many('hr.payslip.line', 'payslip_deduction', string='Deductions', index=True)
    loan_ids = fields.One2many('payslip.loans', 'payslip_loan', string='Loans', index=True)
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True, readonly=True,
                                  states={'draft': [('readonly', False)]}, domain="[('state','=','open')]", index=True)
    contract_id = fields.Many2one('hr.contract', string='Contract', readonly=True, related='employee_id.contract_id')
    struct_id = fields.Many2one('hr.payroll.structure', string='Structure', readonly=True,
                                related='employee_id.contract_id.salary_scale',
                                help='Defines the rules that have to be applied to this payslip, accordingly '
                                     'to the contract chosen. If you let empty the field contract, this field isn\'t '
                                     'mandatory anymore and thus the rules applied will be all the rules set on the '
                                     'structure of all contracts of the employee valid for the chosen period')
    percentage = fields.Float(string='Percentage', default=100)
    move_id = fields.Many2one('account.move', string="Move Number")
    # bank_id = fields.Many2one(related='employee_id.bank_account_id.bank_id')

    basic_allowances = fields.Float(string='Basic Salary', compute='compute_allowances_')
    house_allowances = fields.Float(string='House Allowance', compute='compute_allowances_')
    trans_allowances = fields.Float(string='Transport Allowance', compute='compute_allowances_')
    other_allowances = fields.Float(string='Others Allowance', compute='compute_allowances_')

    employee_insurnce = fields.Float(string='Employee Insurnce', compute='compute_allowances_',store=True)
    company_insurnce = fields.Float(string='Company Insurnce', compute='compute_allowances_',store=True)

    employee_no = fields.Char(related='employee_id.emp_no', readonly=True,string='Employee Number', store=True)
    holiday_start_date = fields.Date(string="Holiday Start Date")
    holiday_end_date = fields.Date(string="Holiday End Date")

    def compute_allowances_(self):
        for item in self:
            item.basic_allowances, item.house_allowances, trans_allowances, employee_insurnce, company_insurnce = 0.0, 0.0, 0.0, 0.0, 0.0
            for line in item.allowance_ids:
                if line.salary_rule_id.rules_type == 'salary':
                    item.basic_allowances = line.total
                elif line.salary_rule_id.rules_type == 'house':
                    item.house_allowances = line.total
                elif line.salary_rule_id.rules_type == 'transport':
                    item.trans_allowances = line.total
            item.other_allowances = item.total_allowances - (
                        item.basic_allowances + item.house_allowances + item.trans_allowances)

            for line in item.deduction_ids:
                if line.salary_rule_id.rules_type == 'insurnce':
                    item.employee_insurnce = line.total
                    # TO Dooo
                    '''if item.employee_insurnce and line.employee_id.contract_id.is_gosi_deducted=='yes':
                       total_insurnce = item.employee_insurnce*100/10
                       item.company_insurnce = total_insurnce*12/100
                 else:
                       item.company_insurnce = (item.basic_allowances + item.house_allowances)*2/100'''

    def confirm(self):
        self.write({'state': 'confirmed'})

    def payslip_close(self):
        self.write({'state': 'close'})

    def withdraw(self):
        payslip = self.env['hr.payslip'].search([('number', '=', self.number)])
        loans = self.env['hr.loan.salary.advance'].search([('employee_id', '=', self.employee_id.id)])
        if self.number == payslip.number:
            if self.loan_ids:
                for loan in self.loan_ids:
                    loan.paid = False
                    if loans:
                        for i in loans:
                            if i.id == loan.loan_id.id:
                                for l in i.deduction_lines:
                                    if loan.date == l.installment_date and loan.paid is False:
                                        l.paid = False
                                        #i.remaining_loan_amount += l.installment_amount
                                        i.get_remaining_loan_amount()

                                # check remaining loan and change state to pay
                                if i.state == 'closed' and i.remaining_loan_amount > 0.0:
                                    i.state = 'pay'
                                elif i.remaining_loan_amount == 0.0 and i.gm_propos_amount > 0.0:
                                    i.state = 'closed'

        for line in payslip.worked_days_line_ids:
            if line.name != 'Working days for this month':
                line.unlink()
        self.write({'allowance_ids': [(5,)], 'deduction_ids': [(5,)], 'loan_ids': [(5,)]})
        self.write({'state': 'draft'})

    def return_button(self):
        if self.contract_id.advantages:
            for advantage_rule in self.contract_id.advantages:
                advantage_rule.write({'done': False})
        if self.move_id:
            if self.move_id.state == 'posted':
                raise exceptions.Warning(_('You can not Return account move %s in state not draft') % self.move_id.name)
            else:
                self.move_id.unlink()
                self.move_id = False

        if self.payslip_run_id:
            if self.payslip_run_id.move_id:
                raise exceptions.Warning(
                    _('You can not Return Payslips Patch Has account move %s') % self.payslip_run_id.move_id.name)

        self.write({'state': 'computed'})

    def transfer(self):
        total_list = []
        amount, amount1, amount2 = 0.0, 0.0, 0.0
        total_allow, total_ded, total_loan = 0.0, 0.0, 0.0

        #if self.struct_id.transfer_type == 'one_by_one':
        if self.struct_id.transfer_type == 'one_by_one' or self.struct_id.transfer_type == 'all' :
            for l in self.allowance_ids:
                amount_allow = l.total
                account = l.salary_rule_id.rule_debit_account_id
                total_list.append({
                    'name': l.name,
                    'account_id': account.id,
                    'debit': amount_allow,
                    'partner_id': self.employee_id.user_id.partner_id.id,
                    'analytic_account_id': self.employee_id.contract_id.analytic_account_id.id,
                })
                amount += amount_allow
            total_allow += amount

            for ded in self.deduction_ids:
                amount_ded = -ded.total
                account = ded.salary_rule_id.rule_credit_account_id
                total_list.append({
                    'name': ded.name,
                    'account_id': account.id,
                    'credit': amount_ded,
                    'partner_id': self.employee_id.user_id.partner_id.id
                })
                amount1 += amount_ded
            total_ded += amount1

            for lo in self.loan_ids:
                amount_loans = -lo.amount
                total_list.append({
                    'name': lo.name + ' (' + lo.code + ')',
                    'account_id': lo.account_id.id,
                    'credit': amount_loans,
                    'partner_id': self.employee_id.user_id.partner_id.id
                })
                amount2 += amount_loans
            total_loan += amount2

            # create line for total of all allowance, deduction, loans of one employee
            total = total_allow - total_ded - total_loan
            total_list.append({
                'name': self.name,
                'account_id': self.contract_id.journal_id.default_account_id.id,
                'partner_id': self.employee_id.user_id.partner_id.id,
                'credit': total,
            })
            if not self.contract_id.journal_id.id:
                raise UserError(
                    _("Please be sure that the employee is linked to contract and contract linked with journal"))
            move = self.env['account.move'].create({
                'journal_id': self.contract_id.journal_id.id,
                'date': self.date_to,
                'ref': self.name,
                'line_ids': [(0, 0, item) for item in total_list]
            })
            self.move_id = move.id
        else:
            if self.employee_id.payment_method == 'bank':
                journal = self.env['account.journal'].search([('type', '=', self.employee_id.payment_method)], limit=1)

                if not journal:
                    raise except_orm('Error', ' There is no journal For that Bank..'
                                              ' Please define a sale journal')
            else:
                journal = self.contract_id.journal_id

            for l in self.allowance_ids:
                amount_allow = l.total
                account = l.salary_rule_id.rule_debit_account_id
                total_list.append({
                    'name': l.name,
                    'account_id': account.id,
                    'debit': amount_allow,
                    'partner_id': self.employee_id.user_id.partner_id.id
                })
                amount += amount_allow
            total_allow += amount

            for ded in self.deduction_ids:
                amount_ded = -ded.total
                account = ded.salary_rule_id.rule_credit_account_id
                total_list.append({
                    'name': ded.name,
                    'account_id': account.id,
                    'credit': amount_ded,
                    'partner_id': self.employee_id.user_id.partner_id.id
                })
                amount1 += amount_ded
            total_ded += amount1

            for lo in self.loan_ids:
                amount_loans = -lo.amount
                total_list.append({
                    'name': lo.name + ' (' + lo.code + ')',
                    'account_id': lo.account_id.id,
                    'credit': amount_loans,
                    'partner_id': self.employee_id.user_id.partner_id.id
                })
                total_loan += amount_loans

            # create line for total of all allowance, deduction, loans of one employee
            total = total_allow - total_ded - total_loan
            total_list.append({
                'name': "Total",
                'account_id': journal.id,
                'partner_id': self.employee_id.user_id.partner_id.id,
                'credit': total,
            })
            if not self.move_id:
               move = self.env['account.move'].create({
                   'journal_id': journal.id,
                   # 'date': fields.Date.context_today(self),
                   'date': self.date_to,
                   'ref': self.name,
                   'line_ids': [(0, 0, item) for item in total_list]
               })
               self.move_id = move.id
        self.write({'state': 'transfered'})

    def compute_totals(self):
        for item in self:
            item.total_allowances, item.total_deductions = 0.0, 0.0
            for line in item.allowance_ids:
                allow_tot = line.total
                item.total_allowances += allow_tot
            for line in item.deduction_ids:
                ded_tot = line.total
                item.total_deductions += ded_tot
            for line in item.loan_ids:
                item.total_loans += line.amount
            item.total_sum = item.total_allowances + item.total_deductions + item.total_loans

    def get_inputs(self, contract_ids, date_from, date_to):
        """This Compute the other inputs to employee payslip."""

        res = super(SalaryRuleInput, self).get_inputs(contract_ids, date_from, date_to)
        contract_obj = self.env['hr.contract']
        emp_id = contract_obj.browse(contract_ids[0].id).employee_id
        adv_salary = self.env['salary.advance'].search([('employee_id', '=', emp_id.id)])
        for adv_obj in adv_salary:
            current_date = datetime.strptime(str(date_from), '%Y-%m-%d').date().month
            date = adv_obj.date
            existing_date = datetime.strptime(str(date), '%Y-%m-%d').date().month
            if current_date == existing_date:
                state = adv_obj.state
                amount = adv_obj.advance
                for result in res:
                    if state == 'approve' and amount != 0 and result.get('code') == 'SAR':
                        result['amount'] = amount
        return res

    # Override function compute sheet in employee payslips

    def compute_sheet(self):
        for payslip in self:
            payslip_loans = []
            amount = 0
            flag = False
            number = payslip.number or self.env['ir.sequence'].next_by_code('salary.slip')
            # delete old payslip lines
            payslip.line_ids.unlink()
            # set the list of contract for which the rules have to be applied
            # if we don't give the contract, then the rules to apply should be for all current contracts of the employee
            contract_ids = payslip.contract_id.ids or \
                           self.get_contract(payslip.employee_id, payslip.date_from, payslip.date_to)
            lines = [(0, 0, line) for line in self._get_payslip_lines(contract_ids, payslip.id)]

            payslip.write({'line_ids': lines, 'number': number, 'level_id': payslip.contract_id.salary_level.id,
                           'group_id': payslip.contract_id.salary_group.id,
                           'degree_id': payslip.contract_id.salary_degree.id, })

            for line in payslip.line_ids:
                if line.category_id.rule_type == 'allowance' or line.category_id.rule_type == 'deduction':
                    flag = True

            if flag:
                allowances = payslip.line_ids.filtered(
                    lambda a: a.amount != 0 and a.rate != 0 and a.category_id.rule_type == 'allowance')
                payslip.allowance_ids = [(6, 0, allowances.ids)]
                deductions = payslip.line_ids.filtered(
                    lambda a: a.amount != 0 and a.rate != 0 and a.category_id.rule_type == 'deduction')
                for d in deductions:
                    if d.amount > 0:
                        d.amount = -d.amount
                    else:
                        d.amount = d.amount
                payslip.deduction_ids = [(6, 0, deductions.ids)]

            # Loans #
            loans = self.env['hr.loan.salary.advance'].search([('employee_id', '=', payslip.employee_id.id),
                                                               ('request_type.refund_from', '=', 'salary'),
                                                               ('state', '=', 'pay')]).filtered(
                lambda item: item.employee_id.state == 'open')
            if loans:
                for loan in loans:
                    for l in loan.deduction_lines:
                        if not l.paid and (
                                str(l.installment_date) <= str(payslip.date_from) or str(l.installment_date) <= str(payslip.date_to)):
                            employee_loan_id = payslip.loan_ids.filtered(
                                lambda item: item.name == loan.request_type.name)
                            if not employee_loan_id:
                                payslip_loans.append({
                                    'name': loan.request_type.name,
                                    'code': loan.code,
                                    'amount': round((-l.installment_amount),2),
                                    'date': l.installment_date,
                                    'account_id': loan.request_type.account_id.id,
                                    'loan_id': loan.id
                                })
                                l.paid = True
                                l.payment_date = payslip.date_to
                            else:
                                payslip.loan_ids = [(0, 0, loan_item) for loan_item in payslip_loans]

                    # check remaining loan and change state to closed
                    if loan.remaining_loan_amount <= 0.0 < loan.gm_propos_amount:
                        loan.state = 'closed'

                payslip.loan_ids = [(0, 0, loan_item) for loan_item in payslip_loans]

            # Holidays #
            holidays = self.env['hr.holidays'].search([('employee_id', '=', payslip.employee_id.id),
                                                       ('state', '=', 'validate1')]).filtered(
                lambda item: item.employee_id.state == 'open')

            contract = self.env['hr.contract'].search([('employee_id', '=', payslip.employee_id.id)])
            localdict = dict(employee=payslip.employee_id.id, contract=contract)

            number_of_days = 0

            for line in payslip.worked_days_line_ids:
                if line.name == 'Unpaid Holidays For this month':
                    line.unlink()
                elif line.name == 'Paid Holidays By percentage':
                    line.unlink()
                elif line.name == 'Additional Paid Holidays':
                    line.unlink()
                elif line.name == 'Exclusion or Reconcile Paid Holidays':
                    line.unlink()

            for holiday in holidays:
                if holiday.date_from and holiday.date_to:
                    holiday_date_from = datetime.strptime(str(holiday.date_from), '%Y-%m-%d %H:%M:%S').strftime('%Y-%m-%d')
                    holiday_date_to = datetime.strptime(str(holiday.date_to), '%Y-%m-%d %H:%M:%S').strftime('%Y-%m-%d')
                    payslip_date_from = str(payslip.date_from)
                    payslip_date_to = str(payslip.date_to)
                    if payslip.holiday_start_date and payslip.holiday_end_date:
                        payslip_date_from = str(payslip.holiday_start_date)
                        payslip_date_to = str(payslip.holiday_end_date)

                    if holiday.holiday_status_id.payslip_type == 'unpaid':
                        if payslip_date_to >= holiday_date_to and holiday_date_from >= payslip_date_from:
                            payroll_start = datetime.strptime(payslip_date_from, "%Y-%m-%d").date()
                            pyroll_end = datetime.strptime(payslip_date_to, "%Y-%m-%d").date()
                            pyroll_days = relativedelta(pyroll_end, payroll_start).days + 1
                            number_of_days = holiday.number_of_days_temp
                            if number_of_days >=28:
                               if pyroll_days ==28:
                                  number_of_days= number_of_days + 2
                               if pyroll_days ==29:
                                  number_of_days= number_of_days + 1
                               if pyroll_days ==31:
                                  number_of_days= number_of_days - 1
                            if holiday.number_of_days_temp >= 0:  # if holiday.number_of_days_temp <= 0:
                                payslip.worked_days_line_ids = [(0, 0, {
                                    'name': "Unpaid Holidays For this month",
                                    'sequence': 1,
                                    'payslip_id': payslip.id,
                                    'code': 2,
                                    'number_of_days': number_of_days,
                                    'number_of_hours': 0.0,
                                    'contract_id': payslip.contract_id.id})]
                        elif holiday_date_from >= payslip_date_from and payslip_date_to <= holiday_date_to and holiday_date_from <= payslip_date_to:
                            payroll_start = datetime.strptime(payslip_date_from, "%Y-%m-%d").date()
                            pyroll_end = datetime.strptime(payslip_date_to, "%Y-%m-%d").date()
                            pyroll_days = relativedelta(pyroll_end, payroll_start).days + 1

                            start_date = datetime.strptime(str(holiday.date_from), "%Y-%m-%d %H:%M:%S").date()
                            end_date = datetime.strptime(str(payslip.date_to), "%Y-%m-%d").date()
                            number_of_days = relativedelta(end_date, start_date).days + 1
                            #if number_of_days >=28:
                            if pyroll_days ==28:
                               number_of_days= number_of_days + 2
                            if pyroll_days ==29:
                               number_of_days= number_of_days + 1
                            if pyroll_days ==31:
                               number_of_days= number_of_days - 1
                            if number_of_days >= 0:  # number_of_days <= 0
                                payslip.worked_days_line_ids = [(0, 0, {
                                    'name': "Unpaid Holidays For this month",
                                    'sequence': 1,
                                    'payslip_id': payslip.id,
                                    'code': 2,
                                    'number_of_days': number_of_days,
                                    'number_of_hours': 0.0,
                                    'contract_id': payslip.contract_id.id})]
                        elif payslip_date_from >= holiday_date_from and payslip_date_to >= holiday_date_to and holiday_date_to >= payslip_date_from  :
                            payroll_start = datetime.strptime(payslip_date_from, "%Y-%m-%d").date()
                            pyroll_end = datetime.strptime(payslip_date_to, "%Y-%m-%d").date()
                            pyroll_days = relativedelta(pyroll_end, payroll_start).days + 1

                            start_date = datetime.strptime(payslip_date_from, "%Y-%m-%d").date()
                            end_date = datetime.strptime(str(holiday.date_to), "%Y-%m-%d %H:%M:%S").date()
                            number_of_days = relativedelta(end_date, start_date).days +1
                            if number_of_days >=28:
                               if pyroll_days ==28:
                                  number_of_days= number_of_days + 2
                               if pyroll_days ==29:
                                  number_of_days= number_of_days + 1
                               if pyroll_days ==31:
                                  number_of_days= number_of_days - 1
                            if number_of_days >= 0:  # number_of_days <= 0
                                payslip.worked_days_line_ids = [(0, 0, {
                                    'name': "Unpaid Holidays For this month",
                                    'sequence': 1,
                                    'payslip_id': payslip.id,
                                    'code': 2,
                                    'number_of_days': number_of_days,
                                    'number_of_hours': 0.0,
                                    'contract_id': payslip.contract_id.id
                                })]
                        else:
                            if payslip_date_to <= holiday_date_to and holiday_date_from <= payslip_date_from:
                            #if payslip_date_to <= holiday_date_to:
                                start_date = datetime.strptime(str(payslip.date_from), "%Y-%m-%d").date()
                                end_date = datetime.strptime(str(payslip.date_to), "%Y-%m-%d").date()
                                number_of_days = relativedelta(end_date, start_date).days + 1
                                if number_of_days ==28:
                                   number_of_days= number_of_days + 2
                                if number_of_days ==29:
                                   number_of_days= number_of_days + 1
                                if number_of_days ==31:
                                   number_of_days= number_of_days - 1
                                if number_of_days >= 0:  # number_of_days <= 0
                                    payslip.worked_days_line_ids = [(0, 0, {
                                        'name': "Unpaid Holidays For this month",
                                        'sequence': 1,
                                        'payslip_id': payslip.id,
                                        'code': 2,
                                        'number_of_days': number_of_days,
                                        'number_of_hours': 0.0,
                                        'contract_id': payslip.contract_id.id})]

                    elif holiday.holiday_status_id.payslip_type == 'percentage':
                        #if payslip.date_from >= holiday.date_from and payslip.date_to >= holiday.date_to:
                        if payslip_date_from >= holiday_date_from and payslip_date_to >= holiday_date_to:
                            start_date = datetime.strptime(payslip_date_from, "%Y-%m-%d").date()
                            end_date = datetime.strptime(holiday_date_to, "%Y-%m-%d").date() + timedelta(
                                days=1)
                            number_of_days = relativedelta(end_date, start_date).days
                            if number_of_days >= 0:  # number_of_days <= 0
                                payslip.worked_days_line_ids = [(0, 0, {
                                    'name': "Paid Holidays By percentage",
                                    'sequence': 1,
                                    'payslip_id': payslip.id,
                                    'code': 2,
                                    'number_of_days': number_of_days,
                                    'number_of_hours': holiday.holiday_status_id.percentage,
                                    'contract_id': payslip.contract_id.id})]
                        elif payslip_date_to >= holiday_date_to and holiday_date_from >= payslip_date_from:
                            if holiday.number_of_days_temp >= 0:  # holiday.number_of_days_temp <= 0
                                payslip.worked_days_line_ids = [(0, 0, {
                                    'name': "Paid Holidays By percentage",
                                    'sequence': 1,
                                    'payslip_id': payslip.id,
                                    'code': 2,
                                    'number_of_days': holiday.number_of_days_temp,
                                    'number_of_hours': holiday.holiday_status_id.percentage,
                                    'contract_id': payslip.contract_id.id})]
                        elif holiday_date_from >= payslip_date_from and payslip_date_to <= holiday_date_to:
                            start_date = datetime.strptime(holiday_date_from, "%Y-%m-%d %H:%M:%S").date()
                            end_date = datetime.strptime(payslip_date_to, "%Y-%m-%d").date()
                            number_of_days = relativedelta(end_date, start_date).days + 1
                            if number_of_days >= 0:  # number_of_days <= 0
                                payslip.worked_days_line_ids = [(0, 0, {
                                    'name': "Paid Holidays By percentage",
                                    'sequence': 1,
                                    'payslip_id': payslip.id,
                                    'code': 2,
                                    'number_of_days': number_of_days,
                                    'number_of_hours': holiday.holiday_status_id.percentage,
                                    'contract_id': payslip.contract_id.id})]
                        else:
                            if payslip_date_to <= holiday_date_to:
                                start_date = datetime.strptime(payslip_date_from, "%Y-%m-%d").date()
                                end_date = datetime.strptime(payslip_date_to, "%Y-%m-%d").date() + timedelta(
                                    days=1)
                                number_of_days = relativedelta(end_date, start_date).days
                                if number_of_days >= 0:  # number_of_days <= 0
                                    payslip.worked_days_line_ids = [(0, 0, {
                                        'name': "Paid Holidays By percentage",
                                        'sequence': 1,
                                        'payslip_id': payslip.id,
                                        'code': 2,
                                        'number_of_days': number_of_days,
                                        'number_of_hours': holiday.holiday_status_id.percentage,
                                        'contract_id': payslip.contract_id.id})]
                    elif holiday.holiday_status_id.payslip_type == 'addition':
                        if payslip_date_to >= holiday_date_to and holiday_date_from >= payslip_date_from:
                            payroll_start = datetime.strptime(payslip_date_from, "%Y-%m-%d").date()
                            pyroll_end = datetime.strptime(payslip_date_to, "%Y-%m-%d").date()
                            pyroll_days = relativedelta(pyroll_end, payroll_start).days + 1
                            number_of_days = holiday.number_of_days_temp
                            if number_of_days >= 28:
                                if pyroll_days == 28:
                                    number_of_days = number_of_days + 2
                                if pyroll_days == 29:
                                    number_of_days = number_of_days + 1
                                if pyroll_days == 31:
                                    number_of_days = number_of_days - 1
                            if holiday.number_of_days_temp >= 0:  # if holiday.number_of_days_temp <= 0:
                                payslip.worked_days_line_ids = [(0, 0, {
                                    'name': "Additional Paid Holidays",
                                    'sequence': 1,
                                    'payslip_id': payslip.id,
                                    'code': 2,
                                    'number_of_days': number_of_days,
                                    'number_of_hours': 0.0,
                                    'contract_id': payslip.contract_id.id})]
                        elif holiday_date_from >= payslip_date_from and payslip_date_to <= holiday_date_to and holiday_date_from <= payslip_date_to:
                            payroll_start = datetime.strptime(payslip_date_from, "%Y-%m-%d").date()
                            pyroll_end = datetime.strptime(payslip_date_to, "%Y-%m-%d").date()
                            pyroll_days = relativedelta(pyroll_end, payroll_start).days + 1

                            start_date = datetime.strptime(str(holiday.date_from), "%Y-%m-%d %H:%M:%S").date()
                            end_date = datetime.strptime(str(payslip.date_to), "%Y-%m-%d").date()
                            number_of_days = relativedelta(end_date, start_date).days + 1
                            # if number_of_days >=28:
                            if pyroll_days == 28:
                                number_of_days = number_of_days + 2
                            if pyroll_days == 29:
                                number_of_days = number_of_days + 1
                            if pyroll_days == 31:
                                number_of_days = number_of_days - 1
                            if number_of_days >= 0:  # number_of_days <= 0
                                payslip.worked_days_line_ids = [(0, 0, {
                                    'name': "Additional Paid Holidays",
                                    'sequence': 1,
                                    'payslip_id': payslip.id,
                                    'code': 2,
                                    'number_of_days': number_of_days,
                                    'number_of_hours': 0.0,
                                    'contract_id': payslip.contract_id.id})]
                        elif payslip_date_from >= holiday_date_from and payslip_date_to >= holiday_date_to and holiday_date_to >= payslip_date_from:
                            payroll_start = datetime.strptime(payslip_date_from, "%Y-%m-%d").date()
                            pyroll_end = datetime.strptime(payslip_date_to, "%Y-%m-%d").date()
                            pyroll_days = relativedelta(pyroll_end, payroll_start).days + 1

                            start_date = datetime.strptime(payslip_date_from, "%Y-%m-%d").date()
                            end_date = datetime.strptime(str(holiday.date_to), "%Y-%m-%d %H:%M:%S").date()
                            number_of_days = relativedelta(end_date, start_date).days + 1
                            if number_of_days >= 28:
                                if pyroll_days == 28:
                                    number_of_days = number_of_days + 2
                                if pyroll_days == 29:
                                    number_of_days = number_of_days + 1
                                if pyroll_days == 31:
                                    number_of_days = number_of_days - 1
                            if number_of_days >= 0:  # number_of_days <= 0
                                payslip.worked_days_line_ids = [(0, 0, {
                                    'name': "Additional Paid Holidays",
                                    'sequence': 1,
                                    'payslip_id': payslip.id,
                                    'code': 2,
                                    'number_of_days': number_of_days,
                                    'number_of_hours': 0.0,
                                    'contract_id': payslip.contract_id.id
                                })]
                        else:
                            if payslip_date_to <= holiday_date_to and holiday_date_from <= payslip_date_from:
                                # if payslip_date_to <= holiday_date_to:
                                start_date = datetime.strptime(str(payslip.date_from), "%Y-%m-%d").date()
                                end_date = datetime.strptime(str(payslip.date_to), "%Y-%m-%d").date()
                                number_of_days = relativedelta(end_date, start_date).days + 1
                                if number_of_days == 28:
                                    number_of_days = number_of_days + 2
                                if number_of_days == 29:
                                    number_of_days = number_of_days + 1
                                if number_of_days == 31:
                                    number_of_days = number_of_days - 1
                                if number_of_days >= 0:  # number_of_days <= 0
                                    payslip.worked_days_line_ids = [(0, 0, {
                                        'name': "Additional Paid Holidays",
                                        'sequence': 1,
                                        'payslip_id': payslip.id,
                                        'code': 2,
                                        'number_of_days': number_of_days,
                                        'number_of_hours': 0.0,
                                        'contract_id': payslip.contract_id.id})]

                        if payslip.worked_days_line_ids:
                            if number_of_days < 0 or holiday.number_of_days_temp < 0:
                                pass
                            else:
                                for line in holiday.holiday_status_id.salary_rules_ids:
                                    if line.amount_select == 'fix':
                                        for allowance in payslip.allowance_ids:
                                            if line.name == allowance.name:
                                                if line._compute_rule(localdict)[0] != allowance.amount:
                                                    amount = allowance.amount
                                                else:
                                                    amount = line._compute_rule(localdict)[0]
                                            else:
                                                amount = line._compute_rule(localdict)[0]
                                        for deduction in payslip.deduction_ids:
                                            if line.name == deduction.name:
                                                if line._compute_rule(localdict)[0] != deduction.amount:
                                                    amount = (-deduction.amount)
                                                else:
                                                    amount = line._compute_rule(localdict)[0]
                                    elif line.amount_select == 'percentage':
                                        if line.related_benefits_discounts:
                                            for li in line.related_benefits_discounts:
                                                for allowance in payslip.allowance_ids:
                                                    if line.name == allowance.name:
                                                        if li._compute_rule(localdict)[0] != allowance.amount:
                                                            amount = allowance.amount
                                                        else:
                                                            amount = li._compute_rule(localdict)[0]

                                                for deduction in payslip.deduction_ids:
                                                    if line.name == deduction.name:
                                                        if li._compute_rule(localdict)[0] != deduction.amount:
                                                            amount = (-deduction.amount)
                                                        else:
                                                            amount = li._compute_rule(localdict)[0]
                                    else:
                                        for allowance in payslip.allowance_ids:
                                            if line.name == allowance.name:
                                                if line._compute_rule(localdict)[0] != allowance.amount:
                                                    amount = allowance.amount
                                                else:
                                                    amount = line._compute_rule(localdict)[0]

                                        for deduction in payslip.deduction_ids:
                                            if line.name == deduction.name:
                                                if line._compute_rule(localdict)[0] != deduction.amount:
                                                    amount = (-deduction.amount)
                                                else:
                                                    amount = line._compute_rule(localdict)[0]

                                    # Update 29/07/2019
                                    for allow in payslip.allowance_ids:
                                        if line.name == allow.name:
                                            allow.update({
                                                'name': line.name,
                                                'code': line.code,
                                                'category_id': line.category_id.id,
                                                'contract_id': payslip.contract_id.id,
                                                'slip_id': payslip.id,
                                                'quantity': 1,
                                                'rate': 100,
                                                'salary_rule_id': line.id,
                                                'leave_request_case': True,
                                                'amount': amount
                                            })
                                    for ded in payslip.deduction_ids:
                                        if line.name == ded.name:
                                            ded.update({
                                                'name': line.name,
                                                'code': line.code,
                                                'category_id': line.category_id.id,
                                                'contract_id': payslip.contract_id.id,
                                                'slip_id': payslip.id,
                                                'quantity': 1,
                                                'rate': 100,
                                                'salary_rule_id': line.id,
                                                'leave_request_case': True,
                                                'amount': -amount
                                            })
                    elif holiday.holiday_status_id.payslip_type == 'exclusion' or (
                            holiday.holiday_status_id.payslip_type == 'reconcile' and holiday.reconcile_leave is True):

                        start_holiday = datetime.strptime(str(holiday_date_from), "%Y-%m-%d %H:%M:%S").date()
                        end_holiday = datetime.strptime(str(holiday_date_to), "%Y-%m-%d %H:%M:%S").date()
                        payroll_start = datetime.strptime(str(payslip_date_from), "%Y-%m-%d").date()
                        pyroll_end = datetime.strptime(str(payslip_date_to), "%Y-%m-%d").date()

                        if payslip.date_from >= start_holiday and payslip_date_to >= end_holiday and end_holiday >= payslip_date_from:
                            pyroll_days = relativedelta(pyroll_end, payroll_start).days + 1
                            number_of_days = relativedelta(end_holiday, payroll_start).days+ 1
                            if pyroll_days == 28:
                                number_of_days = number_of_days + 2
                            if pyroll_days == 29:
                                number_of_days = number_of_days + 1
                            if number_of_days >= 0:  # number_of_days <= 0
                                payslip.worked_days_line_ids = [(0, 0, {
                                    'name': "Exclusion or Reconcile Paid Holidays",
                                    'sequence': 2,
                                    'payslip_id': payslip.id,
                                    'code': 4,
                                    'number_of_days': number_of_days,
                                    'number_of_hours': 0.0,
                                    'contract_id': payslip.contract_id.id})]
                        elif payslip.date_to >= end_holiday and start_holiday >= payslip.date_from:
                            pyroll_days = relativedelta(pyroll_end, payroll_start).days + 1

                            number_of_days = relativedelta(pyroll_end, start_holiday).days + 1
                            if pyroll_days == 28:
                                number_of_days = number_of_days + 2
                            if pyroll_days == 29:
                                number_of_days = number_of_days + 1
                            if pyroll_days == 31:
                                number_of_days = number_of_days - 1

                            if holiday.number_of_days_temp >= 0:  # holiday.number_of_days_temp <= 0
                                payslip.worked_days_line_ids = [(0, 0, {
                                    'name': "Exclusion or Reconcile Paid Holidays",
                                    'sequence': 2,
                                    'payslip_id': payslip.id,
                                    'code': 4,
                                    'number_of_days': number_of_days,
                                    'number_of_hours': 0.0,
                                    'contract_id': payslip.contract_id.id})]
                        elif start_holiday >= payslip.date_from and payslip.date_to <= end_holiday and start_holiday <= payslip.date_to:
                            pyroll_days = relativedelta(pyroll_end, payroll_start).days + 1
                            number_of_days = relativedelta(pyroll_end, start_holiday).days + 1

                            if pyroll_days == 28:
                                number_of_days = number_of_days + 2
                            if pyroll_days == 29:
                                number_of_days = number_of_days + 1
                            if pyroll_days == 31:
                                number_of_days = number_of_days - 1

                            if number_of_days >= 0:  # number_of_days <= 0
                                payslip.worked_days_line_ids = [(0, 0, {
                                    'name': "Exclusion or Reconcile Paid Holidays",
                                    'sequence': 2,
                                    'payslip_id': payslip.id,
                                    'code': 4,
                                    'number_of_days': number_of_days,
                                    'number_of_hours': 0.0,
                                    'contract_id': payslip.contract_id.id})]
                        else:
                            if payslip.date_to <= end_holiday and start_holiday <= payslip.date_from:
                                number_of_days = relativedelta(pyroll_end, payroll_start).days + 1
                                if number_of_days == 28:
                                    number_of_days = number_of_days + 2
                                if number_of_days == 29:
                                    number_of_days = number_of_days + 1
                                if number_of_days ==31:
                                   number_of_days= number_of_days - 1
                                if number_of_days >= 0:  # number_of_days <= 0
                                    payslip.worked_days_line_ids = [(0, 0, {
                                        'name': "Exclusion or Reconcile Paid Holidays",
                                        'sequence': 2,
                                        'payslip_id': payslip.id,
                                        'code': 4,
                                        'number_of_days': number_of_days,
                                        'number_of_hours': 0.0,
                                        'contract_id': payslip.contract_id.id})]
                        if payslip.worked_days_line_ids:
                            for line in holiday.holiday_status_id.salary_rules_ids:
                                if line.amount_select == 'fix':
                                    for allowance in payslip.allowance_ids:
                                        if line.name == allowance.name:
                                            if line._compute_rule(localdict)[0] != allowance.amount:
                                                amount = allowance.amount
                                            else:
                                                amount = line._compute_rule(localdict)[0]
                                        else:
                                            amount = line._compute_rule(localdict)[0]

                                    for deduction in payslip.deduction_ids:
                                        if line.name == deduction.name:
                                            if line._compute_rule(localdict)[0] != deduction.amount:
                                                amount = (-deduction.amount)
                                            else:
                                                amount = line._compute_rule(localdict)[0]
                                elif line.amount_select == 'percentage':
                                    if line.related_benefits_discounts:
                                        for li in line.related_benefits_discounts:
                                            for allowance in payslip.allowance_ids:
                                                if line.name == allowance.name:
                                                    if li._compute_rule(localdict)[0] != allowance.amount:
                                                        amount = allowance.amount
                                                    else:
                                                        amount = li._compute_rule(localdict)[0]

                                            for deduction in payslip.deduction_ids:
                                                if line.name == deduction.name:
                                                    if li._compute_rule(localdict)[0] != deduction.amount:
                                                        amount = (-deduction.amount)
                                                    else:
                                                        amount = li._compute_rule(localdict)[0]
                                else:
                                    for allowance in payslip.allowance_ids:
                                        if line.name == allowance.name:
                                            if line._compute_rule(localdict)[0] != allowance.amount:
                                                amount = allowance.amount
                                            else:
                                                amount = line._compute_rule(localdict)[0]

                                    for deduction in payslip.deduction_ids:
                                        if line.name == deduction.name:
                                            if line._compute_rule(localdict)[0] != deduction.amount:
                                                amount = (-deduction.amount)
                                            else:
                                                amount = line._compute_rule(localdict)[0]

                                for allow in payslip.allowance_ids:
                                    if line.name == allow.name:
                                        allow.update({
                                            'name': line.name,
                                            'code': line.code,
                                            'category_id': line.category_id.id,
                                            'contract_id': payslip.contract_id.id,
                                            'slip_id': payslip.id,
                                            'quantity': 1,
                                            'rate': 100,
                                            'salary_rule_id': line.id,
                                            'leave_request_case': True,
                                            'amount': amount
                                        })
                                for ded in payslip.deduction_ids:
                                    if line.name == ded.name:
                                        ded.update({
                                            'name': line.name,
                                            'code': line.code,
                                            'category_id': line.category_id.id,
                                            'contract_id': payslip.contract_id.id,
                                            'slip_id': payslip.id,
                                            'quantity': 1,
                                            'rate': 100,
                                            'salary_rule_id': line.id,
                                            'leave_request_case': True,
                                            'amount': -amount
                                        })
            payslip.allowance_ids._compute_total()
            payslip.deduction_ids._compute_total()
            for pay in payslip:
                if pay.total_sum < 0:
                    raise exceptions.Warning(_("Salary is less than 0 this month for the following employees \n %s") % (
                        pay.employee_id.name))

        self.write({'state': 'computed'})
        return True

    # Override function get_payslip_lines
    @api.model
    def _get_payslip_lines(self, contract_ids, payslip_id):
        def _sum_salary_rule_category(localdict, category, amount):
            if category.parent_id:
                localdict = _sum_salary_rule_category(localdict, category.parent_id, amount)
            localdict['categories'].dict[category.code] = category.code in localdict['categories'].dict and \
                                                          localdict['categories'].dict[category.code] + amount or amount
            return localdict

        class BrowsableObject(object):
            def __init__(self, employee_id, dict, env):
                self.employee_id = employee_id
                self.dict = dict
                self.env = env

            def __getattr__(self, attr):
                return attr in self.dict and self.dict.__getitem__(attr) or 0.0

        class InputLine(BrowsableObject):
            """a class that will be used into the python code, mainly for usability purposes"""

            def sum(self, code, from_date, to_date=None):
                if to_date is None:
                    to_date = fields.Date.today()
                self.env.cr.execute("""
                       SELECT sum(amount) as sum
                       FROM hr_payslip as hp, hr_payslip_input as pi
                       WHERE hp.employee_id = %s AND hp.state = 'done'
                       AND hp.date_from >= %s AND hp.date_to <= %s AND hp.id = pi.payslip_id AND pi.code = %s""",
                                    (self.employee_id, from_date, to_date, code))
                return self.env.cr.fetchone()[0] or 0.0

        class WorkedDays(BrowsableObject):
            """a class that will be used into the python code, mainly for usability purposes"""

            def _sum(self, code, from_date, to_date=None):
                if to_date is None:
                    to_date = fields.Date.today()
                self.env.cr.execute("""
                       SELECT sum(number_of_days) as number_of_days, sum(number_of_hours) as number_of_hours
                       FROM hr_payslip as hp, hr_payslip_worked_days as pi
                       WHERE hp.employee_id = %s AND hp.state = 'done'
                       AND hp.date_from >= %s AND hp.date_to <= %s AND hp.id = pi.payslip_id AND pi.code = %s""",
                                    (self.employee_id, from_date, to_date, code))
                return self.env.cr.fetchone()

            def sum(self, code, from_date, to_date=None):
                res = self._sum(code, from_date, to_date)
                return res and res[0] or 0.0

            def sum_hours(self, code, from_date, to_date=None):
                res = self._sum(code, from_date, to_date)
                return res and res[1] or 0.0

        class Payslips(BrowsableObject):
            """a class that will be used into the python code, mainly for usability purposes"""

            def sum(self, code, from_date, to_date=None):
                if to_date is None:
                    to_date = fields.Date.today()
                self.env.cr.execute("""SELECT sum(case when hp.credit_note = False then (pl.total) else (-pl.total) end)
                               FROM hr_payslip as hp, hr_payslip_line as pl
                               WHERE hp.employee_id = %s AND hp.state = 'done'
                               AND hp.date_from >= %s AND hp.date_to <= %s AND hp.id = pl.slip_id AND pl.code = %s""",
                                    (self.employee_id, from_date, to_date, code))
                res = self.env.cr.fetchone()
                return res and res[0] or 0.0

        # we keep a dict with the result because a value can be overwritten by another rule with the same code
        result_dict, rules_dict, worked_days_dict, inputs_dict = {}, {}, {}, {}
        blacklist = []
        payslip = self.env['hr.payslip'].browse(payslip_id)
        for worked_days_line in payslip.worked_days_line_ids:
            worked_days_dict[worked_days_line.code] = worked_days_line
        for input_line in payslip.input_line_ids:
            inputs_dict[input_line.code] = input_line

        categories = BrowsableObject(payslip.employee_id.id, {}, self.env)
        inputs = InputLine(payslip.employee_id.id, inputs_dict, self.env)
        worked_days = WorkedDays(payslip.employee_id.id, worked_days_dict, self.env)
        payslips = Payslips(payslip.employee_id.id, payslip, self.env)
        rules = BrowsableObject(payslip.employee_id.id, rules_dict, self.env)

        baselocaldict = {'categories': categories, 'rules': rules, 'payslip': payslips, 'worked_days': worked_days,
                         'inputs': inputs}
        # get the ids of the structures on the contracts and their parent id as well
        contracts = self.env['hr.contract'].browse(contract_ids)
        if len(contracts) == 1 and payslip.struct_id:
            structure_ids = list(set(payslip.contract_id.salary_scale.ids))
        else:
            structure_ids = contracts.get_all_structures()
        # get the rules of the structure and their children
        rule_ids = self.env['hr.payroll.structure'].browse(structure_ids).get_all_rules()
        # run the rules by sequence
        sorted_rule_ids = [id for id, sequence in sorted(rule_ids, key=lambda x: x[1])]
        sorted_rules = self.env['hr.salary.rule'].browse(sorted_rule_ids)

        for contract in contracts:
            employee = contract.employee_id
            localdict = dict(baselocaldict, payslip=payslip, employee=employee, contract=contract)
            if contract.contractor_type.salary_type == 'scale':
                for rule in sorted_rules:
                    key1 = rule.code + '-' + str(contract.id)
                    localdict['result'] = None
                    localdict['result_qty'] = 1.0
                    localdict['result_rate'] = 100
                    # check if the rule can be applied
                    if rule._satisfy_condition(localdict) and rule.id not in blacklist:
                        if payslip.contract_id.advantages:
                            for advantage_rule in payslip.contract_id.advantages:
                                date1 = datetime.strptime(str(advantage_rule.date_from), "%Y-%m-%d")
                                key = str(advantage_rule.benefits_discounts.code) + '-' + str(contract.id)
                                if advantage_rule.date_to:
                                    date2 = datetime.strptime(str(advantage_rule.date_to), "%Y-%m-%d")
                                    if (datetime.strptime(str(payslip.date_from), "%Y-%m-%d") >= date1
                                        and date2 >= datetime.strptime(str(payslip.date_to), "%Y-%m-%d")) \
                                            or date2 >= datetime.strptime(str(payslip.date_from), "%Y-%m-%d") >= date1 \
                                            or date2 >= datetime.strptime(str(payslip.date_to), "%Y-%m-%d") >= date1 \
                                            or (datetime.strptime(str(payslip.date_to), "%Y-%m-%d") >= date1
                                                and date2 >= datetime.strptime(str(payslip.date_from), "%Y-%m-%d")):

                                        if advantage_rule.benefits_discounts.name not in sorted_rules:
                                            amount, qty, rate = rule._compute_rule(localdict)
                                            previous_amount = rule.code in localdict and localdict[
                                                rule.code] or 0.0
                                            tot_rule = amount * qty * rate / 100.0
                                            localdict[rule.code] = tot_rule
                                            rules_dict[rule.code] = rule
                                            localdict = _sum_salary_rule_category(localdict, rule.category_id,
                                                                                  tot_rule - previous_amount)
                                            # create/overwrite the rule in the temporary results
                                            if amount != 0:
                                                result_dict[key1] = {
                                                    'salary_rule_id': rule.id,
                                                    'contract_id': contract.id,
                                                    'name': rule.name,
                                                    'code': rule.code,
                                                    'category_id': rule.category_id.id,
                                                    'amount_select': rule.amount_select,
                                                    'amount_fix': rule.amount_fix,
                                                    'amount_python_compute': rule.amount_python_compute,
                                                    'amount_percentage': rule.amount_percentage,
                                                    'register_id': rule.register_id.id,
                                                    'amount': amount,
                                                    'employee_id': contract.employee_id.id,
                                                    'quantity': qty,
                                                    'rate': rate}

                                            if advantage_rule.type == 'customize':
                                                amount = advantage_rule.amount
                                                qty, rate = 1, 100.0
                                                previous_amount = advantage_rule.benefits_discounts.code in localdict and \
                                                                  localdict[
                                                                      advantage_rule.benefits_discounts.code] or 0.0
                                                tot_rule = amount * qty * rate / 100.0
                                                localdict[advantage_rule.benefits_discounts.code] = tot_rule
                                                rules_dict[advantage_rule.benefits_discounts.code] = advantage_rule
                                                # sum the amount for its salary category
                                                localdict = _sum_salary_rule_category(localdict,
                                                                                      advantage_rule.benefits_discounts.category_id,
                                                                                      tot_rule - previous_amount)
                                                # create/overwrite the rule in the temporary results
                                                result_dict[key] = {
                                                    'salary_rule_id': advantage_rule.benefits_discounts.id,
                                                    'contract_id': contract.id,
                                                    'name': advantage_rule.benefits_discounts.name,
                                                    'code': advantage_rule.benefits_discounts.code,
                                                    'category_id': advantage_rule.benefits_discounts.category_id.id,
                                                    'amount_select': advantage_rule.benefits_discounts.amount_select,
                                                    'amount_fix': advantage_rule.benefits_discounts.amount_fix,
                                                    'amount_python_compute': advantage_rule.benefits_discounts.amount_python_compute,
                                                    'amount_percentage': advantage_rule.benefits_discounts.amount_percentage,
                                                    'register_id': advantage_rule.benefits_discounts.register_id.id,
                                                    'amount': amount,
                                                    'employee_id': contract.employee_id.id,
                                                    'quantity': qty,
                                                    'rate': rate}
                                            elif advantage_rule.type == 'exception':
                                                total = advantage_rule.benefits_discounts._compute_rule(localdict)[0]
                                                if total == advantage_rule.amount or total == 0.0:
                                                    amount, qty, rate = 0.0, 0, 0.0
                                                    previous_amount = advantage_rule.benefits_discounts.code in localdict and \
                                                                      localdict[
                                                                          advantage_rule.benefits_discounts.code] or 0.0
                                                    tot_rule = amount * qty * rate / 100.0
                                                    localdict[advantage_rule.benefits_discounts.code] = tot_rule
                                                    rules_dict[advantage_rule.benefits_discounts.code] = advantage_rule
                                                    # sum the amount for its salary category
                                                    localdict = _sum_salary_rule_category(localdict,
                                                                                          advantage_rule.benefits_discounts.category_id,
                                                                                          tot_rule - previous_amount)
                                                    # create/overwrite the rule in the temporary results
                                                    result_dict[key] = {
                                                        'salary_rule_id': advantage_rule.benefits_discounts.id,
                                                        'contract_id': contract.id,
                                                        'name': advantage_rule.benefits_discounts.name,
                                                        'code': advantage_rule.benefits_discounts.code,
                                                        'category_id': advantage_rule.benefits_discounts.category_id.id,
                                                        'amount_select': advantage_rule.benefits_discounts.amount_select,
                                                        'amount_fix': advantage_rule.benefits_discounts.amount_fix,
                                                        'amount_python_compute': advantage_rule.benefits_discounts.amount_python_compute,
                                                        'amount_percentage': advantage_rule.benefits_discounts.amount_percentage,
                                                        'register_id': advantage_rule.benefits_discounts.register_id.id,
                                                        'amount': amount,
                                                        'employee_id': contract.employee_id.id,
                                                        'quantity': qty,
                                                        'rate': rate}
                                                elif total <= advantage_rule.amount:
                                                    raise UserError(
                                                        _(
                                                            'The amount you put is greater than fact value of this Salary rule'))
                                                else:
                                                    amount = total - advantage_rule.amount  # update 21/04/2019
                                                    qty, rate = 1, 100.0
                                                    previous_amount = advantage_rule.benefits_discounts.code in localdict and \
                                                                      localdict[
                                                                          advantage_rule.benefits_discounts.code] or 0.0
                                                    tot_rule = amount * qty * rate / 100.0
                                                    localdict[advantage_rule.benefits_discounts.code] = tot_rule
                                                    rules_dict[advantage_rule.benefits_discounts.code] = advantage_rule
                                                    # sum the amount for its salary category
                                                    localdict = _sum_salary_rule_category(localdict,
                                                                                          advantage_rule.benefits_discounts.category_id,
                                                                                          tot_rule - previous_amount)
                                                    # create/overwrite the rule in the temporary results
                                                    result_dict[key] = {
                                                        'salary_rule_id': advantage_rule.benefits_discounts.id,
                                                        'contract_id': contract.id,
                                                        'name': advantage_rule.benefits_discounts.name,
                                                        'code': advantage_rule.benefits_discounts.code,
                                                        'category_id': advantage_rule.benefits_discounts.category_id.id,
                                                        'amount_select': advantage_rule.benefits_discounts.amount_select,
                                                        'amount_fix': advantage_rule.benefits_discounts.amount_fix,
                                                        'amount_python_compute': advantage_rule.benefits_discounts.amount_python_compute,
                                                        'amount_percentage': advantage_rule.benefits_discounts.amount_percentage,
                                                        'register_id': advantage_rule.benefits_discounts.register_id.id,
                                                        'amount': amount,
                                                        'employee_id': contract.employee_id.id,
                                                        'quantity': qty,
                                                        'rate': rate}
                                                    advantage_rule.done = False
                                        else:
                                            amount, qty, rate = rule._compute_rule(localdict)
                                            previous_amount = rule.code in localdict and localdict[rule.code] or 0.0
                                            tot_rule = amount * qty * rate / 100.0
                                            localdict[rule.code] = tot_rule
                                            rules_dict[rule.code] = rule
                                            localdict = _sum_salary_rule_category(localdict, rule.category_id,
                                                                                  tot_rule - previous_amount)
                                            # create/overwrite the rule in the temporary results
                                            if amount != 0:
                                                result_dict[key1] = {
                                                    'salary_rule_id': rule.id,
                                                    'contract_id': contract.id,
                                                    'name': rule.name,
                                                    'code': rule.code,
                                                    'category_id': rule.category_id.id,
                                                    'amount_select': rule.amount_select,
                                                    'amount_fix': rule.amount_fix,
                                                    'amount_python_compute': rule.amount_python_compute,
                                                    'amount_percentage': rule.amount_percentage,
                                                    'register_id': rule.register_id.id,
                                                    'amount': amount,
                                                    'employee_id': contract.employee_id.id,
                                                    'quantity': qty,
                                                    'rate': rate}
                                    else:
                                        if date2 <= datetime.strptime(str(payslip.date_from), "%Y-%m-%d"):
                                            amount, qty, rate = rule._compute_rule(localdict)
                                            previous_amount = rule.code in localdict and localdict[rule.code] or 0.0
                                            tot_rule = amount * qty * rate / 100.0
                                            localdict[rule.code] = tot_rule
                                            rules_dict[rule.code] = rule
                                            localdict = _sum_salary_rule_category(localdict, rule.category_id,
                                                                                  tot_rule - previous_amount)
                                            # create/overwrite the rule in the temporary results
                                            if amount != 0:
                                                result_dict[key1] = {
                                                    'salary_rule_id': rule.id,
                                                    'contract_id': contract.id,
                                                    'name': rule.name,
                                                    'code': rule.code,
                                                    'category_id': rule.category_id.id,
                                                    'amount_select': rule.amount_select,
                                                    'amount_fix': rule.amount_fix,
                                                    'amount_python_compute': rule.amount_python_compute,
                                                    'amount_percentage': rule.amount_percentage,
                                                    'register_id': rule.register_id.id,
                                                    'amount': amount,
                                                    'employee_id': contract.employee_id.id,
                                                    'quantity': qty,
                                                    'rate': rate}
                                else:
                                    if date1 <= datetime.strptime(str(payslip.date_from),
                                                                  "%Y-%m-%d") or date1 <= datetime.strptime(
                                        str(payslip.date_to), "%Y-%m-%d"):
                                        if advantage_rule.benefits_discounts.name not in sorted_rules:
                                            amount, qty, rate = rule._compute_rule(localdict)
                                            previous_amount = rule.code in localdict and localdict[rule.code] or 0.0
                                            tot_rule = amount * qty * rate / 100.0
                                            localdict[rule.code] = tot_rule
                                            rules_dict[rule.code] = rule
                                            localdict = _sum_salary_rule_category(localdict, rule.category_id,
                                                                                  tot_rule - previous_amount)
                                            # create/overwrite the rule in the temporary results
                                            if amount != 0:
                                                result_dict[key1] = {
                                                    'salary_rule_id': rule.id,
                                                    'contract_id': contract.id,
                                                    'name': rule.name,
                                                    'code': rule.code,
                                                    'category_id': rule.category_id.id,
                                                    'amount_select': rule.amount_select,
                                                    'amount_fix': rule.amount_fix,
                                                    'amount_python_compute': rule.amount_python_compute,
                                                    'amount_percentage': rule.amount_percentage,
                                                    'register_id': rule.register_id.id,
                                                    'amount': amount,
                                                    'employee_id': contract.employee_id.id,
                                                    'quantity': qty,
                                                    'rate': rate}
                                            # To Doooooooooooooo #if
                                            # if rule.name == advantage_rule.benefits_discounts.name:
                                            if advantage_rule.type == 'customize':
                                                amount = advantage_rule.amount
                                                qty, rate = 1, 100.0
                                                previous_amount = advantage_rule.benefits_discounts.code in localdict and \
                                                                  localdict[
                                                                      advantage_rule.benefits_discounts.code] or 0.0
                                                tot_rule = amount * qty * rate / 100.0
                                                localdict[advantage_rule.benefits_discounts.code] = tot_rule
                                                rules_dict[advantage_rule.benefits_discounts.code] = advantage_rule
                                                # sum the amount for its salary category
                                                localdict = _sum_salary_rule_category(localdict,
                                                                                      advantage_rule.benefits_discounts.category_id,
                                                                                      tot_rule - previous_amount)
                                                # create/overwrite the rule in the temporary results
                                                result_dict[key] = {
                                                    'salary_rule_id': advantage_rule.benefits_discounts.id,
                                                    'contract_id': contract.id,
                                                    'name': advantage_rule.benefits_discounts.name,
                                                    'code': advantage_rule.benefits_discounts.code,
                                                    'category_id': advantage_rule.benefits_discounts.category_id.id,
                                                    'amount_select': advantage_rule.benefits_discounts.amount_select,
                                                    'amount_fix': advantage_rule.benefits_discounts.amount_fix,
                                                    'amount_python_compute': advantage_rule.benefits_discounts.amount_python_compute,
                                                    'amount_percentage': advantage_rule.benefits_discounts.amount_percentage,
                                                    'register_id': advantage_rule.benefits_discounts.register_id.id,
                                                    'amount': amount,
                                                    'employee_id': contract.employee_id.id,
                                                    'quantity': qty,
                                                    'rate': rate}
                                            elif advantage_rule.type == 'exception':
                                                total = advantage_rule.benefits_discounts._compute_rule(localdict)[
                                                    0]
                                                if total == advantage_rule.amount or total == 0.0:
                                                    amount, qty, rate = 0.0, 0, 0.0
                                                    previous_amount = advantage_rule.benefits_discounts.code in localdict and \
                                                                      localdict[
                                                                          advantage_rule.benefits_discounts.code] or 0.0
                                                    tot_rule = amount * qty * rate / 100.0
                                                    localdict[advantage_rule.benefits_discounts.code] = tot_rule
                                                    rules_dict[
                                                        advantage_rule.benefits_discounts.code] = advantage_rule
                                                    # sum the amount for its salary category
                                                    localdict = _sum_salary_rule_category(localdict,
                                                                                          advantage_rule.benefits_discounts.category_id,
                                                                                          tot_rule - previous_amount)
                                                    # create/overwrite the rule in the temporary results
                                                    result_dict[key] = {
                                                        'salary_rule_id': advantage_rule.benefits_discounts.id,
                                                        'contract_id': contract.id,
                                                        'name': advantage_rule.benefits_discounts.name,
                                                        'code': advantage_rule.benefits_discounts.code,
                                                        'category_id': advantage_rule.benefits_discounts.category_id.id,
                                                        'amount_select': advantage_rule.benefits_discounts.amount_select,
                                                        'amount_fix': advantage_rule.benefits_discounts.amount_fix,
                                                        'amount_python_compute': advantage_rule.benefits_discounts.amount_python_compute,
                                                        'amount_percentage': advantage_rule.benefits_discounts.amount_percentage,
                                                        'register_id': advantage_rule.benefits_discounts.register_id.id,
                                                        'amount': amount,
                                                        'employee_id': contract.employee_id.id,
                                                        'quantity': qty,
                                                        'rate': rate}
                                                elif total <= advantage_rule.amount:
                                                    raise UserError(
                                                        _(
                                                            'The amount you put is greater than fact value of this Salary rule'))
                                                else:
                                                    amount = total - advantage_rule.amount  # update 21/04/2019
                                                    qty, rate = 1, 100.0
                                                    previous_amount = advantage_rule.benefits_discounts.code in localdict and \
                                                                      localdict[
                                                                          advantage_rule.benefits_discounts.code] or 0.0
                                                    tot_rule = amount * qty * rate / 100.0
                                                    localdict[advantage_rule.benefits_discounts.code] = tot_rule
                                                    rules_dict[
                                                        advantage_rule.benefits_discounts.code] = advantage_rule
                                                    # sum the amount for its salary category
                                                    localdict = _sum_salary_rule_category(localdict,
                                                                                          advantage_rule.benefits_discounts.category_id,
                                                                                          tot_rule - previous_amount)
                                                    # create/overwrite the rule in the temporary results
                                                    result_dict[key] = {
                                                        'salary_rule_id': advantage_rule.benefits_discounts.id,
                                                        'contract_id': contract.id,
                                                        'name': advantage_rule.benefits_discounts.name,
                                                        'code': advantage_rule.benefits_discounts.code,
                                                        'category_id': advantage_rule.benefits_discounts.category_id.id,
                                                        'amount_select': advantage_rule.benefits_discounts.amount_select,
                                                        'amount_fix': advantage_rule.benefits_discounts.amount_fix,
                                                        'amount_python_compute': advantage_rule.benefits_discounts.amount_python_compute,
                                                        'amount_percentage': advantage_rule.benefits_discounts.amount_percentage,
                                                        'register_id': advantage_rule.benefits_discounts.register_id.id,
                                                        'amount': amount,
                                                        'employee_id': contract.employee_id.id,
                                                        'quantity': qty,
                                                        'rate': rate}
                                    else:
                                        amount, qty, rate = rule._compute_rule(localdict)
                                        previous_amount = rule.code in localdict and localdict[rule.code] or 0.0
                                        tot_rule = amount * qty * rate / 100.0
                                        localdict[rule.code] = tot_rule
                                        rules_dict[rule.code] = rule
                                        localdict = _sum_salary_rule_category(localdict, rule.category_id,
                                                                              tot_rule - previous_amount)
                                        # create/overwrite the rule in the temporary results
                                        if amount != 0:
                                            result_dict[key1] = {
                                                'salary_rule_id': rule.id,
                                                'contract_id': contract.id,
                                                'name': rule.name,
                                                'code': rule.code,
                                                'category_id': rule.category_id.id,
                                                'amount_select': rule.amount_select,
                                                'amount_fix': rule.amount_fix,
                                                'amount_python_compute': rule.amount_python_compute,
                                                'amount_percentage': rule.amount_percentage,
                                                'register_id': rule.register_id.id,
                                                'amount': amount,
                                                'employee_id': contract.employee_id.id,
                                                'quantity': qty,
                                                'rate': rate}
                                advantage_rule.write({'done': True})
                        else:
                            amount, qty, rate = rule._compute_rule(localdict)
                            previous_amount = rule.code in localdict and localdict[rule.code] or 0.0
                            tot_rule = amount * qty * rate / 100.0
                            localdict[rule.code] = tot_rule
                            rules_dict[rule.code] = rule
                            localdict = _sum_salary_rule_category(localdict, rule.category_id,
                                                                  tot_rule - previous_amount)
                            # create/overwrite the rule in the temporary results
                            if amount != 0:
                                result_dict[key1] = {
                                    'salary_rule_id': rule.id,
                                    'contract_id': contract.id,
                                    'name': rule.name,
                                    'code': rule.code,
                                    'category_id': rule.category_id.id,
                                    'amount_select': rule.amount_select,
                                    'amount_fix': rule.amount_fix,
                                    'amount_python_compute': rule.amount_python_compute,
                                    'amount_percentage': rule.amount_percentage,
                                    'register_id': rule.register_id.id,
                                    'amount': amount,
                                    'employee_id': contract.employee_id.id,
                                    'quantity': qty,
                                    'rate': rate}
                    else:
                        blacklist += [id for id, seq in rule._recursive_search_of_rules()]

                if payslip.contract_id.salary_level.benefits_discounts_ids:
                    level_structure_ids = list(set(payslip.contract_id.salary_level.ids))
                    level_rule_ids = self.env['hr.payroll.structure'].browse(level_structure_ids).get_all_rules()
                    level_sorted_rule_ids = [id for id, sequence in sorted(level_rule_ids, key=lambda x: x[1])]
                    level_sorted_rules = self.env['hr.salary.rule'].browse(level_sorted_rule_ids)
                    for rule in level_sorted_rules:
                        key = rule.code + '-' + str(contract.id)
                        localdict['result'] = None
                        localdict['result_qty'] = 1.0
                        localdict['result_rate'] = 100
                        # check if the rule can be applied
                        if rule._satisfy_condition(localdict) and rule.id not in blacklist:
                            amount, qty, rate = rule._compute_rule(localdict)
                            if qty == 0:
                                qty = 1
                            previous_amount = rule.code in localdict and localdict[rule.code] or 0.0
                            tot_rule = amount * qty * rate / 100.0
                            localdict[rule.code] = tot_rule
                            rules_dict[rule.code] = rule
                            localdict = _sum_salary_rule_category(localdict, rule.category_id,
                                                                  tot_rule - previous_amount)
                            # create/overwrite the rule in the temporary results
                            result_dict[key] = {
                                'salary_rule_id': rule.id,
                                'contract_id': contract.id,
                                'name': rule.name,
                                'code': rule.code,
                                'category_id': rule.category_id.id,
                                'amount_select': rule.amount_select,
                                'amount_fix': rule.amount_fix,
                                'amount_python_compute': rule.amount_python_compute,
                                'amount_percentage': rule.amount_percentage,
                                'register_id': rule.register_id.id,
                                'amount': amount,
                                'employee_id': contract.employee_id.id,
                                'quantity': qty,
                                'rate': rate}

                            for advantage_rule in payslip.contract_id.advantages:
                                if advantage_rule.benefits_discounts.name == rule.name:
                                    if advantage_rule.type == 'customize':
                                        amount = advantage_rule.amount + amount
                                        qty, rate = 1, 100.0
                                        previous_amount = advantage_rule.benefits_discounts.code in localdict and \
                                                          localdict[
                                                              advantage_rule.benefits_discounts.code] or 0.0
                                        tot_rule = amount * qty * rate / 100.0
                                        localdict[advantage_rule.benefits_discounts.code] = tot_rule
                                        rules_dict[advantage_rule.benefits_discounts.code] = advantage_rule
                                        # sum the amount for its salary category
                                        localdict = _sum_salary_rule_category(localdict,
                                                                              advantage_rule.benefits_discounts.category_id,
                                                                              tot_rule - previous_amount)
                                        # create/overwrite the rule in the temporary results
                                        result_dict[key] = {
                                            'salary_rule_id': advantage_rule.benefits_discounts.id,
                                            'contract_id': contract.id,
                                            'name': advantage_rule.benefits_discounts.name,
                                            'code': advantage_rule.benefits_discounts.code,
                                            'category_id': advantage_rule.benefits_discounts.category_id.id,
                                            'amount_select': advantage_rule.benefits_discounts.amount_select,
                                            'amount_fix': advantage_rule.benefits_discounts.amount_fix,
                                            'amount_python_compute': advantage_rule.benefits_discounts.amount_python_compute,
                                            'amount_percentage': advantage_rule.benefits_discounts.amount_percentage,
                                            'register_id': advantage_rule.benefits_discounts.register_id.id,
                                            'amount': amount,
                                            'employee_id': contract.employee_id.id,
                                            'quantity': qty,
                                            'rate': rate}
                                    if advantage_rule.type == 'exception':
                                        total = advantage_rule.benefits_discounts._compute_rule(localdict)[0]
                                        if total == advantage_rule.amount or total == 0.0:
                                            amount, qty, rate = 0.0, 0, 0.0
                                            previous_amount = advantage_rule.benefits_discounts.code in localdict and \
                                                              localdict[
                                                                  advantage_rule.benefits_discounts.code] or 0.0
                                            tot_rule = amount * qty * rate / 100.0
                                            localdict[advantage_rule.benefits_discounts.code] = tot_rule
                                            rules_dict[advantage_rule.benefits_discounts.code] = advantage_rule
                                            # sum the amount for its salary category
                                            localdict = _sum_salary_rule_category(localdict,
                                                                                  advantage_rule.benefits_discounts.category_id,
                                                                                  tot_rule - previous_amount)
                                            # create/overwrite the rule in the temporary results
                                            result_dict[key] = {
                                                'salary_rule_id': advantage_rule.benefits_discounts.id,
                                                'contract_id': contract.id,
                                                'name': advantage_rule.benefits_discounts.name,
                                                'code': advantage_rule.benefits_discounts.code,
                                                'category_id': advantage_rule.benefits_discounts.category_id.id,
                                                'amount_select': advantage_rule.benefits_discounts.amount_select,
                                                'amount_fix': advantage_rule.benefits_discounts.amount_fix,
                                                'amount_python_compute': advantage_rule.benefits_discounts.amount_python_compute,
                                                'amount_percentage': advantage_rule.benefits_discounts.amount_percentage,
                                                'register_id': advantage_rule.benefits_discounts.register_id.id,
                                                'amount': amount,
                                                'employee_id': contract.employee_id.id,
                                                'quantity': qty,
                                                'rate': rate}
                                        elif total <= advantage_rule.amount:
                                            raise UserError(
                                                _(
                                                    'The amount you put is greater than fact value of this Salary rule'))
                                        else:
                                            amount = total - advantage_rule.amount  # update 21/04/2019
                                            qty, rate = 1, 100.0
                                            previous_amount = advantage_rule.benefits_discounts.code in localdict and \
                                                              localdict[
                                                                  advantage_rule.benefits_discounts.code] or 0.0
                                            tot_rule = amount * qty * rate / 100.0
                                            localdict[advantage_rule.benefits_discounts.code] = tot_rule
                                            rules_dict[advantage_rule.benefits_discounts.code] = advantage_rule
                                            # sum the amount for its salary category
                                            localdict = _sum_salary_rule_category(localdict,
                                                                                  advantage_rule.benefits_discounts.category_id,
                                                                                  tot_rule - previous_amount)
                                            # create/overwrite the rule in the temporary results
                                            result_dict[key] = {
                                                'salary_rule_id': advantage_rule.benefits_discounts.id,
                                                'contract_id': contract.id,
                                                'name': advantage_rule.benefits_discounts.name,
                                                'code': advantage_rule.benefits_discounts.code,
                                                'category_id': advantage_rule.benefits_discounts.category_id.id,
                                                'amount_select': advantage_rule.benefits_discounts.amount_select,
                                                'amount_fix': advantage_rule.benefits_discounts.amount_fix,
                                                'amount_python_compute': advantage_rule.benefits_discounts.amount_python_compute,
                                                'amount_percentage': advantage_rule.benefits_discounts.amount_percentage,
                                                'register_id': advantage_rule.benefits_discounts.register_id.id,
                                                'amount': amount,
                                                'employee_id': contract.employee_id.id,
                                                'quantity': qty,
                                                'rate': rate}
                        else:
                            blacklist += [id for id, seq in rule._recursive_search_of_rules()]

                if payslip.contract_id.salary_group.benefits_discounts_ids:
                    group_structure_ids = list(set(payslip.contract_id.salary_group.ids))
                    group_rule_ids = self.env['hr.payroll.structure'].browse(group_structure_ids).get_all_rules()
                    group_sorted_rule_ids = [id for id, sequence in sorted(group_rule_ids, key=lambda x: x[1])]
                    group_sorted_rules = self.env['hr.salary.rule'].browse(group_sorted_rule_ids)
                    for rule in group_sorted_rules:
                        key = rule.code + '-' + str(contract.id)
                        localdict['result'] = None
                        localdict['result_qty'] = 1.0
                        localdict['result_rate'] = 100
                        # check if the rule can be applied
                        if rule._satisfy_condition(localdict) and rule.id not in blacklist:
                            amount, qty, rate = rule._compute_rule(localdict)
                            previous_amount = rule.code in localdict and localdict[rule.code] or 0.0
                            tot_rule = amount * qty * rate / 100.0
                            localdict[rule.code] = tot_rule
                            rules_dict[rule.code] = rule
                            localdict = _sum_salary_rule_category(localdict, rule.category_id,
                                                                  tot_rule - previous_amount)
                            # create/overwrite the rule in the temporary results
                            result_dict[key] = {
                                'salary_rule_id': rule.id,
                                'contract_id': contract.id,
                                'name': rule.name,
                                'code': rule.code,
                                'category_id': rule.category_id.id,
                                'amount_select': rule.amount_select,
                                'amount_fix': rule.amount_fix,
                                'amount_python_compute': rule.amount_python_compute,
                                'amount_percentage': rule.amount_percentage,
                                'register_id': rule.register_id.id,
                                'amount': amount,
                                'employee_id': contract.employee_id.id,
                                'quantity': qty,
                                'rate': rate}

                            for advantage_rule in payslip.contract_id.advantages:
                                if advantage_rule.benefits_discounts.name == rule.name:
                                    if advantage_rule.type == 'customize':
                                        amount = advantage_rule.amount + amount
                                        qty, rate = 1, 100.0
                                        previous_amount = advantage_rule.benefits_discounts.code in localdict and \
                                                          localdict[
                                                              advantage_rule.benefits_discounts.code] or 0.0
                                        tot_rule = amount * qty * rate / 100.0
                                        localdict[advantage_rule.benefits_discounts.code] = tot_rule
                                        rules_dict[advantage_rule.benefits_discounts.code] = advantage_rule
                                        # sum the amount for its salary category
                                        localdict = _sum_salary_rule_category(localdict,
                                                                              advantage_rule.benefits_discounts.category_id,
                                                                              tot_rule - previous_amount)
                                        # create/overwrite the rule in the temporary results
                                        result_dict[key] = {
                                            'salary_rule_id': advantage_rule.benefits_discounts.id,
                                            'contract_id': contract.id,
                                            'name': advantage_rule.benefits_discounts.name,
                                            'code': advantage_rule.benefits_discounts.code,
                                            'category_id': advantage_rule.benefits_discounts.category_id.id,
                                            'amount_select': advantage_rule.benefits_discounts.amount_select,
                                            'amount_fix': advantage_rule.benefits_discounts.amount_fix,
                                            'amount_python_compute': advantage_rule.benefits_discounts.amount_python_compute,
                                            'amount_percentage': advantage_rule.benefits_discounts.amount_percentage,
                                            'register_id': advantage_rule.benefits_discounts.register_id.id,
                                            'amount': amount,
                                            'employee_id': contract.employee_id.id,
                                            'quantity': qty,
                                            'rate': rate}
                                    if advantage_rule.type == 'exception':
                                        total = advantage_rule.benefits_discounts._compute_rule(localdict)[0]
                                        if total == advantage_rule.amount or total == 0.0:
                                            amount, qty, rate = 0.0, 0, 0.0
                                            previous_amount = advantage_rule.benefits_discounts.code in localdict and \
                                                              localdict[
                                                                  advantage_rule.benefits_discounts.code] or 0.0
                                            tot_rule = amount * qty * rate / 100.0
                                            localdict[advantage_rule.benefits_discounts.code] = tot_rule
                                            rules_dict[advantage_rule.benefits_discounts.code] = advantage_rule
                                            # sum the amount for its salary category
                                            localdict = _sum_salary_rule_category(localdict,
                                                                                  advantage_rule.benefits_discounts.category_id,
                                                                                  tot_rule - previous_amount)
                                            # create/overwrite the rule in the temporary results
                                            result_dict[key] = {
                                                'salary_rule_id': advantage_rule.benefits_discounts.id,
                                                'contract_id': contract.id,
                                                'name': advantage_rule.benefits_discounts.name,
                                                'code': advantage_rule.benefits_discounts.code,
                                                'category_id': advantage_rule.benefits_discounts.category_id.id,
                                                'amount_select': advantage_rule.benefits_discounts.amount_select,
                                                'amount_fix': advantage_rule.benefits_discounts.amount_fix,
                                                'amount_python_compute': advantage_rule.benefits_discounts.amount_python_compute,
                                                'amount_percentage': advantage_rule.benefits_discounts.amount_percentage,
                                                'register_id': advantage_rule.benefits_discounts.register_id.id,
                                                'amount': amount,
                                                'employee_id': contract.employee_id.id,
                                                'quantity': qty,
                                                'rate': rate}
                                        elif total <= advantage_rule.amount:
                                            raise UserError(
                                                _(
                                                    'The amount you put is greater than fact value of this Salary rule'))
                                        else:
                                            amount = total - advantage_rule.amount  # update 21/04/2019
                                            qty, rate = 1, 100.0
                                            previous_amount = advantage_rule.benefits_discounts.code in localdict and \
                                                              localdict[
                                                                  advantage_rule.benefits_discounts.code] or 0.0
                                            tot_rule = amount * qty * rate / 100.0
                                            localdict[advantage_rule.benefits_discounts.code] = tot_rule
                                            rules_dict[advantage_rule.benefits_discounts.code] = advantage_rule
                                            # sum the amount for its salary category
                                            localdict = _sum_salary_rule_category(localdict,
                                                                                  advantage_rule.benefits_discounts.category_id,
                                                                                  tot_rule - previous_amount)
                                            # create/overwrite the rule in the temporary results
                                            result_dict[key] = {
                                                'salary_rule_id': advantage_rule.benefits_discounts.id,
                                                'contract_id': contract.id,
                                                'name': advantage_rule.benefits_discounts.name,
                                                'code': advantage_rule.benefits_discounts.code,
                                                'category_id': advantage_rule.benefits_discounts.category_id.id,
                                                'amount_select': advantage_rule.benefits_discounts.amount_select,
                                                'amount_fix': advantage_rule.benefits_discounts.amount_fix,
                                                'amount_python_compute': advantage_rule.benefits_discounts.amount_python_compute,
                                                'amount_percentage': advantage_rule.benefits_discounts.amount_percentage,
                                                'register_id': advantage_rule.benefits_discounts.register_id.id,
                                                'amount': amount,
                                                'employee_id': contract.employee_id.id,
                                                'quantity': qty,
                                                'rate': rate}
                        else:
                            blacklist += [id for id, seq in rule._recursive_search_of_rules()]

            else:
                advantage_list = []
                for advantage_rule in payslip.contract_id.advantages:
                    advantage_list.append(advantage_rule.benefits_discounts.id)
                for rule in sorted_rules:
                    key1 = rule.code + '-' + str(contract.id)
                    localdict['result'] = None
                    localdict['result_qty'] = 1.0
                    localdict['result_rate'] = 100
                    # check if the rule can be applied
                    if rule._satisfy_condition(localdict) and rule.id not in blacklist:
                        if payslip.contract_id.advantages:
                            for advantage_rule in payslip.contract_id.advantages:
                                key = advantage_rule.benefits_discounts.code + '-' + str(contract.id)
                                date1 = datetime.strptime(str(advantage_rule.date_from), "%Y-%m-%d")
                                if advantage_rule.benefits_discounts.name == rule.name:
                                    if advantage_rule.date_to:
                                        date2 = datetime.strptime(str(advantage_rule.date_to), "%Y-%m-%d")
                                        if (datetime.strptime(str(payslip.date_from),
                                                              "%Y-%m-%d") >= date1 and date2 >= datetime.strptime(
                                            str(payslip.date_to), "%Y-%m-%d")) \
                                                or date2 >= datetime.strptime(str(payslip.date_from),
                                                                              "%Y-%m-%d") >= date1 \
                                                or date2 >= datetime.strptime(str(payslip.date_to), "%Y-%m-%d") >= date1 \
                                                or (datetime.strptime(str(payslip.date_to),
                                                                      "%Y-%m-%d") >= date1 and date2 >= datetime.strptime(
                                            str(payslip.date_from), "%Y-%m-%d")):
                                            if advantage_rule.type == 'customize':
                                                amount = advantage_rule.amount
                                                qty, rate = 1, 100.0
                                                previous_amount = advantage_rule.benefits_discounts.code in localdict and \
                                                                  localdict[
                                                                      advantage_rule.benefits_discounts.code] or 0.0
                                                tot_rule = amount * qty * rate / 100.0
                                                localdict[advantage_rule.benefits_discounts.code] = tot_rule
                                                rules_dict[advantage_rule.benefits_discounts.code] = advantage_rule
                                                # sum the amount for its salary category
                                                localdict = _sum_salary_rule_category(localdict,
                                                                                      advantage_rule.benefits_discounts.category_id,
                                                                                      tot_rule - previous_amount)
                                                # create/overwrite the rule in the temporary results
                                                result_dict[key] = {
                                                    'salary_rule_id': advantage_rule.benefits_discounts.id,
                                                    'contract_id': contract.id,
                                                    'name': advantage_rule.benefits_discounts.name,
                                                    'code': advantage_rule.benefits_discounts.code,
                                                    'category_id': advantage_rule.benefits_discounts.category_id.id,
                                                    'amount_select': advantage_rule.benefits_discounts.amount_select,
                                                    'amount_fix': advantage_rule.benefits_discounts.amount_fix,
                                                    'amount_python_compute': advantage_rule.benefits_discounts.amount_python_compute,
                                                    'amount_percentage': advantage_rule.benefits_discounts.amount_percentage,
                                                    'register_id': advantage_rule.benefits_discounts.register_id.id,
                                                    'amount': amount,
                                                    'employee_id': contract.employee_id.id,
                                                    'quantity': qty,
                                                    'rate': rate}
                                            elif advantage_rule.type == 'exception':
                                                total = advantage_rule.benefits_discounts._compute_rule(localdict)[
                                                    0]  # update 21/04/2019
                                                if total == advantage_rule.amount or total == 0.0:
                                                    amount, qty, rate = 0.0, 0, 0.0
                                                    previous_amount = advantage_rule.benefits_discounts.code in localdict and \
                                                                      localdict[
                                                                          advantage_rule.benefits_discounts.code] or 0.0
                                                    tot_rule = amount * qty * rate / 100.0
                                                    localdict[advantage_rule.benefits_discounts.code] = tot_rule
                                                    rules_dict[advantage_rule.benefits_discounts.code] = advantage_rule
                                                    localdict = _sum_salary_rule_category(localdict,
                                                                                          advantage_rule.benefits_discounts.category_id,
                                                                                          tot_rule - previous_amount)
                                                    # create/overwrite the rule in the temporary results
                                                    result_dict[key] = {
                                                        'salary_rule_id': advantage_rule.benefits_discounts.id,
                                                        'contract_id': contract.id,
                                                        'name': advantage_rule.benefits_discounts.name,
                                                        'code': advantage_rule.benefits_discounts.code,
                                                        'category_id': advantage_rule.benefits_discounts.category_id.id,
                                                        'amount_select': advantage_rule.benefits_discounts.amount_select,
                                                        'amount_fix': advantage_rule.benefits_discounts.amount_fix,
                                                        'amount_python_compute': advantage_rule.benefits_discounts.amount_python_compute,
                                                        'amount_percentage': advantage_rule.benefits_discounts.amount_percentage,
                                                        'register_id': advantage_rule.benefits_discounts.register_id.id,
                                                        'amount': amount,
                                                        'employee_id': contract.employee_id.id,
                                                        'quantity': qty,
                                                        'rate': rate}
                                                elif total <= advantage_rule.amount:
                                                    raise UserError(
                                                        _(
                                                            'The amount you put is greater than fact value of this Salary rule'))
                                                else:
                                                    amount = total - advantage_rule.amount  # update 21/04/2019
                                                    qty, rate = 1, 100.0
                                                    previous_amount = advantage_rule.benefits_discounts.code in localdict and \
                                                                      localdict[
                                                                          advantage_rule.benefits_discounts.code] or 0.0
                                                    tot_rule = amount * qty * rate / 100.0
                                                    localdict[advantage_rule.benefits_discounts.code] = tot_rule
                                                    rules_dict[advantage_rule.benefits_discounts.code] = advantage_rule
                                                    # sum the amount for its salary category
                                                    localdict = _sum_salary_rule_category(localdict,
                                                                                          advantage_rule.benefits_discounts.category_id,
                                                                                          tot_rule - previous_amount)
                                                    # create/overwrite the rule in the temporary results
                                                    result_dict[key] = {
                                                        'salary_rule_id': advantage_rule.benefits_discounts.id,
                                                        'contract_id': contract.id,
                                                        'name': advantage_rule.benefits_discounts.name,
                                                        'code': advantage_rule.benefits_discounts.code,
                                                        'category_id': advantage_rule.benefits_discounts.category_id.id,
                                                        'amount_select': advantage_rule.benefits_discounts.amount_select,
                                                        'amount_fix': advantage_rule.benefits_discounts.amount_fix,
                                                        'amount_python_compute': advantage_rule.benefits_discounts.amount_python_compute,
                                                        'amount_percentage': advantage_rule.benefits_discounts.amount_percentage,
                                                        'register_id': advantage_rule.benefits_discounts.register_id.id,
                                                        'amount': amount,
                                                        'employee_id': contract.employee_id.id,
                                                        'quantity': qty,
                                                        'rate': rate}
                                        else:
                                            amount, qty, rate = rule._compute_rule(localdict)
                                            previous_amount = rule.code in localdict and localdict[rule.code] or 0.0
                                            tot_rule = amount * qty * rate / 100.0
                                            localdict[rule.code] = tot_rule
                                            rules_dict[rule.code] = rule
                                            localdict = _sum_salary_rule_category(localdict, rule.category_id,
                                                                                  tot_rule - previous_amount)
                                            # create/overwrite the rule in the temporary results
                                            if amount != 0:
                                                result_dict[key1] = {
                                                    'salary_rule_id': rule.id,
                                                    'contract_id': contract.id,
                                                    'name': rule.name,
                                                    'code': rule.code,
                                                    'category_id': rule.category_id.id,
                                                    'amount_select': rule.amount_select,
                                                    'amount_fix': rule.amount_fix,
                                                    'amount_python_compute': rule.amount_python_compute,
                                                    'amount_percentage': rule.amount_percentage,
                                                    'register_id': rule.register_id.id,
                                                    'amount': amount,
                                                    'employee_id': contract.employee_id.id,
                                                    'quantity': qty,
                                                    'rate': rate}
                                    else:
                                        if date1 <= datetime.strptime(str(payslip.date_from), "%Y-%m-%d"):
                                            if advantage_rule.benefits_discounts.name in sorted_rules:
                                                if advantage_rule.type == 'customize':
                                                    amount = advantage_rule.amount
                                                    qty, rate = 1, 100.0
                                                    previous_amount = advantage_rule.benefits_discounts.code in localdict and \
                                                                      localdict[
                                                                          advantage_rule.benefits_discounts.code] or 0.0
                                                    tot_rule = amount * qty * rate / 100.0
                                                    localdict[advantage_rule.benefits_discounts.code] = tot_rule
                                                    rules_dict[advantage_rule.benefits_discounts.code] = advantage_rule
                                                    # sum the amount for its salary category
                                                    localdict = _sum_salary_rule_category(localdict,
                                                                                          advantage_rule.benefits_discounts.category_id,
                                                                                          tot_rule - previous_amount)
                                                    # create/overwrite the rule in the temporary results
                                                    result_dict[key] = {
                                                        'salary_rule_id': advantage_rule.benefits_discounts.id,
                                                        'contract_id': contract.id,
                                                        'name': advantage_rule.benefits_discounts.name,
                                                        'code': advantage_rule.benefits_discounts.code,
                                                        'category_id': advantage_rule.benefits_discounts.category_id.id,
                                                        'amount_select': advantage_rule.benefits_discounts.amount_select,
                                                        'amount_fix': advantage_rule.benefits_discounts.amount_fix,
                                                        'amount_python_compute': advantage_rule.benefits_discounts.amount_python_compute,
                                                        'amount_percentage': advantage_rule.benefits_discounts.amount_percentage,
                                                        'register_id': advantage_rule.benefits_discounts.register_id.id,
                                                        'amount': amount,
                                                        'employee_id': contract.employee_id.id,
                                                        'quantity': qty,
                                                        'rate': rate}
                                                elif advantage_rule.type == 'exception':
                                                    total = advantage_rule.benefits_discounts._compute_rule(localdict)[
                                                        0]
                                                    if total == advantage_rule.amount or total == 0.0:
                                                        amount, qty, rate = 0.0, 0, 0.0
                                                        previous_amount = advantage_rule.benefits_discounts.code in localdict and \
                                                                          localdict[
                                                                              advantage_rule.benefits_discounts.code] or 0.0
                                                        tot_rule = amount * qty * rate / 100.0
                                                        localdict[advantage_rule.benefits_discounts.code] = tot_rule
                                                        rules_dict[
                                                            advantage_rule.benefits_discounts.code] = advantage_rule
                                                        # sum the amount for its salary category
                                                        localdict = _sum_salary_rule_category(localdict,
                                                                                              advantage_rule.benefits_discounts.category_id,
                                                                                              tot_rule - previous_amount)
                                                        # create/overwrite the rule in the temporary results
                                                        result_dict[key] = {
                                                            'salary_rule_id': advantage_rule.benefits_discounts.id,
                                                            'contract_id': contract.id,
                                                            'name': advantage_rule.benefits_discounts.name,
                                                            'code': advantage_rule.benefits_discounts.code,
                                                            'category_id': advantage_rule.benefits_discounts.category_id.id,
                                                            'amount_select': advantage_rule.benefits_discounts.amount_select,
                                                            'amount_fix': advantage_rule.benefits_discounts.amount_fix,
                                                            'amount_python_compute': advantage_rule.benefits_discounts.amount_python_compute,
                                                            'amount_percentage': advantage_rule.benefits_discounts.amount_percentage,
                                                            'register_id': advantage_rule.benefits_discounts.register_id.id,
                                                            'amount': amount,
                                                            'employee_id': contract.employee_id.id,
                                                            'quantity': qty,
                                                            'rate': rate}
                                                    elif total <= advantage_rule.amount:
                                                        raise UserError(
                                                            _(
                                                                'The amount you put is greater than fact value of this Salary rule'))
                                                    else:
                                                        amount = total - advantage_rule.amount  # update 21/04/2019
                                                        qty, rate = 1, 100.0
                                                        previous_amount = advantage_rule.benefits_discounts.code in localdict and \
                                                                          localdict[
                                                                              advantage_rule.benefits_discounts.code] or 0.0
                                                        tot_rule = amount * qty * rate / 100.0
                                                        localdict[advantage_rule.benefits_discounts.code] = tot_rule
                                                        rules_dict[
                                                            advantage_rule.benefits_discounts.code] = advantage_rule
                                                        # sum the amount for its salary category
                                                        localdict = _sum_salary_rule_category(localdict,
                                                                                              advantage_rule.benefits_discounts.category_id,
                                                                                              tot_rule - previous_amount)
                                                        # create/overwrite the rule in the temporary results
                                                        result_dict[key] = {
                                                            'salary_rule_id': advantage_rule.benefits_discounts.id,
                                                            'contract_id': contract.id,
                                                            'name': advantage_rule.benefits_discounts.name,
                                                            'code': advantage_rule.benefits_discounts.code,
                                                            'category_id': advantage_rule.benefits_discounts.category_id.id,
                                                            'amount_select': advantage_rule.benefits_discounts.amount_select,
                                                            'amount_fix': advantage_rule.benefits_discounts.amount_fix,
                                                            'amount_python_compute': advantage_rule.benefits_discounts.amount_python_compute,
                                                            'amount_percentage': advantage_rule.benefits_discounts.amount_percentage,
                                                            'register_id': advantage_rule.benefits_discounts.register_id.id,
                                                            'amount': amount,
                                                            'employee_id': contract.employee_id.id,
                                                            'quantity': qty,
                                                            'rate': rate}
                                            else:
                                                if advantage_rule.benefits_discounts.name not in sorted_rules:
                                                    amount, qty, rate = rule._compute_rule(localdict)
                                                    previous_amount = rule.code in localdict and localdict[
                                                        rule.code] or 0.0
                                                    tot_rule = amount * qty * rate / 100.0
                                                    localdict[rule.code] = tot_rule
                                                    rules_dict[rule.code] = rule
                                                    localdict = _sum_salary_rule_category(localdict, rule.category_id,
                                                                                          tot_rule - previous_amount)
                                                    # create/overwrite the rule in the temporary results
                                                    if amount != 0:
                                                        result_dict[key1] = {
                                                            'salary_rule_id': rule.id,
                                                            'contract_id': contract.id,
                                                            'name': rule.name,
                                                            'code': rule.code,
                                                            'category_id': rule.category_id.id,
                                                            'amount_select': rule.amount_select,
                                                            'amount_fix': rule.amount_fix,
                                                            'amount_python_compute': rule.amount_python_compute,
                                                            'amount_percentage': rule.amount_percentage,
                                                            'register_id': rule.register_id.id,
                                                            'amount': amount,
                                                            'employee_id': contract.employee_id.id,
                                                            'quantity': qty,
                                                            'rate': rate}

                                                    if advantage_rule.type == 'customize':
                                                        amount = advantage_rule.amount
                                                        qty, rate = 1, 100.0
                                                        previous_amount = advantage_rule.benefits_discounts.code in localdict and \
                                                                          localdict[
                                                                              advantage_rule.benefits_discounts.code] or 0.0
                                                        tot_rule = amount * qty * rate / 100.0
                                                        localdict[advantage_rule.benefits_discounts.code] = tot_rule
                                                        rules_dict[
                                                            advantage_rule.benefits_discounts.code] = advantage_rule
                                                        # sum the amount for its salary category
                                                        localdict = _sum_salary_rule_category(localdict,
                                                                                              advantage_rule.benefits_discounts.category_id,
                                                                                              tot_rule - previous_amount)
                                                        # create/overwrite the rule in the temporary results
                                                        result_dict[key] = {
                                                            'salary_rule_id': advantage_rule.benefits_discounts.id,
                                                            'contract_id': contract.id,
                                                            'name': advantage_rule.benefits_discounts.name,
                                                            'code': advantage_rule.benefits_discounts.code,
                                                            'category_id': advantage_rule.benefits_discounts.category_id.id,
                                                            'amount_select': advantage_rule.benefits_discounts.amount_select,
                                                            'amount_fix': advantage_rule.benefits_discounts.amount_fix,
                                                            'amount_python_compute': advantage_rule.benefits_discounts.amount_python_compute,
                                                            'amount_percentage': advantage_rule.benefits_discounts.amount_percentage,
                                                            'register_id': advantage_rule.benefits_discounts.register_id.id,
                                                            'amount': amount,
                                                            'employee_id': contract.employee_id.id,
                                                            'quantity': qty,
                                                            'rate': rate}
                                                    elif advantage_rule.type == 'exception':
                                                        total = \
                                                            advantage_rule.benefits_discounts._compute_rule(localdict)[
                                                                0]
                                                        if total == advantage_rule.amount or total == 0.0:
                                                            amount, qty, rate = 0.0, 0, 0.0
                                                            previous_amount = advantage_rule.benefits_discounts.code in localdict and \
                                                                              localdict[
                                                                                  advantage_rule.benefits_discounts.code] or 0.0
                                                            tot_rule = amount * qty * rate / 100.0
                                                            localdict[advantage_rule.benefits_discounts.code] = tot_rule
                                                            rules_dict[
                                                                advantage_rule.benefits_discounts.code] = advantage_rule
                                                            # sum the amount for its salary category
                                                            localdict = _sum_salary_rule_category(localdict,
                                                                                                  advantage_rule.benefits_discounts.category_id,
                                                                                                  tot_rule - previous_amount)
                                                            # create/overwrite the rule in the temporary results
                                                            result_dict[key] = {
                                                                'salary_rule_id': advantage_rule.benefits_discounts.id,
                                                                'contract_id': contract.id,
                                                                'name': advantage_rule.benefits_discounts.name,
                                                                'code': advantage_rule.benefits_discounts.code,
                                                                'category_id': advantage_rule.benefits_discounts.category_id.id,
                                                                'amount_select': advantage_rule.benefits_discounts.amount_select,
                                                                'amount_fix': advantage_rule.benefits_discounts.amount_fix,
                                                                'amount_python_compute': advantage_rule.benefits_discounts.amount_python_compute,
                                                                'amount_percentage': advantage_rule.benefits_discounts.amount_percentage,
                                                                'register_id': advantage_rule.benefits_discounts.register_id.id,
                                                                'amount': amount,
                                                                'employee_id': contract.employee_id.id,
                                                                'quantity': qty,
                                                                'rate': rate}
                                                        elif total <= advantage_rule.amount:
                                                            raise UserError(
                                                                _(
                                                                    'The amount you put is greater than fact value of this Salary rule'))
                                                        else:
                                                            amount = total - advantage_rule.amount  # update 21/04/2019
                                                            qty, rate = 1, 100.0
                                                            previous_amount = advantage_rule.benefits_discounts.code in localdict and \
                                                                              localdict[
                                                                                  advantage_rule.benefits_discounts.code] or 0.0
                                                            tot_rule = amount * qty * rate / 100.0
                                                            localdict[advantage_rule.benefits_discounts.code] = tot_rule
                                                            rules_dict[
                                                                advantage_rule.benefits_discounts.code] = advantage_rule
                                                            # sum the amount for its salary category
                                                            localdict = _sum_salary_rule_category(localdict,
                                                                                                  advantage_rule.benefits_discounts.category_id,
                                                                                                  tot_rule - previous_amount)
                                                            # create/overwrite the rule in the temporary results
                                                            result_dict[key] = {
                                                                'salary_rule_id': advantage_rule.benefits_discounts.id,
                                                                'contract_id': contract.id,
                                                                'name': advantage_rule.benefits_discounts.name,
                                                                'code': advantage_rule.benefits_discounts.code,
                                                                'category_id': advantage_rule.benefits_discounts.category_id.id,
                                                                'amount_select': advantage_rule.benefits_discounts.amount_select,
                                                                'amount_fix': advantage_rule.benefits_discounts.amount_fix,
                                                                'amount_python_compute': advantage_rule.benefits_discounts.amount_python_compute,
                                                                'amount_percentage': advantage_rule.benefits_discounts.amount_percentage,
                                                                'register_id': advantage_rule.benefits_discounts.register_id.id,
                                                                'amount': amount,
                                                                'employee_id': contract.employee_id.id,
                                                                'quantity': qty,
                                                                'rate': rate}
                                        else:
                                            amount, qty, rate = rule._compute_rule(localdict)
                                            previous_amount = rule.code in localdict and localdict[rule.code] or 0.0
                                            tot_rule = amount * qty * rate / 100.0
                                            localdict[rule.code] = tot_rule
                                            rules_dict[rule.code] = rule
                                            localdict = _sum_salary_rule_category(localdict, rule.category_id,
                                                                                  tot_rule - previous_amount)
                                            # create/overwrite the rule in the temporary results
                                            if amount != 0:
                                                result_dict[key1] = {
                                                    'salary_rule_id': rule.id,
                                                    'contract_id': contract.id,
                                                    'name': rule.name,
                                                    'code': rule.code,
                                                    'category_id': rule.category_id.id,
                                                    'amount_select': rule.amount_select,
                                                    'amount_fix': rule.amount_fix,
                                                    'amount_python_compute': rule.amount_python_compute,
                                                    'amount_percentage': rule.amount_percentage,
                                                    'register_id': rule.register_id.id,
                                                    'amount': amount,
                                                    'employee_id': contract.employee_id.id,
                                                    'quantity': qty,
                                                    'rate': rate}

                                else:
                                    if rule.id not in advantage_list:
                                        # compute the amount of the rule
                                        amount, qty, rate = rule._compute_rule(localdict)
                                        # check if there is already a rule computed with that code
                                        previous_amount = rule.code in localdict and localdict[rule.code] or 0.0
                                        # set/overwrite the amount computed for this rule in the localdict
                                        tot_rule = amount * qty * rate / 100.0
                                        localdict[rule.code] = tot_rule
                                        rules_dict[rule.code] = rule
                                        # sum the amount for its salary category
                                        localdict = _sum_salary_rule_category(localdict, rule.category_id,
                                                                              tot_rule - previous_amount)
                                        # create/overwrite the rule in the temporary results
                                        if amount != 0:
                                            result_dict[key1] = {
                                                'salary_rule_id': rule.id,
                                                'contract_id': contract.id,
                                                'name': rule.name,
                                                'code': rule.code,
                                                'category_id': rule.category_id.id,
                                                'amount_select': rule.amount_select,
                                                'amount_fix': rule.amount_fix,
                                                'amount_python_compute': rule.amount_python_compute,
                                                'amount_percentage': rule.amount_percentage,
                                                'register_id': rule.register_id.id,
                                                'amount': amount,
                                                'employee_id': contract.employee_id.id,
                                                'quantity': qty,
                                                'rate': rate}

                                    if advantage_rule.type == 'customize':
                                        amount = advantage_rule.amount
                                        qty, rate = 1, 100.0
                                        previous_amount = advantage_rule.benefits_discounts.code in localdict and \
                                                          localdict[advantage_rule.benefits_discounts.code] or 0.0
                                        tot_rule = amount * qty * rate / 100.0
                                        localdict[advantage_rule.benefits_discounts.code] = tot_rule
                                        rules_dict[advantage_rule.benefits_discounts.code] = advantage_rule
                                        # sum the amount for its salary category
                                        localdict = _sum_salary_rule_category(localdict,
                                                                              advantage_rule.benefits_discounts.category_id,
                                                                              tot_rule - previous_amount)
                                        # create/overwrite the rule in the temporary results
                                        result_dict[key] = {
                                            'salary_rule_id': advantage_rule.benefits_discounts.id,
                                            'contract_id': contract.id,
                                            'name': advantage_rule.benefits_discounts.name,
                                            'code': advantage_rule.benefits_discounts.code,
                                            'category_id': advantage_rule.benefits_discounts.category_id.id,
                                            'amount_select': advantage_rule.benefits_discounts.amount_select,
                                            'amount_fix': advantage_rule.benefits_discounts.amount_fix,
                                            'amount_python_compute': advantage_rule.benefits_discounts.amount_python_compute,
                                            'amount_percentage': advantage_rule.benefits_discounts.amount_percentage,
                                            'register_id': advantage_rule.benefits_discounts.register_id.id,
                                            'amount': amount,
                                            'employee_id': contract.employee_id.id,
                                            'quantity': qty,
                                            'rate': rate}
                                    elif advantage_rule.type == 'exception':
                                        total = advantage_rule.benefits_discounts._compute_rule(
                                            localdict)[0]  # update 21/04/2019
                                        if total == advantage_rule.amount or total == 0.0:
                                            amount, qty, rate = 0.0, 0, 0.0
                                            previous_amount = advantage_rule.benefits_discounts.code in localdict and \
                                                              localdict[
                                                                  advantage_rule.benefits_discounts.code] or 0.0
                                            tot_rule = amount * qty * rate / 100.0
                                            localdict[advantage_rule.benefits_discounts.code] = tot_rule
                                            rules_dict[advantage_rule.benefits_discounts.code] = advantage_rule
                                            localdict = _sum_salary_rule_category(localdict,
                                                                                  advantage_rule.benefits_discounts.category_id,
                                                                                  tot_rule - previous_amount)
                                            # create/overwrite the rule in the temporary results
                                            result_dict[key] = {
                                                'salary_rule_id': advantage_rule.benefits_discounts.id,
                                                'contract_id': contract.id,
                                                'name': advantage_rule.benefits_discounts.name,
                                                'code': advantage_rule.benefits_discounts.code,
                                                'category_id': advantage_rule.benefits_discounts.category_id.id,
                                                'amount_select': advantage_rule.benefits_discounts.amount_select,
                                                'amount_fix': advantage_rule.benefits_discounts.amount_fix,
                                                'amount_python_compute': advantage_rule.benefits_discounts.amount_python_compute,
                                                'amount_percentage': advantage_rule.benefits_discounts.amount_percentage,
                                                'register_id': advantage_rule.benefits_discounts.register_id.id,
                                                'amount': amount,
                                                'employee_id': contract.employee_id.id,
                                                'quantity': qty,
                                                'rate': rate}
                                        elif total <= advantage_rule.amount:
                                            raise UserError(
                                                _(
                                                    'The amount you put is greater than fact value of this Salary rule'))
                                        else:
                                            amount = total - advantage_rule.amount  # update 21/04/2019
                                            qty, rate = 1, 100.0
                                            previous_amount = advantage_rule.benefits_discounts.code in localdict and \
                                                              localdict[advantage_rule.benefits_discounts.code] or 0.0
                                            tot_rule = amount * qty * rate / 100.0
                                            localdict[advantage_rule.benefits_discounts.code] = tot_rule
                                            rules_dict[advantage_rule.benefits_discounts.code] = advantage_rule
                                            # sum the amount for its salary category
                                            localdict = _sum_salary_rule_category(localdict,
                                                                                  advantage_rule.benefits_discounts.category_id,
                                                                                  tot_rule - previous_amount)
                                            # create/overwrite the rule in the temporary results
                                            result_dict[key] = {
                                                'salary_rule_id': advantage_rule.benefits_discounts.id,
                                                'contract_id': contract.id,
                                                'name': advantage_rule.benefits_discounts.name,
                                                'code': advantage_rule.benefits_discounts.code,
                                                'category_id': advantage_rule.benefits_discounts.category_id.id,
                                                'amount_select': advantage_rule.benefits_discounts.amount_select,
                                                'amount_fix': advantage_rule.benefits_discounts.amount_fix,
                                                'amount_python_compute': advantage_rule.benefits_discounts.amount_python_compute,
                                                'amount_percentage': advantage_rule.benefits_discounts.amount_percentage,
                                                'register_id': advantage_rule.benefits_discounts.register_id.id,
                                                'amount': amount,
                                                'employee_id': contract.employee_id.id,
                                                'quantity': qty,
                                                'rate': rate}
                                advantage_rule.write({'done': True})
                        else:
                            # compute the amount of the rule
                            amount, qty, rate = rule._compute_rule(localdict)
                            # check if there is already a rule computed with that code
                            previous_amount = rule.code in localdict and localdict[rule.code] or 0.0
                            # set/overwrite the amount computed for this rule in the localdict
                            tot_rule = amount * qty * rate / 100.0
                            localdict[rule.code] = tot_rule
                            rules_dict[rule.code] = rule
                            # sum the amount for its salary category
                            localdict = _sum_salary_rule_category(localdict, rule.category_id,
                                                                  tot_rule - previous_amount)
                            # create/overwrite the rule in the temporary results
                            if amount != 0:
                                result_dict[key1] = {
                                    'salary_rule_id': rule.id,
                                    'contract_id': contract.id,
                                    'name': rule.name,
                                    'code': rule.code,
                                    'category_id': rule.category_id.id,
                                    'amount_select': rule.amount_select,
                                    'amount_fix': rule.amount_fix,
                                    'amount_python_compute': rule.amount_python_compute,
                                    'amount_percentage': rule.amount_percentage,
                                    'register_id': rule.register_id.id,
                                    'amount': amount,
                                    'employee_id': contract.employee_id.id,
                                    'quantity': qty,
                                    'rate': rate}
                    else:
                        blacklist += [id for id, seq in rule._recursive_search_of_rules()]

        return list(result_dict.values())


class HrPayslipLine(models.Model):
    _inherit = 'hr.payslip.line'

    leave_request_case = fields.Boolean()

    # Relational fields
    payslip_allowance = fields.Many2one('hr.payslip', ondelete='cascade', index=True)
    payslip_deduction = fields.Many2one('hr.payslip', ondelete='cascade', index=True)
    related_benefits_discounts = fields.Many2many(comodel_name='hr.salary.rule',
                                                  relation='payslip_line_benefit_discount_rel',
                                                  column1='rule_id', column2='sub_rule_id',
                                                  string='Related Benefits and Discount')
    percentage = fields.Float(string='Percentage', related='slip_id.percentage')

    # override compute function in payslip lines
    @api.depends('quantity', 'amount', 'rate')
    def _compute_total(self):
        # payslip = self.env['hr.payslip'].search([('id', '=', self.slip_id.id)])
        #print("payslip######################### ", self)
        start_time = time.time()
        for line in self:
            #print('--------------------------hr.payslip.line-------------------', line.id)
            if line.slip_id.worked_days_line_ids:
                total_days = 0
                per = 0
                for wo in line.slip_id.worked_days_line_ids:

                    ####################################################### Holidays Unpaid  ######################################
                    if wo.name == "Unpaid Holidays For this month":
                        work_days = wo.number_of_days
                        if total_days:
                            line.slip_id.total_allowances = 0.0
                            line.slip_id.total_deductions = 0.0
                            total_days_after_holiday = total_days - work_days
                            total_days = total_days_after_holiday

                        else:
                            total_days_after_holiday = 30 - work_days
                            total_days = total_days_after_holiday
                        if line.salary_rule_id.special == False:
                            line.total = round(((line.amount / 30) * total_days_after_holiday) * line.percentage / 100,2)
                        else:
                            line.total = round(((line.amount) * line.percentage / 100),2)
                        # line.total = ((line.amount / 30) * total_days_after_holiday) * line.percentage / 100
                    #################################################### Holidays percentage  #######################################
                    elif wo.name == "Paid Holidays By percentage":
                        work_days = wo.number_of_days
                        percentage = wo.number_of_hours
                        if total_days:
                            line.slip_id.total_allowances = 0.0
                            line.slip_id.total_deductions = 0.0
                            total_days_after_holiday = total_days - work_days
                            total_days = total_days_after_holiday

                        else:
                            total_days_after_holiday = 30 - work_days
                            total_days = total_days_after_holiday
                        allow = (line.amount / 30) * work_days
                        per += (allow * percentage / 100)
                        actual_allow_tot = (line.amount / 30) * total_days_after_holiday
                        if line.salary_rule_id.special == False:
                            line.total = round((actual_allow_tot + per) * line.percentage / 100,2)
                        else:
                            line.total = round(((line.amount) * line.percentage / 100),2)
                        # line.total = (actual_allow_tot + per) * line.percentage / 100
                    ##################################################### Holidays Additional  ########################################
                    elif wo.name == "Additional Paid Holidays":
                        work_days = wo.number_of_days
                        if total_days:
                            line.slip_id.total_allowances = 0.0
                            line.slip_id.total_deductions = 0.0
                            total_days_after_holiday = total_days - work_days
                            total_days = total_days_after_holiday


                        else:
                            total_days_after_holiday = 30 - work_days
                            total_days = total_days_after_holiday
                        if line.leave_request_case or line.salary_rule_id.special == True:
                            line.total = round((line.amount) * line.percentage / 100,2)
                        else:
                            line.total = round(((line.amount / 30) * total_days_after_holiday) * line.percentage / 100,2)
                    ################################################### Holidays Reconcile and Exclusion  ###############################
                    elif wo.name == "Exclusion or Reconcile Paid Holidays":
                        work_days = wo.number_of_days
                        if total_days:
                            line.slip_id.total_allowances = 0.0
                            line.slip_id.total_deductions = 0.0
                            total_days_after_holiday = total_days - work_days
                            total_days = total_days_after_holiday

                        else:
                            total_days_after_holiday = 30 - work_days
                            total_days = total_days_after_holiday
                        if not line.leave_request_case or line.salary_rule_id.special == True:
                            line.total = round((line.amount) * line.percentage / 100,2)
                        else:
                            line.total = round(((line.amount / 30) * total_days_after_holiday) * line.percentage / 100,2)
                    ################################################### Working days for this month ######################################
                    else:
                        work_days = wo.number_of_days
                        total_days = work_days
                        if line.leave_request_case or line.salary_rule_id.special == True:
                            line.total = round((line.amount) * line.percentage / 100,2)
                        else:
                            line.total = round(((line.amount / 30) * work_days) * line.percentage / 100,2)
            ################################################### End IF Then else #################################################
            else:
                total = Decimal(line.amount * line.percentage / 100)
                rounded = total.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                line.total = round(rounded,2)
        #print("compute_shee_computee_total payslips_Run %s" % (time.time() - start_time))


class HrPayslipRun(models.Model):
    _inherit = 'hr.payslip.run'

    required_condition = fields.Boolean(string='Required Condition', compute='compute_type')
    state = fields.Selection(selection_add=[('computed', 'Computed'),
                                            ('confirmed', 'Confirmed'),
                                            ('transfered', 'Transfer'), ('close', 'Close')], tracking=True)

    # Relational fields
    salary_scale = fields.Many2one('hr.payroll.structure', string='Salary Scale')
    employee_ids = fields.Many2many('hr.employee', 'hr_employee_payslip_rel', 'payslip_id', 'employee_id', 'Employees',
                                    index=True,domain="[('id', 'in', employee_value_ids)]")
    department_ids = fields.Many2many('hr.department', 'hr_department_payslip_rel',
                                      'payslip_id', 'department_id', 'Departments')
    journal_id = fields.Many2one('account.journal', 'Salary Journal')

    percentage = fields.Float(string='Percentage', default=100)
    move_id = fields.Many2one('account.move', string="Move Number")
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    employee_value_ids = fields.Many2many(comodel_name="hr.employee", compute="_compute_allowed_value_ids")
    holiday_start_date = fields.Date(string="Holiday Start Date")
    holiday_end_date = fields.Date(string="Holiday End Date")


    @api.onchange('date_start')
    def check_date_start(self):
        if self.date_start :
            self.date_end = fields.Date.from_string(self.date_start)+relativedelta(months=+1, day=1, days=-1)

    @api.onchange('date_end')
    def check_date_end(self):
        if self.date_start and self.date_end and self.date_start > self.date_end:
            raise UserError(_('Date From must be less than or equal Date To'))
        month_current_from = datetime.strptime(str(self.date_start), '%Y-%m-%d').strftime('%m')
        year_current_from  = datetime.strptime(str(self.date_start), '%Y-%m-%d').strftime('%y')
        month_current_to   = datetime.strptime(str(self.date_end), '%Y-%m-%d').strftime('%m')
        year_current_to    = datetime.strptime(str(self.date_end), '%Y-%m-%d').strftime('%y')
        if month_current_from != month_current_to or year_current_from != year_current_to: 
           raise exceptions.Warning(_('Sorry, The Pyroll period Must be During the same Month'))

    @api.depends('salary_scale.transfer_type')
    def compute_type(self):
        if self.salary_scale.transfer_type == 'all' or self.salary_scale.transfer_type == 'per_analytic_account':
            self.required_condition = True
        else:
            self.required_condition = False

    # domain the employee to compute salary
    @api.depends('salary_scale','department_ids','date_start')
    def _compute_allowed_value_ids(self):
        for item in self:
            date_from = str(item.date_start)
            date_to = str(item.date_end)
            if item.salary_scale:
                if item.department_ids:
                    depart = item.department_ids._origin
                    #for dep in item.department_ids._origin:
                    employee_contracts = self.env['hr.contract'].search(
                            [('salary_scale', '=', item.salary_scale.id),
                             ('state', '=', 'program_directory')]).filtered(
                            lambda item: item.employee_id.department_id in depart and item.employee_id.state == 'open' 
                                   and str(item.employee_id.first_hiring_date) <= date_to)
                    item.employee_value_ids = employee_contracts.mapped("employee_id")
                else:
                    employee_contracts = self.env['hr.contract'].search(
                        [('salary_scale', '=', item.salary_scale.id), ('state', '=', 'program_directory')]).filtered(
                        lambda item: item.employee_id.state == 'open' and str(item.employee_id.first_hiring_date) <= date_to)

                    item.employee_value_ids = employee_contracts.mapped("employee_id")
            else:
                item.employee_value_ids = False

    @api.onchange('salary_scale')
    def _onchange_salary_scale_id(self):
        for item in self:
            if item.salary_scale:
                item.employee_ids = False
                item.department_ids = False

    @api.onchange('department_ids','date_start')
    def _onchange_department_ids(self):
        for item in self:
            item.employee_ids = False

    '''@api.onchange('salary_scale')
    def onchange_salary_scale_id(self):
        for item in self:
            if item.salary_scale:
                item.employee_ids = False
                item.department_ids = False
                if item.department_ids:
                    for dep in item.department_ids:
                        employee_contracts = self.env['hr.contract'].search(
                            [('salary_scale', '=', item.salary_scale.id),
                             ('state', '=', 'program_directory')]).filtered(
                            lambda item: item.employee_id.department_id == dep and item.employee_id.state == 'open')
                        emps = []
                        for contract in employee_contracts:
                            emps.append(contract.employee_id.id)
                        return {'domain': {'employee_ids': [('id', 'in', emps)]}}
                else:
                    employee_contracts = self.env['hr.contract'].search(
                        [('salary_scale', '=', item.salary_scale.id), ('state', '=', 'program_directory')]).filtered(
                        lambda item: item.employee_id.state == 'open')
                    emps = []
                    for contract in employee_contracts:
                        emps.append(contract.employee_id.id)
                    return {'domain': {'employee_ids': [('id', 'in', emps)]}}
            else:
                return {'domain': {'employee_ids': [('id', 'in', [])]}}'''

    # Override function compute sheet in Payslip Batches


    def compute_sheet(self):
        payslips = self.env['hr.payslip']
        [data] = self.read()
        from_date = str(self.date_start)
        to_date = str(self.date_end)
        holiday_start_date = str(self.holiday_start_date) if self.holiday_start_date else False
        holiday_end_date = str(self.holiday_end_date) if self.holiday_end_date else False
        start_time = time.time()

        #worked_days, emps, dictionary = [], [], []
        worked_days, emps, dictionary,emp_last_payslip,emp_priv_payslip = [], [], [], [],[]

        if datetime.strptime(str(from_date), "%Y-%m-%d").date().month == datetime.strptime(str(to_date),"%Y-%m-%d").date().month:
            month_date = datetime.strptime(str(from_date), "%Y-%m-%d").date()

        if self.department_ids:
            for dep in self.department_ids:
                employee_contracts = self.env['hr.contract'].search(
                    [('salary_scale', '=', self.salary_scale.id), ('state', '=', 'program_directory')]).filtered(
                    lambda item: item.employee_id.department_id == dep and item.employee_id.state == 'open'
                           and str(item.employee_id.first_hiring_date) <= to_date)
                for contract in employee_contracts:
                    emps.append(contract.employee_id.id)
        else:
            employee_contracts = self.env['hr.contract'].search(
                [('salary_scale', '=', self.salary_scale.id), ('state', '=', 'program_directory')]).filtered(
                lambda item: item.employee_id.state == 'open' and str(item.employee_id.first_hiring_date) <= to_date)
            for contract in employee_contracts:
                emps.append(contract.employee_id.id)

        emps = self.env['hr.employee'].browse(emps)
        employees = self.env['hr.employee'].browse(data['employee_ids'])

        ################### Employee run payslip one in month and previously month #######
        last_payslips = self.env['hr.payslip'].search([('date_from', '>=', self.date_start),('date_from', '<=', self.date_end),
                                                       ('payslip_run_id', '!=', self.id)])
        if last_payslips:
           for priv_pay in last_payslips:
               if employees:
                  for emp in employees:
                      if emp.id == priv_pay.employee_id.id:
                         emp_last_payslip.append(emp.name)
               else :
                  for emp in emps:
                      if emp.id == priv_pay.employee_id.id:
                         emp_last_payslip.append(emp.name)
           if emp_last_payslip:
               raise exceptions.Warning(
                _("Sorry, Salary has already been calculated This Month for Employees \n %s") % (emp_last_payslip))
        ########################################################################################
        last_month = self.date_start - relativedelta(months=1)
        end_last_month = self.date_start - relativedelta(days=1)
        priv_payslips_month = self.env['hr.payslip'].search([('date_from', '>=', last_month),('date_from', '<=', end_last_month),
                                                       ('payslip_run_id', '!=', self.id)]).employee_id
        old_payslips = self.env['hr.payslip'].search([('date_from', '<', self.date_start),
                                                      ('payslip_run_id', '!=', self.id)]).employee_id

        if employees:
           diff_employee= employees-priv_payslips_month
        else:
           diff_employee= emps-priv_payslips_month

        #if diff_employee and diff_employee in old_payslips :
        if diff_employee :
           for emp in diff_employee:
               if emp in old_payslips:
                  emp_priv_payslip.append(emp.name)
           if emp_priv_payslip:
               raise exceptions.Warning(
                  _("Sorry, The Previous month's salary has Not been calculated for Employees \n %s") % (emp_priv_payslip))

        ################### End ################################################################
        if employees:
            locale = self.env.context.get('lang') or 'en_US'
            for employee in employees:
                slip_data = self.env['hr.payslip'].onchange_employee_id(from_date, to_date, employee.id,
                                                                        contract_id=False)
                # pays = self.env['hr.payslip'].search([('contract_id', '=', employee.contract_id.id)])
                ################### Rename Slip and Date#######
                ttyme = datetime.fromtimestamp(time.mktime(time.strptime(str(from_date), "%Y-%m-%d")))
                slip_data['value'].update({
                    'name': _('Salary Slip of %s for %s') % (
                        employee.name, tools.ustr(babel.dates.format_date(date=ttyme, format='MMMM-y',locale=locale))),
                    'company_id': employee.company_id.id,
                })
                ###########
                employee_slip_line = self.slip_ids.filtered(lambda item: item.employee_id.id == employee.id)
                if to_date >= str(employee.first_hiring_date) >= from_date:
                    contract_start_date = datetime.strptime(str(employee.first_hiring_date), "%Y-%m-%d").date()
                    if to_date >= str(employee.leaving_date) >= str(employee.first_hiring_date):
                        contract_end_date = datetime.strptime(str(employee.leaving_date),
                                                              "%Y-%m-%d").date() + timedelta(
                            days=1)
                        duration = relativedelta(contract_end_date, contract_start_date).days
                        hours = (float((contract_end_date - contract_start_date).seconds) / 86400) * 24
                        if not employee_slip_line:
                            res = {
                                'employee_id': employee.id,
                                'name': slip_data['value'].get('name'),
                                'struct_id': self.salary_scale.id,
                                'contract_id': employee.contract_id.id,
                                'input_line_ids': [(0, 0, x) for x in slip_data['value'].get('input_line_ids')],
                                'worked_days_line_ids': worked_days,
                                'date_from': str(employee.first_hiring_date) or from_date,
                                'date_to': employee.leaving_date or to_date,
                                'holiday_start_date': holiday_start_date,
                                'holiday_end_date': holiday_end_date,
                                'credit_note': self.credit_note,
                                'company_id': employee.company_id.id,
                                'percentage': self.percentage}

                            item_payslip = self.env['hr.payslip'].create(res)
                            payslips += item_payslip
                            # if pays:
                            #     for p in pays:
                            #         if p.employee_id != employee and p not in payslips:
                            #             payslips += item_payslip
                            # else:
                            #     payslips += item_payslip
                            if item_payslip:
                                days = {'name': "Working days for this month",
                                        'sequence': 1,
                                        'payslip_id': item_payslip.id,
                                        'code': 2,
                                        'number_of_days': duration,
                                        'number_of_hours': hours,
                                        'contract_id': employee.contract_id.id}
                                worked_days += self.env['hr.payslip.worked_days'].create(days)
                        else:
                            item_payslip = employee_slip_line
                            payslips += item_payslip
                            # if pays:
                            #     for p in pays:
                            #         if p.employee_id != employee and p not in payslips:
                            #             payslips += item_payslip
                            # else:
                            #     payslips += item_payslip
                    else:

                        from calendar import monthrange
                        month_range = monthrange(datetime.now().date().year, month_date.month)[1]
                        contract_end_date = datetime.strptime(str(to_date), "%Y-%m-%d").date()

                        if month_range == 30 and contract_end_date.day == 30:
                            duration = relativedelta(contract_end_date, contract_start_date).days + 1

                        elif month_range > 30 and contract_end_date.day > 30:
                            duration = relativedelta(contract_end_date, contract_start_date).days
                        elif month_range == 28 and contract_end_date.day == 28:
                            duration = relativedelta(contract_end_date, contract_start_date).days + 3

                        elif month_range == 29 and contract_end_date.day == 29:
                            duration = relativedelta(contract_end_date, contract_start_date).days + 2

                        else:
                            duration = relativedelta(contract_end_date, contract_start_date).days + 1

                        hours = (float((contract_end_date - contract_start_date).seconds) / 86400) * 24
                        if not employee_slip_line:


                            res = {
                                'employee_id': employee.id,
                                'name': slip_data['value'].get('name'),
                                'struct_id': self.salary_scale.id,
                                'contract_id': employee.contract_id.id,
                                'input_line_ids': [(0, 0, x) for x in slip_data['value'].get('input_line_ids')],
                                # 'worked_days_line_ids': worked_days ,
                                'date_from': str(employee.first_hiring_date) or from_date,
                                'date_to': to_date,
                                'holiday_start_date': holiday_start_date,
                                'holiday_end_date': holiday_end_date,
                                'credit_note': self.credit_note,
                                'company_id': employee.company_id.id,
                                'percentage': self.percentage}

                            item_payslip = self.env['hr.payslip'].create(res)
                            payslips += item_payslip


                            # if pays:
                            #     for p in pays:
                            #         if p.employee_id != employee and p not in payslips:
                            #             payslips += item_payslip
                            # else:
                            #     payslips += item_payslip

                            if item_payslip:
                                # print("22222222222222222222222222222222222222222222222", employee.english_name)
                                days = {'name': "Working days for this month",
                                        'sequence': 1,
                                        'payslip_id': item_payslip.id,
                                        'code': 2,
                                        'number_of_days': duration,
                                        'number_of_hours': hours,
                                        'contract_id': employee.contract_id.id}
                                worked_days += self.env['hr.payslip.worked_days'].create(days)
                        else:
                            item_payslip = employee_slip_line
                            payslips += item_payslip
                            # if pays:
                            #     for p in pays:
                            #         if p.employee_id != employee and p not in payslips:
                            #             payslips += item_payslip
                            # else:
                            #     payslips += item_payslip

                elif to_date >= str(employee.leaving_date) >= from_date:
                    contract_start_date = datetime.strptime(str(from_date), "%Y-%m-%d").date()
                    contract_end_date = datetime.strptime(str(employee.leaving_date), "%Y-%m-%d").date() + timedelta(
                        days=1)
                    duration = relativedelta(contract_end_date, contract_start_date).days
                    hours = (float((contract_end_date - contract_start_date).seconds) / 86400) * 24
                    employee_slip_line = self.slip_ids.filtered(lambda item: item.employee_id.id == employee.id)
                    if not employee_slip_line:
                        res = {
                            'employee_id': employee.id,
                            'name': slip_data['value'].get('name'),
                            'struct_id': self.salary_scale.id,
                            'contract_id': employee.contract_id.id,
                            'input_line_ids': [(0, 0, x) for x in slip_data['value'].get('input_line_ids')],
                            'worked_days_line_ids': worked_days,
                            'date_from': from_date,
                            'date_to': employee.leaving_date or to_date,
                            'holiday_start_date': holiday_start_date,
                            'holiday_end_date': holiday_end_date,
                            'credit_note': self.credit_note,
                            'company_id': employee.company_id.id,
                            'percentage': self.percentage}

                        item_payslip = self.env['hr.payslip'].create(res)
                        payslips += item_payslip
                        # if pays:
                        #     for p in pays:
                        #         if p.employee_id != employee and p not in payslips:
                        #             payslips += item_payslip
                        # else:
                        #     payslips += item_payslip
                        if item_payslip:
                            days = {'name': "Working days for this month",
                                    'sequence': 1,
                                    'payslip_id': item_payslip.id,
                                    'code': 2,
                                    'number_of_days': duration,
                                    'number_of_hours': hours,
                                    'contract_id': employee.contract_id.id}
                            worked_days += self.env['hr.payslip.worked_days'].create(days)
                    else:
                        item_payslip = employee_slip_line
                        payslips += item_payslip
                        # if pays:
                        #     for p in pays:
                        #         if p.employee_id != employee and p not in payslips:
                        #             payslips += item_payslip
                        # else:
                        #     payslips += item_payslip
                else:
                    if not employee_slip_line and str(employee.first_hiring_date) < from_date:
                        if employee.leaving_date:
                            if str(employee.leaving_date) <= from_date:
                                pass
                            else:
                                res = {
                                    'employee_id': employee.id,
                                    'name': slip_data['value'].get('name'),
                                    'struct_id': self.salary_scale.id,
                                    'contract_id': employee.contract_id.id,
                                    'input_line_ids': [(0, 0, x) for x in slip_data['value'].get('input_line_ids')],
                                    'worked_days_line_ids': [(0, 0, x) for x in
                                                             slip_data['value'].get('worked_days_line_ids')],
                                    'date_from': from_date,
                                    'date_to': to_date,
                                    'holiday_start_date': holiday_start_date,
                                    'holiday_end_date': holiday_end_date,
                                    'credit_note': self.credit_note,
                                    'company_id': employee.company_id.id,
                                    'percentage': self.percentage}

                                payslips += self.env['hr.payslip'].create(res)
                        else:
                            res = {
                                'employee_id': employee.id,
                                'name': slip_data['value'].get('name'),
                                'struct_id': self.salary_scale.id,
                                'contract_id': employee.contract_id.id,
                                'input_line_ids': [(0, 0, x) for x in slip_data['value'].get('input_line_ids')],
                                'worked_days_line_ids': [(0, 0, x) for x in
                                                         slip_data['value'].get('worked_days_line_ids')],
                                'date_from': from_date,
                                'date_to': to_date,
                                'holiday_start_date': holiday_start_date,
                                'holiday_end_date': holiday_end_date,
                                'credit_note': self.credit_note,
                                'company_id': employee.company_id.id,
                                'percentage': self.percentage}

                            payslips += self.env['hr.payslip'].create(res)
                    else:
                        if employee.leaving_date and str(employee.first_hiring_date) < from_date:
                            if str(employee.leaving_date) <= from_date:
                                pass
                            else:
                                payslips += employee_slip_line
                        else:
                            payslips += employee_slip_line
        else:
            for emp in emps:
                slip_data = self.env['hr.payslip'].onchange_employee_id(from_date, to_date, emp.id, contract_id=False)
                # pays = self.env['hr.payslip'].search(
                #     [('contract_id', '=', emp.contract_id.id), ('date_from', '>=', self.date_start)])
                ################### Rename Slip and Date#######
                ttyme = datetime.fromtimestamp(time.mktime(time.strptime(str(from_date), "%Y-%m-%d")))
                slip_data['value'].update({
                    'name': _('Salary Slip of %s for %s') % (
                        emp.name, tools.ustr(babel.dates.format_date(date=ttyme, format='MMMM-y'))),
                    'company_id': emp.company_id.id,
                })
                ###########
                employee_slip_line = self.slip_ids.filtered(lambda item: item.employee_id.id == emp.id)
                if to_date >= str(emp.first_hiring_date) >= from_date:
                    if to_date >= str(emp.leaving_date) >= str(emp.first_hiring_date):
                        contract_start_date = datetime.strptime(str(emp.first_hiring_date), "%Y-%m-%d").date()
                        contract_end_date = datetime.strptime(str(emp.leaving_date), "%Y-%m-%d").date() + timedelta(
                            days=1)
                        duration = relativedelta(contract_end_date, contract_start_date).days
                        hours = (float((contract_end_date - contract_start_date).seconds) / 86400) * 24
                        if not employee_slip_line:
                            res = {
                                'employee_id': emp.id,
                                'name': slip_data['value'].get('name'),
                                'struct_id': self.salary_scale.id,
                                'contract_id': emp.contract_id.id,
                                'input_line_ids': [(0, 0, x) for x in slip_data['value'].get('input_line_ids')],
                                # 'worked_days_line_ids': worked_days,
                                'date_from': emp.first_hiring_date or from_date,
                                'date_to': emp.leaving_date or to_date,
                                'holiday_start_date': holiday_start_date,
                                'holiday_end_date': holiday_end_date,
                                'credit_note': self.credit_note,
                                'company_id': emp.company_id.id,
                                'percentage': self.percentage}
                            item_payslip = self.env['hr.payslip'].create(res)
                            payslips += item_payslip
                            # if pays:
                            #     for p in pays:
                            #         if p.employee_id != emp and p not in payslips:
                            #             payslips += item_payslip
                            # else:
                            #     payslips += item_payslip
                            if item_payslip:
                                days = {'name': "Working days for this month",
                                        'sequence': 1,
                                        'payslip_id': item_payslip.id,
                                        'code': 2,
                                        'number_of_days': duration,
                                        'number_of_hours': hours,
                                        'contract_id': emp.contract_id.id}
                                worked_days += self.env['hr.payslip.worked_days'].create(days)
                        else:
                            item_payslip = employee_slip_line
                            payslips += item_payslip
                            # if pays:
                            #     for p in pays:
                            #         if p.employee_id != emp and p not in payslips:
                            #             payslips += item_payslip
                            # else:
                            #     payslips += item_payslip
                    else:
                        contract_start_date = datetime.strptime(str(emp.first_hiring_date), "%Y-%m-%d").date()
                        from calendar import monthrange
                        month_range = monthrange(datetime.now().date().year, month_date.month)[1]
                        contract_end_date = datetime.strptime(str(to_date), "%Y-%m-%d").date()

                        if month_range == 30 and contract_end_date.day == 30:
                            duration = relativedelta(contract_end_date, contract_start_date).days + 1
                        elif month_range > 30 and contract_end_date.day > 30:
                            duration = relativedelta(contract_end_date, contract_start_date).days
                        elif month_range == 28 and contract_end_date.day == 28:
                            duration = relativedelta(contract_end_date, contract_start_date).days + 3
                        elif month_range == 29 and contract_end_date.day == 29:
                            duration = relativedelta(contract_end_date, contract_start_date).days + 2
                        else:
                            duration = relativedelta(contract_end_date, contract_start_date).days + 1
                        hours = (float((contract_end_date - contract_start_date).seconds) / 86400) * 24
                        if not employee_slip_line:
                            res = {
                                'employee_id': emp.id,
                                'name': slip_data['value'].get('name'),
                                'struct_id': self.salary_scale.id,
                                'contract_id': emp.contract_id.id,
                                'input_line_ids': [(0, 0, x) for x in slip_data['value'].get('input_line_ids')],
                                # 'worked_days_line_ids': worked_days,
                                'date_from': emp.first_hiring_date or from_date,
                                'date_to': to_date,
                                'holiday_start_date': holiday_start_date,
                                'holiday_end_date': holiday_end_date,
                                'credit_note': self.credit_note,
                                'company_id': emp.company_id.id,
                                'percentage': self.percentage}
                            item_payslip = self.env['hr.payslip'].create(res)
                            payslips += item_payslip
                            # if pays:
                            #     for p in pays:
                            #         if p.employee_id != emp and p not in payslips:
                            #             payslips += item_payslip
                            # else:
                            #     payslips += item_payslip
                            if item_payslip:
                                days = {'name': "Working days for this month",
                                        'sequence': 1,
                                        'payslip_id': item_payslip.id,
                                        'code': 2,
                                        'number_of_days': duration,
                                        'number_of_hours': hours,
                                        'contract_id': emp.contract_id.id}
                                worked_days += self.env['hr.payslip.worked_days'].create(days)
                        else:
                            item_payslip = employee_slip_line
                            payslips += item_payslip
                            # if pays:
                            #     for p in pays:
                            #         if p.employee_id != emp and p not in payslips:
                            #             payslips += item_payslip
                            # else:
                            #     payslips += item_payslip

                elif to_date >= str(emp.leaving_date) >= from_date:
                    contract_start_date = datetime.strptime(str(from_date), "%Y-%m-%d").date()
                    contract_end_date = datetime.strptime(str(emp.leaving_date), "%Y-%m-%d").date() + timedelta(days=1)
                    duration = relativedelta(contract_end_date, contract_start_date).days
                    hours = (float((contract_end_date - contract_start_date).seconds) / 86400) * 24
                    if not employee_slip_line:
                        res = {
                            'employee_id': emp.id,
                            'name': slip_data['value'].get('name'),
                            'struct_id': self.salary_scale.id,
                            'contract_id': emp.contract_id.id,
                            'input_line_ids': [(0, 0, x) for x in slip_data['value'].get('input_line_ids')],
                            'worked_days_line_ids': worked_days,
                            'date_from': from_date,
                            'date_to': emp.leaving_date,
                            'holiday_start_date': holiday_start_date,
                            'holiday_end_date': holiday_end_date,
                            'credit_note': self.credit_note,
                            'company_id': emp.company_id.id,
                            'percentage': self.percentage}
                        item_payslip = self.env['hr.payslip'].create(res)
                        payslips += item_payslip
                        # if pays:
                        #     for p in pays:
                        #         if p.employee_id != emp and p not in payslips:
                        #             payslips += item_payslip
                        # else:
                        #     payslips += item_payslip
                        if item_payslip:
                            days = {'name': "Working days for this month",
                                    'sequence': 1,
                                    'payslip_id': item_payslip.id,
                                    'code': 2,
                                    'number_of_days': duration,
                                    'number_of_hours': hours,
                                    'contract_id': emp.contract_id.id}
                            worked_days += self.env['hr.payslip.worked_days'].create(days)
                    else:
                        item_payslip = employee_slip_line
                        payslips += item_payslip
                        # if pays:
                        #     for p in pays:
                        #         if p.employee_id != emp and p not in payslips:
                        #             payslips += item_payslip
                        # else:
                        #     payslips += item_payslip
                else:
                    if not employee_slip_line  and str(emp.first_hiring_date) < from_date:
                        if emp.leaving_date:
                            if str(emp.leaving_date) <= from_date:
                                pass
                            else:
                                res = {
                                    'employee_id': emp.id,
                                    'name': slip_data['value'].get('name'),
                                    'struct_id': self.salary_scale.id,
                                    'contract_id': emp.contract_id.id,
                                    'input_line_ids': [(0, 0, x) for x in slip_data['value'].get('input_line_ids')],
                                    'worked_days_line_ids': [(0, 0, x) for x in
                                                             slip_data['value'].get('worked_days_line_ids')],
                                    'date_from': from_date,
                                    'date_to': to_date,
                                    'holiday_start_date': holiday_start_date,
                                    'holiday_end_date': holiday_end_date,
                                    'credit_note': self.credit_note,
                                    'company_id': emp.company_id.id,
                                    'percentage': self.percentage}
                                # if pays:
                                #     for p in pays:
                                #         if p.employee_id != emp and p not in payslips:
                                #             payslips += self.env['hr.payslip'].create(res)
                                # else:
                                payslips += self.env['hr.payslip'].create(res)
                        else:
                            res = {
                                'employee_id': emp.id,
                                'name': slip_data['value'].get('name'),
                                'struct_id': self.salary_scale.id,
                                'contract_id': emp.contract_id.id,
                                'input_line_ids': [(0, 0, x) for x in slip_data['value'].get('input_line_ids')],
                                'worked_days_line_ids': [(0, 0, x) for x in
                                                         slip_data['value'].get('worked_days_line_ids')],
                                'date_from': from_date,
                                'date_to': to_date,
                                'holiday_start_date': holiday_start_date,
                                'holiday_end_date': holiday_end_date,
                                'credit_note': self.credit_note,
                                'company_id': emp.company_id.id,
                                'percentage': self.percentage}
                            # if pays:
                            #     for p in pays:
                            #         if p.employee_id != emp and p not in payslips:
                            #             payslips += self.env['hr.payslip'].create(res)
                            # else:
                            payslips += self.env['hr.payslip'].create(res)
                    else:
                        if emp.leaving_date and str(emp.first_hiring_date) < from_date:
                            if str(emp.leaving_date) <= from_date:
                                pass
                            else:
                                payslips += employee_slip_line
                        else:
                            payslips += employee_slip_line

        payslips.compute_sheet()
        self.env['hr.payslip.line']._compute_total()
        for pay in payslips:
            if pay.total_sum < 0:
                dictionary.append(pay.employee_id.name)
        if dictionary:
            raise exceptions.Warning(
                _("Salary is less than 0 this month for the following employees \n %s") % (dictionary))
        self.slip_ids = payslips
        self.write({'state': 'computed'})

    def withdraw(self):
        for line in self.slip_ids:
            payslip = self.env['hr.payslip'].search([('number', '=', line.number)])
            loans = self.env['hr.loan.salary.advance'].search([('employee_id', '=', line.employee_id.id)])
            if line.number == payslip.number:
                if line.loan_ids:
                    for loan in line.loan_ids:
                        loan.paid = False
                        if loans:
                            for i in loans:
                                if i.id == loan.loan_id.id:
                                    for l in i.deduction_lines:
                                        if loan.date == l.installment_date and loan.paid is False:
                                            l.paid = False
                                            l.payment_date = False
                                           #i.remaining_loan_amount += l.installment_amount
                                            i.get_remaining_loan_amount()

                                    # check remaining loan and change state to pay
                                    if i.state == 'closed' and i.remaining_loan_amount > 0.0:
                                        i.state = 'pay'
                                    elif i.remaining_loan_amount == 0.0 and i.gm_propos_amount > 0.0:
                                        i.state = 'closed'
                for record in payslip:
                    record.write({'state': 'draft'})
                    record.unlink()
        self.write({'slip_ids': [(5,)]})
        self.write({'state': 'draft'})

    def unlink(self):
        if any(self.filtered(lambda payslip: payslip.state != 'draft')):
            raise UserError(_('You cannot delete a payslip which is not draft!'))
        return super(HrPayslipRun, self).unlink()

    def return_button(self):
        for line in self.slip_ids:
            payslip = self.env['hr.payslip'].search([('state', '=', line.state)])
            if payslip:
                if self.move_id:
                    if self.move_id.state == 'posted':
                        raise exceptions.Warning(
                            _('You can not Return account move %s in state not draft') % self.move_id.name)
                    else:
                        self.move_id.unlink()
                        self.move_id = False

                if line.move_id:
                    if line.move_id.state == 'posted':
                        raise exceptions.Warning(
                            _('You can not Return account move %s in state not draft') % line.move_id.name)
                    else:
                        line.move_id.unlink()
                        line.move_id = False

                line.write({'state': 'computed'})
        self.write({'state': 'computed'})

    def confirm(self):
        for line in self.slip_ids:
            payslip = self.env['hr.payslip'].search([('state', '=', line.state)])
            if payslip:
                line.write({'state': 'confirmed'})
        self.write({'state': 'confirmed'})

    def merge_lists(self, l1, key, key2):
        grupos = it.groupby(sorted(l1, key=itemgetter(key,key2)), key=itemgetter(key, key2))
        res = []
        for v, items in grupos:
            new_items = list(items)
            analytic_account_id = None
            if round(sum(dicc['debit'] for dicc in new_items),2) > 0:
                analytic_account_id = self.salary_scale.analytic_account_id.id
            res.append({
                'name': v[0],
                'account_id': v[1],
                'debit': round(sum(dicc['debit'] for dicc in new_items),2),
                'credit': round(sum(dicc2['credit'] for dicc2 in new_items),2),
                'analytic_account_id': analytic_account_id ,
            })
        return res

    def new_merge_lists(self, l1, key1, key2, key3):
        # groups = it.groupby(sorted(l1, key=itemgetter(key)), key=itemgetter(key, key2, key3))
        groups = it.groupby(sorted(l1, key=itemgetter(key1, key2, key3)), key=itemgetter(key1, key2, key3))
        res = []
        for v, items in groups:
            new_items = list(items)
            res.append({
                'name': v[0],
                'account_id': v[1],
                'analytic_account_id': v[2],
                'debit': sum(dicc['debit'] for dicc in new_items),
                'credit': sum(dicc2['credit'] for dicc2 in new_items)
            })
        return res

    def transfer(self):
        list_of_vals = []

        if self.salary_scale.transfer_type == 'all':
            total_of_list = []
            for line in self.slip_ids:
                emp_type = line.employee_id.employee_type_id.id
                total_allow, total_ded, total_loan = 0.0, 0.0, 0.0
                total_list = []
                total_loan_list = []
                move_vals = dict()
                journal = self.journal_id
                if list_of_vals:
                    for item in list_of_vals:
                        if item.get('move') == journal.id:
                            move_vals = item
                            break
                for l in line.allowance_ids:
                    amount_allow = l.total
                    # account = l.salary_rule_id.rule_debit_account_id
                    account = l.salary_rule_id.get_debit_account_id(emp_type)
                    if not account:
                        raise exceptions.Warning(
                            _('Sorry The Allowance %s is Not account Set') % l.name)
                    total_list.append({
                        'name': l.name,
                        'debit': amount_allow,
                        'journal_id': journal.id,
                        'credit': 0,
                        'account_id': account,
                    })
                    total_allow += amount_allow

                for ded in line.deduction_ids:
                    amount_ded = -ded.total
                    # account = ded.salary_rule_id.rule_credit_account_id
                    account = ded.salary_rule_id.get_credit_account_id(emp_type)
                    if not account:
                        raise exceptions.Warning(
                            _('Sorry The Deduction %s is Not account Set') % ded.name)
                    total_list.append({
                        'name': ded.name,
                        'credit': amount_ded,
                        'journal_id': journal.id,
                        'debit': 0,
                        'account_id': account,
                    })
                    total_ded += amount_ded

                for lo in line.loan_ids:
                    amount_loans = -lo.amount
                    if not lo.account_id:
                        raise exceptions.Warning(
                            _('Sorry The Loan %s is Not account Set') % lo.name)
                    loan_line_vals = {
                        'name': lo.name,
                        'credit': amount_loans,
                        'debit': 0,
                        'journal_id': journal.id,
                        'account_id': lo.account_id.id,
                        'partner_id': line.employee_id.user_id.partner_id.id,
                    }
                    total_loan_list.append(loan_line_vals)
                    total_loan += amount_loans

                    # credit_loans_vals = {
                    #     'name': lo.name,
                    #     'credit': amount_loans,
                    #     'journal_id': journal.id,
                    #     'debit': 0,
                    #     'account_id': lo.account_id.id,
                    # }
                    # total_list.append(credit_loans_vals)
                # create line for total of all allowance, deduction, loans of all employees
                total_of_list.append({
                    'name': "Total",
                    'journal_id': journal.id,
                    'partner_id': line.employee_id.user_id.partner_id.id,
                    'account_id': journal.default_account_id.id,
                    'credit': round(total_allow, 2) - round(total_ded, 2) - round(total_loan, 2),
                    'debit': 0,
                })
                if not move_vals:
                    move_vals.update({'move': journal.id, 'list_ids': total_list, 'loans': total_loan_list})
                    list_of_vals.append(move_vals)
                else:
                    new_list = move_vals.get('list_ids')
                    new_list.extend(total_list)
                    new_loan_list = move_vals.get('loans')
                    new_loan_list.extend(total_loan_list)
                    move_vals.update({'list_ids': new_list, 'loans': new_loan_list})

            for record in list_of_vals:
                new_record_list = record.get('list_ids') + [d for d in total_of_list if
                                                            d['journal_id'] == record.get('move')]
                new_rec_loan_list = record.get('loans')

                merged_list = self.merge_lists(new_record_list, 'name', 'account_id')
                record_final_item = merged_list + new_rec_loan_list
                if not self.move_id:
                   move = self.env['account.move'].create({
                       'state': 'draft',
                       'journal_id': record.get('move'),
                       # 'date': fields.Date.context_today(self),
                       'date': self.date_end,
                       'ref': self.name,
                       'line_ids': [(0, 0, item) for item in record_final_item],
                       'res_model': 'hr.payslip.run',
                       'res_id': self.id
                   })
                   self.move_id = move.id


        ########################## per_analytic_account ###########

        elif self.salary_scale.transfer_type == 'per_analytic_account':
            total_of_list = []
            journal = self.journal_id
            department_totals = {}  # Dictionary to store department-wise totals
            total_allow, total_ded, total_loan = 0.0, 0.0, 0.0
            for line in self.slip_ids:
                emp_type = line.employee_id.employee_type_id.id
                total_list = []
                total_loan_list = []
                move_vals = dict()
                journal = self.journal_id
                if list_of_vals:
                    for item in list_of_vals:
                        if item.get('move') == journal.id:
                            move_vals = item
                            break
                for l in line.allowance_ids:
                    amount_allow = l.total
                    # account = l.salary_rule_id.rule_debit_account_id
                    account = l.salary_rule_id.get_debit_account_id(emp_type)
                    if not account:
                        raise exceptions.Warning(
                            _('Sorry The Allowance %s is Not account Set') % l.name)
                    total_list.append({
                        'name': l.name,
                        'debit': amount_allow,
                        'journal_id': journal.id,
                        'credit': 0,
                        'account_id': account,
                        'analytic_account_id': line.employee_id.department_id.analytic_account_id.id,
                    })
                    total_allow += amount_allow
                for ded in line.deduction_ids:
                    amount_ded = -ded.total
                    account = ded.salary_rule_id.get_credit_account_id(emp_type)
                    # account = ded.salary_rule_id.rule_credit_account_id
                    if not account:
                        raise exceptions.Warning(
                            _('Sorry The Deduction %s is Not account Set') % ded.name)
                    total_list.append({
                        'name': ded.name,
                        'credit': amount_ded,
                        'journal_id': journal.id,
                        'debit': 0,
                        'account_id': account,
                        'analytic_account_id': None,
                    })
                    total_ded += amount_ded

                for lo in line.loan_ids:
                    amount_loans = -lo.amount
                    if not lo.account_id:
                        raise exceptions.Warning(
                            _('Sorry The Loan %s is Not account Set') % lo.name)
                    credit_loans_vals = {
                        'name': lo.name,
                        'credit': amount_loans,
                        'journal_id': journal.id,
                        'debit': 0,
                        'account_id': lo.account_id.id,
                        'analytic_account_id': None,
                        'partner_id': line.employee_id.user_id.partner_id.id,
                    }
                    total_loan += amount_loans
                    total_loan_list.append(credit_loans_vals)

                # Get the department of the employee
                department = line.employee_id.department_id

                # Add allowance amount to the department total
                if department in department_totals:
                    department_totals[department] += total_allow
                else:
                    department_totals[department] = total_allow
                if not move_vals:
                    move_vals.update({'move': journal.id, 'list_ids': total_list, 'loans': total_loan_list})
                    list_of_vals.append(move_vals)
                else:
                    new_list = move_vals.get('list_ids')
                    new_list.extend(total_list)
                    new_loan_list = move_vals.get('loans')
                    new_loan_list.extend(total_loan_list)
                    move_vals.update({'list_ids': new_list, 'loans': new_loan_list})

            total_of_list.append({
                'name': "Total",
                'journal_id': journal.id,
                'account_id': journal.default_account_id.id,
                'credit': total_allow - total_ded - total_loan,
                'debit': 0,
                'analytic_account_id': None,

            })

            # for department, allowance_total in department_totals.items():

            #     total_of_list.append({
            #         'name': f"Total ({department.analytic_account_id.name})",
            #         'journal_id': journal.id,
            #         'account_id': journal.default_credit_account_id.id,
            #         'credit': allowance_total - total_ded - total_loan,
            #         'analytic_account_id': department.analytic_account_id.id,
            #         'debit': 0,
            #     })

            for record in list_of_vals:
                new_record_list = record.get('list_ids') + [d for d in total_of_list if
                                                            d['journal_id'] == record.get('move')]
                new_rec_loan_list = record.get('loans')
                merged_list = self.new_merge_lists(new_record_list, 'name', 'account_id', 'analytic_account_id')
                record_final_item = merged_list + new_rec_loan_list
                if not self.move_id:
                   move = self.env['account.move'].create({
                       'state': 'draft',
                       'journal_id': record.get('move'),
                       'date': self.date_end,

                       'ref': self.name,
                       'line_ids': [(0, 0, item) for item in record_final_item],
                       'res_model': 'hr.payslip.run',
                       'res_id': self.id
                   })
                   self.move_id = move.id

            # import pdb
            # pdb.set_trace()
        #####################################

        elif self.salary_scale.transfer_type == 'one_by_one':
            for line in self.slip_ids:
                emp_type = line.employee_id.employee_type_id.id
                total_allow, total_ded, total_loan = 0.0, 0.0, 0.0
                total_list = []
                move_vals = dict()
                journal = line.contract_id.journal_id
                if not journal:
                   raise exceptions.Warning(
                           _('Sorry The Contract Employee %s is Not Journal Set') % line.employee_id.name)
                for l in line.allowance_ids:
                    amount_allow = l.total
                    # account = l.salary_rule_id.rule_debit_account_id
                    account = l.salary_rule_id.get_debit_account_id(emp_type)
                    if not account:
                        raise exceptions.Warning(
                            _('Sorry The Allowance %s is Not account Set') % l.name)
                    total_list.append({
                        'name': l.name,
                        'debit': amount_allow,
                        'partner_id': line.employee_id.user_id.partner_id.id,
                        'credit': 0,
                        'account_id': account,
                        'analytic_account_id': line.employee_id.contract_id.analytic_account_id.id,
                    })
                    total_allow += amount_allow

                for ded in line.deduction_ids:
                    amount_ded = -ded.total
                    # account = ded.salary_rule_id.rule_credit_account_id
                    account = ded.salary_rule_id.get_credit_account_id(emp_type)
                    if not account:
                        raise exceptions.Warning(
                            _('Sorry The Deduction %s is Not account Set') % ded.name)
                    total_list.append({
                        'name': ded.name,
                        'credit': amount_ded,
                        'partner_id': line.employee_id.user_id.partner_id.id,
                        'debit': 0,
                        'account_id': account,
                    })
                    total_ded += amount_ded

                for lo in line.loan_ids:
                    amount_loans = -lo.amount
                    if not lo.account_id:
                        raise exceptions.Warning(
                            _('Sorry The Loan %s is Not account Set') % lo.name)
                    credit_loans_vals = {
                        'name': lo.name,
                        'credit': amount_loans,
                        'partner_id': line.employee_id.user_id.partner_id.id,
                        'debit': 0,
                        'account_id': lo.account_id.id,
                    }
                    total_loan += amount_loans
                    total_list.append(credit_loans_vals)
                # create line for total of all allowance, deduction, loans of all employees
                total = total_allow - total_ded - total_loan
                total_list.append({
                    'name': line.name,
                    'partner_id': line.employee_id.user_id.partner_id.id,
                    'account_id': line.contract_id.journal_id.default_account_id.id,
                    'credit': total,
                    'debit': 0,
                })
                # print('total list', total_list)
                if not move_vals:
                    move_vals.update({'move': journal.id, 'list_ids': total_list})
                    list_of_vals.append(move_vals)
                else:
                    new_list = move_vals.get('list_ids')
                    new_list.extend(total_list)
                    move_vals.update({'list_ids': new_list})
                for record in list_of_vals:
                    new_record_list = record.get('list_ids')
                    # merged_list = self.merge_lists(new_record_list, 'name', 'account_id')
                    # record_final_item = merged_list
                if not line.move_id:
                   move = self.env['account.move'].create({
                       'state': 'draft',
                       'partner_id': line.employee_id.user_id.partner_id.id,
                       'journal_id': line.contract_id.journal_id.id,
                       # 'date': fields.Date.context_today(self),
                       'date': self.date_end,
                       'ref': line.name,
                       'line_ids': [(0, 0, item) for item in new_record_list],
                       'res_model': 'hr.payslip.run',
                       'res_id': self.id
                   })
                   line.move_id = move.id

        else:
            bank_id = ''
            for line in self.slip_ids:
                emp_type = line.employee_id.employee_type_id.id
                total_allow, total_ded, total_loan = 0.0, 0.0, 0.0
                total_list = []
                total_loan_list = []
                move_vals = dict()
                if line.employee_id.payment_method == 'bank':
                    journal = self.env['account.journal'].search([('type', '=', line.employee_id.payment_method),
                                                                  ], limit=1)

                    if not journal:
                        raise except_orm('Error', ' There is no journal For that Bank..'
                                                  ' Please define a sale journal')
                    if list_of_vals:
                        for item in list_of_vals:
                            if item.get('move') == journal.id:
                                move_vals = item
                                break
                    for l in line.allowance_ids:
                        amount_allow = l.total
                        # account = l.salary_rule_id.rule_debit_account_id
                        account = l.salary_rule_id.get_debit_account_id(emp_type)
                        if not account:
                            raise exceptions.Warning(
                                _('Sorry The Allowance %s is Not account Set') % l.name)
                        total_list.append({
                            'name': l.name,
                            'debit': amount_allow,
                            'journal_id': journal.id,
                            'credit': 0,
                            'account_id': account,
                        })
                        total_allow += amount_allow

                    for ded in line.deduction_ids:
                        amount_ded = -ded.total
                        # account = ded.salary_rule_id.rule_credit_account_id
                        account = ded.salary_rule_id.get_credit_account_id(emp_type)
                        if not account:
                            raise exceptions.Warning(
                                _('Sorry The Deduction %s is Not account Set') % ded.name)
                        total_list.append({
                            'name': ded.name,
                            'credit': amount_ded,
                            'journal_id': journal.id,
                            'debit': 0,
                            'account_id': account,
                        })
                        total_ded += amount_ded

                    for lo in line.loan_ids:
                        amount_loans = -lo.amount
                        if not lo.account_id:
                            raise exceptions.Warning(
                                _('Sorry The Loan %s is Not account Set') % lo.name)
                        credit_loans_vals = {
                            'name': lo.name,
                            'credit': amount_loans,
                            'journal_id': journal.id,
                            'debit': 0,
                            'account_id': lo.account_id.id,
                            'partner_id': line.employee_id.user_id.partner_id.id,
                        }
                        total_loan += amount_loans
                        total_loan_list.append(credit_loans_vals)
                    # create line for total of all allowance, deduction, loans of all employees
                    total_list.append({
                        'name': "Total",
                        'journal_id': journal.id,
                        'account_id': journal.default_account_id.id,
                        'credit': total_allow - total_ded - total_loan,
                        'debit': 0,
                    })
                    if not move_vals:
                        move_vals.update({'move': journal.id, 'list_ids': total_list, 'loans': total_loan_list})
                        list_of_vals.append(move_vals)
                    else:
                        new_list = move_vals.get('list_ids')
                        new_list.extend(total_list)
                        new_loan_list = move_vals.get('loans')
                        new_loan_list.extend(total_loan_list)
                        move_vals.update({'list_ids': new_list, 'loans': new_loan_list})
                    bank_id = line.employee_id.bank_account_id.bank_id.name

                elif line.employee_id.payment_method == 'cash':
                    amount, amount1, amount2 = 0.0, 0.0, 0.0

                    for l in line.allowance_ids:
                        amount_allow = l.total
                        # account = l.salary_rule_id.rule_debit_account_id
                        account = l.salary_rule_id.get_debit_account_id(emp_type)
                        if not account:
                            raise exceptions.Warning(
                                _('Sorry The Allowance %s is Not account Set') % l.name)
                        total_list.append({
                            'name': l.name,
                            'account_id': account,
                            'debit': amount_allow,
                            'credit': 0,
                            'partner_id': line.employee_id.user_id.partner_id.id
                        })
                        amount += amount_allow
                    total_allow += amount

                    for ded in line.deduction_ids:
                        amount_ded = -ded.total
                        # account = ded.salary_rule_id.rule_credit_account_id
                        account = ded.salary_rule_id.get_credit_account_id(emp_type)
                        if not account:
                            raise exceptions.Warning(
                                _('Sorry The Deduction %s is Not account Set') % ded.name)
                        total_list.append({
                            'name': ded.name,
                            'account_id': account,
                            'credit': amount_ded,
                            'debit': 0,
                            'partner_id': line.employee_id.user_id.partner_id.id
                        })
                        amount1 += amount_ded
                    total_ded += amount1

                    for lo in line.loan_ids:
                        amount_loans = -lo.amount
                        if not lo.account_id:
                            raise exceptions.Warning(
                                _('Sorry The Loan %s is Not account Set') % lo.name)
                        total_list.append({
                            'name': lo.name,
                            'account_id': lo.account_id.id,
                            'credit': amount_loans,
                            'debit': 0,
                            'partner_id': line.employee_id.user_id.partner_id.id
                        })
                        amount2 += amount_loans
                    total_loan += amount2

                    # create line for total of all allowance, deduction, loans of one employee
                    total = total_allow - total_ded - total_loan
                    total_list.append({
                        'name': "Total",
                        'account_id': line.contract_id.journal_id.default_account_id.id,
                        'partner_id': line.employee_id.user_id.partner_id.id,
                        'credit': round(total, 1),
                        'debit': 0,
                    })
                    move = self.env['account.move'].create({
                        'journal_id': line.contract_id.journal_id.id,
                        # 'date': fields.Date.context_today(self),
                        'date': self.date_end,
                        'ref': "Cash",
                        'line_ids': [(0, 0, item) for item in total_list]
                    })

            for record in list_of_vals:
                new_record_list = record.get('list_ids')
                new_rec_loan_list = record.get('loans')
                merged_list = self.merge_lists(new_record_list, 'name', 'account_id')
                record_final_item = merged_list + new_rec_loan_list
                if not line.move_id:
                   move = self.env['account.move'].create({
                       'state': 'draft',
                       'journal_id': record.get('move'),
                       # 'date': fields.Date.context_today(self),
                       'date': self.date_end,
                       'ref': bank_id,
                       'line_ids': [(0, 0, item) for item in record_final_item],
                       'res_model': 'hr.payslip.run',
                       'res_id': self.id
                   })
                   line.move_id = move.id

        for line in self.slip_ids:
            payslip = self.env['hr.payslip'].search([('state', '=', line.state)])
            if payslip:
                line.write({'state': 'transfered'})
        self.write({'state': 'transfered'})
