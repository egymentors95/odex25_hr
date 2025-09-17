# -*- coding: utf-8 -*
from odoo import models, fields, api, _, exceptions
from odoo.exceptions import UserError, except_orm
from odoo.tools.safe_eval import safe_eval
from datetime import datetime


class ReconcileLeaves(models.Model):
    _name = 'reconcile.leaves'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'employee_id'
    _description = 'Reconcile Leaves'

    date = fields.Date()
    contract_start_date = fields.Date(related='employee_id.contract_id.date_start')
    contract_end_date = fields.Date(related='employee_id.contract_id.date_end')
    start_vacation_date = fields.Datetime(related='yearly_vacation.date_from')
    end_vacation_date = fields.Datetime(related='yearly_vacation.date_to')
    leave_duration = fields.Float()
    leave_amount = fields.Float()
    salary = fields.Float()
    total_allowance = fields.Float()
    total_deduction = fields.Float()
    total_loans = fields.Float()
    net = fields.Float()
    state = fields.Selection(selection=[
        ("draft", _("Draft")),
        ("submit", _("Submit")),
        ("direct_manager", _("Direct Manager")),
        ("hr_manager", _("HR Manager")),
        ("finance_manager", _("Finance Manager")),
        ("gm_manager", _("GM Manager")),
        ("pay", _("Pay")),
        ("refuse", _("Refuse"))], default='draft', tracking=True)

    # Relational fields
    employee_id = fields.Many2one('hr.employee')
    department_id = fields.Many2one('hr.department', related='employee_id.department_id')
    job_id = fields.Many2one('hr.job', related='employee_id.job_id')
    contract_id = fields.Many2one('hr.contract', related='employee_id.contract_id')
    yearly_vacation = fields.Many2one('hr.holidays', )
    calculation_method = fields.Many2many('hr.salary.rule')
    journal_id = fields.Many2one('account.journal')
    account_id = fields.Many2one('account.account')
    allowance_deduction = fields.One2many('reconcile.allowance.deduction', 'reconcile_id')
    journal_entry_ids = fields.One2many('reconcile.allowance.journal', 'journal_entry_ids_lines')
    account_move_id = fields.Many2one('account.move')
    loans_ids = fields.Many2many(
        'hr.loan.salary.advance',
        domain="[('employee_id','=','self.employee_id.id'),('state','=','pay'),('months','=','1')]")

    def unlink(self):
        for item in self:
            if item.state != 'draft':
                raise exceptions.Warning(_('You can not delete record in state not in draft'))
        return super(ReconcileLeaves, self).unlink()

    # To get salary rules from holiday setting
    @api.onchange('yearly_vacation')
    def _get_salary_rule(self):
        for rec in self:
            rec.calculation_method = False
            if rec.yearly_vacation:
                rec.calculation_method = rec.yearly_vacation.holiday_status_id.salary_rules_ids.ids
            else:
                rec.calculation_method = False

    # one reconcile holiday for each holiday request

    @api.constrains('yearly_vacation')
    def constain_holiday_request(self):
        for rec in self:
            holdiay_req = self.env['reconcile.leaves'].search([('employee_id', '=', rec.employee_id.id),
                                                               ('yearly_vacation', '=', rec.yearly_vacation.id)])
            for itms in holdiay_req:
                if len(holdiay_req) > 1:
                    raise exceptions.Warning(
                        _('This Holiday Request Has Been Reconcile %s') % rec.yearly_vacation.display_name)

    # default loans lines and domain
    @api.onchange('employee_id')
    def _get_loans_ids_and_domain(self):
        record_list = []
        record_ids = self.env['hr.loan.salary.advance'].search(
            [('employee_id', '=', self.employee_id.id), ('state', '=', 'pay'), ('months', '=', '1')])
        for item in record_ids:
            if item.remaining_loan_amount > 0:
                record_list.append(item.id)
        for line in self:
            line.loans_ids = record_list
            # rec.yearly_vacation = False
            domain = [('employee_id', '=', line.employee_id.id), ('state', '=', 'validate1')]
            res = {'domain': {'loans_ids': [('id', 'in', record_ids.ids)],
                              'yearly_vacation': domain}}
            return res
        #
        # return {'domain': {'loans_ids': [('id', 'in', record_ids.ids)],
        #                    'yearly_vacation': domain}}

    # dynamic domain for yearly_vacation when employee_id changed
    @api.onchange('employee_id')
    def onchange_employee_id(self):
        for rec in self:
            # rec.yearly_vacation = False
            domain = [('employee_id', '=', rec.employee_id.id), ('state', '=', 'validate1')]
            res= {'domain': {'yearly_vacation': domain}}
            return res

    # compute leave duration when change yearly_vacation
    @api.onchange('yearly_vacation', 'calculation_method')
    def compute_leave_duration(self):
        self.leave_amount, self.leave_duration = 0.0, 0.0

        if self.start_vacation_date and self.end_vacation_date:
            date_start = datetime.strptime(str(self.start_vacation_date), "%Y-%m-%d %H:%M:%S")
            date_end = datetime.strptime(str(self.end_vacation_date), "%Y-%m-%d %H:%M:%S")
            days_start = date_start.day
            days_end = date_end.day
            duration = date_end - date_start
            if days_start == 31 or days_end == 31:  # payroll for 30 days
                self.leave_duration = duration.days
            else:
                self.leave_duration = duration.days + 1

            if self.salary:
                if self.leave_duration > 0:
                    self.leave_amount = self.salary / (30 / self.leave_duration)

    # Compute employee salary when calculation method changed
    @api.onchange('yearly_vacation', 'calculation_method', 'employee_id', 'loans_ids')
    def compute_employee_salary_fom_calculation_method(self):
        # Initialize fields values
        self.salary, self.total_allowance, self.total_deduction, self.total_loans, self.net = 0.0, 0.0, 0.0, 0.0, 0.0

        if self.calculation_method:
            # initialize variables
            total = 0.0
            allowance_deduction_list = []

            for item in self.calculation_method:
                # check if there is a contract
                if self.contract_id:
                    # Check if item in calculation method is deduction or allowance to subtract or add
                    if item.category_id.rule_type == 'deduction':
                        total -= self.compute_rule(item, self.contract_id)
                    else:
                        total += self.compute_rule(item, self.contract_id)

                    if self.leave_duration > 0:
                        record = self.env['reconcile.allowance.deduction'].create({
                            'salary_rule_id': item.id,
                            'amount': (self.compute_rule(item, self.contract_id) / (30 / self.leave_duration))})
                        allowance_deduction_list.append(record.id)
                else:
                    raise exceptions.Warning(_('Employee "%s" has no contract') % self.employee_id.name)

            self.allowance_deduction = self.env['reconcile.allowance.deduction'].browse(allowance_deduction_list)
            self.salary = total

            # Compute total allowance , total deduction and net
            if self.allowance_deduction:
                for item in self.allowance_deduction:
                    if item.category_id.rule_type == 'allowance':
                        self.total_allowance += item.amount
                    elif item.category_id.rule_type == 'deduction':
                        self.total_deduction += item.amount
                self.net = self.total_allowance - self.total_deduction
        else:
            self.salary, self.total_allowance, self.total_deduction, self.net = 0.0, 0.0, 0.0, 0.0
            self.allowance_deduction = self.env['reconcile.allowance.deduction'].browse([])

        # Compute total loans and net
        if self.loans_ids:
            for line in self.loans_ids:
                self.total_loans += line.remaining_loan_amount
            self.net -= self.total_loans
        else:
            self.total_loans = 0.0

    # Compute salary rules

    def compute_rule(self, rule, contract):
        localdict = dict(employee=contract.employee_id, contract=contract)

        if rule.amount_select == 'percentage':
            total_percent = 0
            if rule.related_benefits_discounts:
                for line in rule.related_benefits_discounts:
                    if line.amount_select == 'fix':
                        total_percent += self.compute_rule(line, contract)
                    elif line.amount_select == 'percentage':
                        total_percent += self.compute_rule(line, contract)
                    else:
                        total_percent += self.compute_rule(line, contract)
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
            return rule._compute_rule(localdict)[0]

        else:
            return rule._compute_rule(localdict)[0]

    # change state to draft and cancel account move if it's state draft
    def re_draft(self):
        if self.account_move_id:
            if self.account_move_id.state == 'draft':
                # self.account_move_id.state = 'canceled'
                self.account_move_id.unlink()
                self.account_move_id = False
            else:
                raise exceptions.Warning(_(
                    'You can not re-draft reconcile leaves because account move with ID "%s" in state Posted') % self.account_move_id.name)

            for item in self.loans_ids:
                last_date = datetime.strptime(str(self.write_date), "%Y-%m-%d %H:%M:%S").date().month
                for install in item.deduction_lines:
                    loan_date = datetime.strptime(str(install.write_date), "%Y-%m-%d %H:%M:%S").date().month
                    if loan_date >= last_date and install.paid == True:
                        install.paid = False
                        item.state = 'pay'
        self.state = 'draft'

    # change state to submit
    def submit(self):
        self.constain_holiday_request()
        self.state = 'submit'

    # change state to direct_manager
    def direct_manager(self):
        self.state = 'direct_manager'

    # change state to hr_manager
    def hr_manager(self):
        self.state = 'hr_manager'

    # change state to finance_manager
    def finance_manager(self):
        self.state = 'finance_manager'

    # change state to gm_manager
    def gm_manager(self):
        self.state = 'gm_manager'

    # change state to create_journal_entry
    def pay(self):
        line_vals = []
        if self.allowance_deduction:
            for item in self.allowance_deduction:
                # check if amount greater than 0.0 to fill move account lines
                if item.amount > 0.0:
                    # check for deduction credit account
                    if item.salary_rule_id.category_id.rule_type == 'deduction':
                        if not item.salary_rule_id.rule_credit_account_id:
                            raise exceptions.Warning(_('Undefined credit account for salary rule %s (%s).') % (
                                item.salary_rule_id.name, item.salary_rule_id.code))
                    # check for allowance debit account
                    elif item.salary_rule_id.category_id.rule_type == 'allowance':
                        if not item.salary_rule_id.rule_debit_account_id:
                            raise exceptions.Warning(_('Undefined credit account for salary rule %s (%s).') % (
                                item.salary_rule_id.name, item.salary_rule_id.code))
                    else:
                        if not item.salary_rule_id.rule_credit_account_id:
                            raise exceptions.Warning(_(
                                'Check account debit for salary rule "%s" ') % item.salary_rule_id.name)

                    # fill move lines with allowance deduction
                    if item.salary_rule_id.category_id.rule_type == 'allowance':
                        line_vals.append({
                            'name': 'Employee  %s  allowance.' % (self.employee_id.name),
                            'debit': abs(item.amount),
                            'account_id': item.salary_rule_id.rule_debit_account_id.id,
                            'partner_id': self.employee_id.user_id.partner_id.id})

                    elif item.salary_rule_id.category_id.rule_type == 'deduction':
                        line_vals.append({
                            'name': 'Employee  %s  deduction.' % (self.employee_id.name),
                            'credit': abs(item.amount),
                            'account_id': item.salary_rule_id.rule_credit_account_id.id,
                            'partner_id': self.employee_id.user_id.partner_id.id})
                    else:
                        line_vals.append({
                            'name': 'Employee  %s  rule.' % (self.employee_id.name),
                            'debit': abs(item.amount),
                            'account_id': item.salary_rule_id.rule_debit_account_id.id,
                            'partner_id': self.employee_id.user_id.partner_id.id})

        for item in self.loans_ids:
            line_vals.append({
                'name': 'Employee  %s  loan.' % (self.employee_id.name),
                'credit': abs(item.remaining_loan_amount),
                'account_id': item.request_type.account_id.id,
                'partner_id': self.employee_id.user_id.partner_id.id})

            for install in item.deduction_lines:
                if install.paid == False:
                    install.paid = True
                    item.state = 'closed'

        line_vals.append({
            'name': 'Employee  %s  Net.' % (self.employee_id.name),
            'credit': abs(self.net),
            'account_id': self.journal_id.default_account_id.id,
            'partner_id': self.employee_id.user_id.partner_id.id})

        # Constrain on net that must be greater than zero
        if self.net < 0.0:
            raise exceptions.Warning(_('The Net must be not negative value .'))

        move = self.env['account.move'].create({
            'state': 'draft',
            'journal_id': self.journal_id.id,
            'date': self.date,
            'ref': 'Reconcile leave of "%s" ' % self.employee_id.name,
            'line_ids': [(0, 0, value) for value in line_vals]
        })
        self.write({'account_move_id': move.id})
        self.state = 'pay'

    # change state to refuse
    def refuse(self):
        self.state = 'refuse'

    # Override create function
    @api.model
    def create(self, values):
        result = super(ReconcileLeaves, self).create(values)
        if result.net < 0.0:
            raise exceptions.Warning(_('The Net must be not negative value .'))
        return result


class ReconcileAllowanceDeduction(models.Model):
    _name = 'reconcile.allowance.deduction'

    amount = fields.Float()

    # relational fields
    reconcile_id = fields.Many2one('reconcile.leaves')
    salary_rule_id = fields.Many2one('hr.salary.rule')
    category_id = fields.Many2one('hr.salary.rule.category', related='salary_rule_id.category_id')


class ReconcileAllowanceJournal(models.Model):
    _name = 'reconcile.allowance.journal'

    amount = fields.Float()

    # relational fields
    journal_entry_ids_lines = fields.Many2one('reconcile.leaves')
    journal_id = fields.Many2one('account.journal')
