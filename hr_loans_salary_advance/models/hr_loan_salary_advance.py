# -*- coding: utf-8 -*-
from __future__ import division
from odoo import models, fields, api, _, exceptions
from dateutil import relativedelta
from odoo.exceptions import UserError
from odoo.tools.safe_eval import safe_eval
from datetime import datetime, date


class HrSalaryAdvance(models.Model):
    _name = 'hr.loan.salary.advance'
    _rec_name = 'employee_id'
    _description = 'Employee Loan'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date DESC'

    code = fields.Char()
    state = fields.Selection(
            [('draft', _('Draft')), 
             ('submit', _('Waiting Payroll Officer')),
             ('direct_manager', _('Wait HR Department')),
             ('hr_manager', _('Wait GM Approval')),
             ('executive_manager', _('Wait Transfer')),
             ('pay', _('Transferred')), ('refused', _('Refused')),
             ('closed', _('Loan Suspended'))],
        default="draft", tracking=True)
    date = fields.Date()
    from_hr_depart = fields.Boolean()
    is_old = fields.Boolean()
    months_employeed = fields.Float(compute='_get_month_no')
    evaluation_grade = fields.Many2one(related='employee_id.contract_id.appraisal_result_id', readonly=True)
    contract_duration_date = fields.Date(related='employee_id.contract_id.date_start')
    payment_ref = fields.Char()
    basic_amount = fields.Float(string='Basic Amount')
    emp_expect_amount = fields.Float(string='Request Employee Amount')
    finance_propos_amount = fields.Float(compute='_get_finance_gm_propos_amount', store=True)
    gm_propos_amount = fields.Float(compute='_get_finance_gm_propos_amount', store=True,string='Approved Amount')
    months = fields.Integer(default=1)
    monthly_salary = fields.Float()
    total_paid_inst = fields.Float(compute='get_total_paid_installment', store=True)
    remaining_loan_amount = fields.Float(compute='get_remaining_loan_amount', store=True)
    installment_amount = fields.Float(compute='get_installment_amount', store=True)
    # previous_loan = fields.Boolean()
    end_date = fields.Date(related='employee_id.contract_id.date_end')

    # Relational fields
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    job_id = fields.Many2one(related='employee_id.job_id', readonly=True)
    department_id = fields.Many2one(related='employee_id.department_id', readonly=True, store=True)
    deduction_lines = fields.One2many('loan.installment.line', 'deduction_line')
    moves_ids = fields.One2many('hr.account.moves', 'moves_id')
    employee_id = fields.Many2one('hr.employee', 'Employee',
                                  default=lambda item: item.get_user_id(), index=True, domain=[('state', '=', 'open')])
    employee_no = fields.Char(related='employee_id.emp_no', readonly=True,string='Employee Number', store=True)
    request_type = fields.Many2one('loan.request.type')
    emp_hiring_date = fields.Date(related='employee_id.contract_id.hiring_date')

    exception_loan = fields.Boolean(help='Exception The Required Loan Amount Or The Number Of Installments,For The Human Resources Manager')

    # change state to piad

    @api.onchange('employee_id', 'request_type')
    def check_hiring_date(self):
        if self.employee_id:
            if not self.employee_id.first_hiring_date:
                raise exceptions.Warning(
                    _('You can not Request Loans The Employee %s have Not First Hiring Date')
                    % self.employee_id.name)

    def name_get(self):
        return [(loan.id, '%s  %s' % (loan.code, loan.request_type.name)) for loan in self]

    def to_re_paid(self):

        if self.state == 'closed' and self.remaining_loan_amount == 0:
            raise exceptions.Warning(_('You can not Re-Paid Loan because Loan is Finished'))

        else:
            self.state = "pay"

    # change state to draft

    def draft_state(self):
        for item in self:
            if item.state == 'closed' and item.remaining_loan_amount == 0:
                raise exceptions.Warning(_('You can not Re-draft Loan because Loan is Finished'))
            if item.moves_ids:
                for line in item.moves_ids:
                    if line.journal_move_id:
                        if line.journal_move_id.state == 'draft':
                            # line.journal_move_id.state = 'canceled'
                            line.journal_move_id.sudo().unlink()
                            line.sudo().unlink()
                            item.state = 'draft'
                        else:
                            raise exceptions.Warning(_(
                                'You can not re-draft Loan because account move with ID "%s" in state Posted')
                                                     % line.journal_move_id.name)
                    else:
                        line.unlink()
                        item.state = 'draft'
            else:
                item.state = 'draft'

    # change state to submit

    def submit(self):
        for item in self:
            
            if item.employee_id.state != 'open':
                raise exceptions.Warning(_('You Can Not Submit Loan where Employee %s Not In Service')
                                         % item.employee_id.name)
            item.create_loan()
            if item.request_type.year > (item.months_employeed / 12):
                raise exceptions.Warning(_('You can not submit loan when your total service is less than number '
                                           'of years'))
            deductions = item.deduction_lines
            
            # if len(deductions) == 0:
            #     raise exceptions.Warning(_('You must create al least one installment'))
            if len(deductions) != item.months:
                raise exceptions.Warning(
                    _("The Number of actual installments is less than %s Installments, Re-click on the "
                      "Create Loan Button") % item.months)
            """else:
                mail_content = "Hello I'm", item.employee_id.name, " request Need to ", item.request_type.name, \
                               "Amount", item.emp_expect_amount, "Please approved thanks :)."
                main_content = {
                    'subject': _('Request Loan-%s Employee %s') % (item.request_type.name, item.employee_id.name),
                    'author_id': self.env.user.partner_id.id,
                    'body_html': mail_content,
                    'email_to': item.department_id.email_manager,
                }
                self.env['mail.mail'].create(main_content).send()"""
        self.percentage_constrain()
        self.state = "submit"

    def direct_manager(self):
        self.state = "direct_manager"

    def hr_manager(self):
        self.state = "hr_manager"

    def executive_manager(self):
        self.state = "executive_manager"

    # change state to pay

    def pay(self):
        for item in self:
            if item.is_old is False:
                debit_line_vals = {
                    'name': 'debit',
                    'debit': item.gm_propos_amount,
                    'account_id': item.request_type.account_id.id,
                    'partner_id': item.employee_id.user_id.partner_id.id
                }
                credit_line_vals = {
                    'name': 'credit',
                    'credit': item.gm_propos_amount,
                    'account_id': item.request_type.journal_id.default_account_id.id,
                    'partner_id': item.employee_id.user_id.partner_id.id
                }
                move = self.env['account.move'].create({
                    'state': 'draft',
                    'journal_id': item.request_type.journal_id.id,
                    'date': item.date,
                    'ref': 'Loan',
                    'line_ids': [(0, 0, debit_line_vals), (0, 0, credit_line_vals)],
                    'res_model': 'hr.loan.salary.advance',
                    'res_id': self.id
                })
                if not item.moves_ids:
                   self.env['hr.account.moves'].create({
                       'number': item.code,
                       'amount': item.gm_propos_amount,
                       'journal': item.request_type.journal_id.id,
                       'partner_id': item.employee_id.user_id.partner_id.id,
                       'date': item.date,
                       'journal_move_id': move.id,
                       'moves_id': item.id })

        self.state = "pay"

    def refused(self):
        for item in self:
            for line in item.deduction_lines:
                if line.paid is True:
                    raise exceptions.Warning(_('You can not Refuse Loan because Loan with Deduction in Salary'))

                else:
                    item.state = "refused"

    def closed(self):
        self.state = "closed"

    def cancel(self):
        self.state = "cancel"

    def get_user_id(self):
        employee_id = self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)
        if employee_id:
            return employee_id.id
        else:
            return False

    def create_loan(self):
        for item in self:
            if item.gm_propos_amount <=0:
               raise exceptions.Warning(_("Sorry, Approved Amount Must Be Greater Than Zero"))

            if item.contract_duration_date:
                if item.end_date:
                    if item.months <= item.months_employeed:
                        date_start = fields.Datetime.from_string(item.date)

                        items = []
                        for number in range(item.months):
                            dt = date_start + relativedelta.relativedelta(months=number)
                            date_end = fields.Datetime.to_string(dt)
                            seq = number + 1
                            record_id = self.env['loan.installment.line'].create({
                                'sequence': seq,
                                'installment_date': date_end,
                                'installment_amount': item.installment_amount,
                                'paid': False
                            })
                            items.append(record_id.id)
                        item.deduction_lines = self.env['loan.installment.line'].browse(items)
                    else:
                        raise exceptions.Warning(
                            _('The number of installments does not exceed the employee contract period.'))

                else:
                    date_start = fields.Datetime.from_string(item.date)

                    items = []
                    for number in range(item.months):
                        dt = date_start + relativedelta.relativedelta(months=number)
                        date_end = fields.Datetime.to_string(dt)
                        seq = number + 1
                        record_id = self.env['loan.installment.line'].create({
                            'sequence': seq,
                            'installment_date': date_end,
                            'installment_amount': item.installment_amount,
                            'paid': False
                        })
                        items.append(record_id.id)
                    item.deduction_lines = self.env['loan.installment.line'].browse(items)
            else:
                raise exceptions.Warning(_('The employee does not have contract Start Date .'))
            install_false = self.env['loan.installment.line'].search([('deduction_line', '=', False)]).unlink()
        self._onchange_emp_expect_amount()

    # @api.constrains('deduction_lines')
    # def deduction_lines_constraine(self):
    #     for item in self:
    #         deductions = item.deduction_lines
    #         if len(deductions) == 0:
    #             raise exceptions.Warning(_('You must create al least one installment'))

    @api.depends('gm_propos_amount', 'months')
    def get_installment_amount(self):
        for item in self:
            item.installment_amount = 0
            if item.gm_propos_amount > 0.0 and item.months > 0:
                item.installment_amount = item.gm_propos_amount / float(item.months)

    @api.depends('contract_duration_date', 'end_date')
    def _get_month_no(self):
        for item in self:
            if item.employee_id.contract_id:
                hiring = item.employee_id.contract_id.hiring_date
                if hiring:
                    start_contract_date = datetime.strptime(str(hiring), "%Y-%m-%d")
                else:
                    start_contract_date = datetime.strptime(str(item.contract_duration_date), "%Y-%m-%d")

                if item.contract_duration_date and item.end_date:
                    end_contract_date = datetime.strptime(str(item.end_date), "%Y-%m-%d")
                    relative_months = relativedelta.relativedelta(end_contract_date, start_contract_date).months +1
                    relative_years = relativedelta.relativedelta(end_contract_date, start_contract_date).years
                    item.months_employeed = relative_months + (relative_years * 12)

                else:

                    current_date = date.today()
                    relative_months = relativedelta.relativedelta(current_date, start_contract_date).months +1
                    relative_years = relativedelta.relativedelta(current_date, start_contract_date).years
                    item.months_employeed = relative_months + (relative_years * 12)
            else:
                raise exceptions.Warning(_('Employee %s has no contract') % item.employee_id.name)

    @api.depends('deduction_lines','deduction_lines.paid')
    def get_total_paid_installment(self):
        for item in self:
            tota_number = 0.0
            if item.employee_id.id:
                for line in item.deduction_lines:
                    if line.paid is True:
                        tota_number += line.installment_amount
                item.total_paid_inst = tota_number

    @api.depends('deduction_lines','total_paid_inst')
    def get_remaining_loan_amount(self):
        for item in self:
            item.remaining_loan_amount = item.gm_propos_amount - item.total_paid_inst

    # @api.constrains('deduction_lines')
    # def deduction_lines_constrain(self):
    #     for item in self:
    #         deductions = item.deduction_lines
    #         if len(deductions) == 0:
    #             raise exceptions.Warning(_('You must create al least one installment'))

    @api.depends('emp_expect_amount')
    def _get_finance_gm_propos_amount(self):
        for item in self:
            if item.emp_expect_amount:
                item.finance_propos_amount = item.emp_expect_amount
                item.gm_propos_amount = item.emp_expect_amount

    # percentage constrain depending on the sart date
    @api.constrains('date')
    def percentage_constrain(self):
        if self.emp_hiring_date:
            if self.date < self.emp_hiring_date:
                raise exceptions.Warning(_('The Request date must be after Hiring Data'))
        records = self.env['hr.loan.salary.advance'].search(
            [('employee_id', '=', self.employee_id.id), ('date', '=', self.date), ('state', '=', 'pay')])
        total_number = 0.0

        # Get all un paid installments from all loans that it's state is pay and it's date is this loan date
        # in "total_number"
        for item in records:
            for line in item.deduction_lines:

                if line.paid is False and line.installment_date == item.date:
                    total_number += line.installment_amount

        # Adding to total_number all intallments that not paid in current loan
        for item in self:
            for line in item.deduction_lines:
                if line.paid is False and line.installment_date == item.date:
                    total_number += line.installment_amount

        # Check if [exp_payroll_custom] module is installed
        Module = self.env['ir.module.module'].sudo()
        modules = Module.search([('state', '=', 'installed'), ('name', '=', 'exp_payroll_custom')])

        if modules:
            # get payslip by check if the loan date is in "Date from - Date to" in payslip
            '''records = self.env['hr.payslip'].search([('employee_id','=', self.employee_id.id),
                                                     ('date_from','<=',self.date),
                                                     ('date_to','>=',self.date)])'''
            emp_deduction = item.employee_id.contract_id.total_deduction
            # adding total deductions to total_number
            # for record in records:
            #   total_number += record.total_deductions - recordss

            total_number = total_number - emp_deduction
        percentage = self.request_type.percentage / 100
        percentage_salary = self.monthly_salary * percentage

        if percentage_salary < total_number:
            raise exceptions.Warning(
                _('The total number of installment of all months in start date is greater than the salary percentage'))

    @api.onchange('request_type')
    def _get_employee_expect_amount(self):

        # Initialize component
        self.emp_expect_amount = 0.0
        self.gm_propos_amount = 0.0
        self.months = self.request_type.installment_number
        if self.request_type.loan_type == 'percentage':
            total = 0.0
            for rule in self.request_type.allowance_id:
                if self.employee_id:
                    if self.employee_id.contract_id:
                        total += self._compute_rule(rule, self.employee_id.contract_id)
                    else:
                        raise exceptions.Warning(_("Employee '%s' has no contract") % self.employee_id.name)
            if self.request_type.factor > 0:
                self.basic_amount = total * self.request_type.factor
                self.emp_expect_amount = total * self.request_type.factor
            else:
                self.basic_amount = total
                self.emp_expect_amount = total
        else:
            self.basic_amount = self.request_type.amount
            self.emp_expect_amount = self.request_type.amount

    @api.onchange('emp_expect_amount','gm_propos_amount','months')
    def _onchange_emp_expect_amount(self):
        if self.exception_loan==False :
           if self.emp_expect_amount > self.basic_amount >0:
              raise exceptions.Warning(_("Sorry, Request Employee Amount Exceeds The Basic Amount"))
           if self.gm_propos_amount > self.basic_amount >0:
              raise exceptions.Warning(_("Sorry, Approved Amount Exceeds The Basic Amount"))
           if self.months > self.request_type.installment_number >0:
              raise exceptions.Warning(_("Sorry, The Number Of installments Must Not Exceed '%s' Installments")% self.request_type.installment_number)

        if self.request_type.refund_from == 'bonus':
            if not self.employee_id.contract_id:
                raise exceptions.Warning(_("Employee '%s' has no contract") % self.employee_id.name)
            if self.emp_expect_amount > self._compute_rule(self.request_type.bonus_id, self.employee_id.contract_id):
                raise exceptions.Warning(_("Sorry loan amount for %s exceeds the bonus amount") % self.employee_id.name)

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

    # Override write function
    def write(self, value):
        result = super(HrSalaryAdvance, self).write(value)
        return result

    # override unlink function
    def unlink(self):
        for item in self:
            if item.state != 'draft':
                raise exceptions.Warning(_('You can not delete record in state not in draft'))

            if item.total_paid_inst > 0.0:
                raise exceptions.Warning(_('You can not delete record when total paid installment greater than zero'))
            item.deduction_lines.unlink()
        return super(HrSalaryAdvance, self).unlink()

    # override create function
    @api.model
    def create(self, values):
        seq = self.env['ir.sequence'].next_by_code('hr.loan.salary.advance') or '/'
        values['code'] = seq
        res = super(HrSalaryAdvance, self).create(values)

        res.finance_propos_amount = values.get("finance_propos_amount", False)
        res.gm_propos_amount = values.get("gm_propos_amount", False)

        get_loans = self.env['hr.loan.salary.advance'].search([('employee_id', '=', res.employee_id.id),('state', '!=', 'refused'), 
                                                               ('request_type', '=', res.request_type.id)])

        total_installment = 0.0

        for item in get_loans:
            if item.request_type.number_of_request == 'once' and res.request_type.number_of_request == 'once' \
                    and item.id != res.id:
                raise exceptions.Warning(
                    _('You can not create loan that have request type with number of request is once.'))

            if item.request_type.id == res.request_type.id:
                if res.request_type.allow_overlapping is False:
                    for line in item.deduction_lines:
                        if line.paid is False:
                            raise exceptions.Warning(
                                _('You can not create loan when there is un paid loan with the same type.'))

                        total_installment += line.installment_amount
        return res


class LoanInstallmentLine(models.Model):
    _name = 'loan.installment.line'
    _rec_name = 'installment_date'
    _order = 'installment_date asc'

    sequence = fields.Integer()
    installment_date = fields.Date()
    installment_amount = fields.Float()
    paid = fields.Boolean()
    payment_date = fields.Date()
    # Relational fields
    deduction_line = fields.Many2one(comodel_name='hr.loan.salary.advance')
    reward_line_id = fields.Many2one(comodel_name='lines.ids.reward')
    termination_paid = fields.Boolean(default=False)

    def postpone_of_installment(self):
        action = self.env.ref('hr_loans_salary_advance.loan_installment_line_action').read()[0]
        action['views'] = [(self.env.ref('hr_loans_salary_advance.loan_installment_line_form_view').id, 'form')]
        action['res_id'] = self.id
        action['target'] = 'new'
        return action

    # Override create function
    def refresh_page(self):
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    # Override write function
    def write(self, value):
        result = super(LoanInstallmentLine, self).write(value)
        # self.refresh_page()
        return result


class LoanRequestType(models.Model):
    _name = 'loan.request.type'
    _rec_name = 'name'


    code = fields.Char()
    name = fields.Char(translate=True)
    loan_type = fields.Selection(selection=[('fixed_amount', _('Fixed Amount')),
                                            ('percentage', _('Percentage of salary'))], default='fixed_amount')
    number_of_request = fields.Selection(selection=[('unlimited', _('unlimited')), ('once', _('Once'))],
                                         default='unlimited')
    allow_overlapping = fields.Boolean()
    factor = fields.Integer()
    percentage = fields.Float()
    amount = fields.Float()
    year = fields.Integer()
    no_month_allowed = fields.Integer()

    # Relational fields
    allowance_id = fields.Many2many('hr.salary.rule')
    journal_id = fields.Many2one('account.journal')
    account_id = fields.Many2one('account.account')
    refund_from = fields.Selection(selection=[('salary', ('Salary')),
                                              ('bonus', ('Bonus')),
                                              ('termination', ('Termination'))], default='salary')
    bonus_id = fields.Many2one('hr.salary.rule')
    loan_deduction_id = fields.Many2one('hr.salary.rule', string='Loan Deduction',
                                        help='This deduction will be used if the Bonus will be paid in the salary')
    installment_number = fields.Integer(default=1)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

    def unlink(self):
        for item in self:
            i = self.env['hr.loan.salary.advance'].search([('request_type', '=', item.id)])
            if i:
                raise exceptions.Warning(
                    _('You can not delete record There is a related other record code %s Request Loan') % i.code)
        return super(LoanRequestType, self).unlink()


class AccountMoves(models.Model):
    _name = 'hr.account.moves'

    number = fields.Char()
    reference = fields.Char()
    date = fields.Date()
    period = fields.Char()
    amount = fields.Float()
    status = fields.Boolean()

    # relational fields
    journal = fields.Many2one(comodel_name='account.journal')
    moves_id = fields.Many2one(comodel_name='hr.loan.salary.advance')
    partner_id = fields.Many2one(comodel_name='res.partner')
    journal_move_id = fields.Many2one(comodel_name='account.move')
