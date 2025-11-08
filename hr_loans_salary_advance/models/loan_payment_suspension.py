# -*- coding: utf-8 -*-
from math import ceil
from datetime import datetime as dt
from dateutil import relativedelta

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from collections import defaultdict


class HrLoanPaymentSuspension(models.Model):
    _name = 'hr.loan.payment.suspension'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    employee_id = fields.Many2one('hr.employee', 'Employee', required=True,
                                  default=lambda e: e.get_user_id(), domain=[('state', '=', 'open')])
    date = fields.Date('Request Date', default=lambda self: fields.Date.today(), required=True)
    type = fields.Selection(selection=[('payment', 'Payment'),
                                       ('suspension', 'Rescheduling')
                                       ], string='Process', default='payment', required=True)
    loan_id = fields.Many2one('hr.loan.salary.advance', 'Loan', required=True,
                              domain="[('employee_id', '=', employee_id), ('state', '=', 'pay')]")
    installment_ids = fields.Many2many('loan.installment.line', 'install_ps_rel', 'ps_id', 'install_id', 'Installments')
    suspend_ids = fields.One2many('hr.loan.installment.suspension', 'pay_suspend_id', 'Reschedule Installments')

    payment_type = fields.Selection(selection=[('sequential', 'Sequential'),
                                               ('flexible', 'Flexible')
                                               ], string='Payment Way')
    amount = fields.Float('Amount', default=1, digits=(16, 2))
    move_id = fields.Many2one('account.move', 'Payment Move', readonly=True)

    state = fields.Selection([('draft', _('Draft')),
                              ('submit', _('Waiting Payroll Officer')),
                              ('confirm', _('Wait HR Department')),
                              ('approve', _('Approved')),
                              ('refuse', _('Refused'))], 'State', default='draft')

    remaining_loan_amount = fields.Float(related='loan_id.remaining_loan_amount', string="Remaining Amount")
    no_month_allowed = fields.Integer(related='loan_id.request_type.no_month_allowed', readonly=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

    @api.model
    def resolve_2many_commands(self, field_name, commands, fields=None):
        result = []  # result (list of dict)
        record_ids = []  # ids of records to read
        updates = defaultdict(dict)  # {id: vals} of updates on records

        for command in commands or []:
            if not isinstance(command, (list, tuple)):
                record_ids.append(command)
            elif command[0] == 0:
                result.append(command[2])
            elif command[0] == 1:
                record_ids.append(command[1])
                updates[command[1]].update(command[2])
            elif command[0] in (2, 3):
                record_ids = [id for id in record_ids if id != command[1]]
            elif command[0] == 4:
                record_ids.append(command[1])
            elif command[0] == 5:
                result, record_ids = [], []
            elif command[0] == 6:
                result, record_ids = [], list(command[2])

        # read the records and apply the updates
        field = self._fields[field_name]
        records = self.env[field.comodel_name].browse(record_ids)
        for data in records.read(fields):
            data.update(updates.get(data['id'], {}))
            result.append(data)

        return result

    def get_user_id(self):
        return self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1) or False

    @api.onchange('employee_id')
    def _onchange_employee(self):
        self.loan_id = False

    @api.onchange('loan_id')
    def _onchange_loan(self):
        self.suspend_ids = [(5, 0, 0)]
        self.installment_ids = [(5, 0, 0)]
        if self.type == 'payment' and self.loan_id:
            return {'domain': {'installment_ids': [('deduction_line', '=', self.loan_id.id), ('paid', '!=', True)]}}

    @api.onchange('type')
    def _onchange_type(self):
        self.amount = 1
        self.payment_type = False
        self.suspend_ids = [(5, 0, 0)]
        self.installment_ids = [(5, 0, 0)]

    @api.onchange('payment_type')
    def _onchange_payment_type(self):
        if self.type == 'payment':
            self.installment_ids = [(5, 0, 0)]
            if self.payment_type == 'sequential':
                self.pay_installment()

    @api.onchange('installment_ids')
    def onchange_installments(self):
        domain = [('deduction_line', 'in', [])]
        if self.type == 'payment' and self.payment_type == 'flexible' and self.loan_id:
            domain = [('deduction_line', '=', self.loan_id.id), ('paid', '!=', True)]
        return {'domain': {'installment_ids': domain}}

    @api.onchange('amount')
    def onchange_amount(self):
        if self.payment_type == 'sequential':
            self.pay_installment()

    def pay_installment(self):
        if self.type != 'payment' or not self.payment_type or not self.loan_id: return
        if self.payment_type == 'sequential':
            installments_to_pay = self.env['loan.installment.line'].search([('deduction_line', '=', self.loan_id.id),
                                                                            ('paid', '=', False)
                                                                            ], order='installment_date asc')
            if not installments_to_pay:
                raise ValidationError(_('Sorry but it seems that all your installments are paid.'))
        else:
            installments_to_pay = self.installment_ids

        if self.payment_type and self.loan_id and not self.amount:
            raise ValidationError(_('Please set the amount you want to pay.'))
        if self.amount and self.amount < 1:
            raise ValidationError(_('Please make sure that the amount you want to pay is greater than 0.'))

        self.installment_ids = [(5, 0, 0)]
        residual = self.amount
        lines = []
        for tp in installments_to_pay:
            if residual < 1: break
            residual -= tp.installment_amount
            lines.append((4, tp.id))
        self.installment_ids = lines

    @api.constrains('amount', 'installment_ids')
    def _check_total_installments(self):
        if self.type == 'suspension' or not (self.amount and self.installment_ids): return True
        inst_amount = self.installment_ids[0].deduction_line.installment_amount
        inst_no = len(self.installment_ids)
        if self.amount > round(sum(self.installment_ids.mapped('installment_amount')),2):
            raise ValidationError(_('Sorry the amount you are paying exceeds the total of '
                                    'the selected installments which is %s.'
                                    '\n You can add more installments to pay or reduce the amount.')
                                  % round(sum(self.installment_ids.mapped('installment_amount')),2))
        elif ceil(self.amount / inst_amount) < inst_no and self.payment_type == 'flexible':
            raise ValidationError(_('Sorry the amount you are paying can cover up to %s installments. \n'
                                    'Please commit to this number or consider increasing the amount')
                                  % ceil(self.amount / inst_amount))

    def action_submit(self):
        for rec in self:
            if rec.type == 'suspension' and not rec.suspend_ids:
                raise ValidationError(_('Sorry no installment has been chosen for rescheduling. Kindly choose some.'))
            elif rec.type == 'payment' and \
                    (
                            (not (rec.amount and rec.installment_ids)) or
                            (rec.amount and not rec.installment_ids) or
                            (not rec.amount and rec.installment_ids)
                    ):
                raise ValidationError(
                    _('Kindly make sure that you have set both the amount and the installments you want to pay.'))
        self.write({'state': 'submit'})

    def action_confirm(self):
        self.write({'state': 'confirm'})

    def installment_update(self):
        install = self.env['loan.installment.line'].search([('deduction_line', '=', self.loan_id.id)],order='installment_date asc')
        i=0
        for line in install:
            i+=1
            line.write({ 'sequence': i })

    def action_approve(self):
        for rec in self:
            if rec.type == 'suspension':
                for s in rec.suspend_ids:
                    if s.installment_id.paid:
                        raise ValidationError(
                            _('Sorry the following installment has already been paid %s.'
                              % s.installment_id.installment_date))
                    s.installment_id.installment_date = s.date_new
            else:
                for ins in rec.installment_ids:
                    if ins.paid:
                        raise ValidationError(
                            _('Sorry the following installment has already been paid %s.' % ins.installment_date))
                residual = rec.amount
                today = fields.Date.today()
                for i in rec.installment_ids.sorted(lambda s: s.installment_date):
                    i.write({'paid': True, 'payment_date': today, 'advance_payment': True})
                    i.payment_date = today
                    if residual >= i.installment_amount:
                        residual -= i.installment_amount
                    elif residual < i.installment_amount:
                        i.create({'installment_date': i.installment_date,
                                  'installment_amount': i.installment_amount - residual,
                                  'deduction_line': i.deduction_line.id,
                                  'paid': False
                                  })
                        i.installment_amount = residual
                dr_vals = {
                    'name': 'debit',
                    'debit': rec.amount,
                    'account_id': rec.loan_id.request_type.journal_id.default_account_id.id,
                    'partner_id': rec.employee_id.user_id.partner_id.id
                }
                cr_vals = {
                    'name': 'credit',
                    'credit': rec.amount,
                    'account_id': rec.loan_id.request_type.account_id.id,
                    'partner_id': rec.employee_id.user_id.partner_id.id
                }
                move = self.env['account.move'].create({
                    'state': 'draft',
                    'journal_id': rec.loan_id.request_type.journal_id.id,
                    'date': today,
                    'ref': 'Loan Payment',
                    'line_ids': [(0, 0, dr_vals), (0, 0, cr_vals)]
                })
                rec.move_id = move.id
                self.env['hr.account.moves'].create({
                    'number': rec.loan_id.code,
                    'reference': _('Loan Payment'),
                    'amount': rec.amount,
                    'journal': rec.loan_id.request_type.journal_id.id,
                    'partner_id': rec.employee_id.user_id.partner_id.id,
                    'date': today,
                    'journal_move_id': move.id,
                    'moves_id': rec.loan_id.id
                })
        self.installment_update()
        if self.loan_id.remaining_loan_amount <= 0.0 < self.loan_id.gm_propos_amount:
            self.loan_id.state = 'closed'
        self.write({'state': 'approve'})

    def action_reset(self):
        for rec in self:
            if rec.state == 'approve' and rec.type == 'payment':
                if rec.move_id.state != 'draft':
                    raise ValidationError(
                        _('Sorry you can not set this payment to draft, the associated transaction is already posted.'))
                rec.move_id.unlink()
                rec.loan_id.moves_ids.filtered(lambda m: m.journal_move_id == rec.move_id).unlink()
                rec.installment_ids.write({'paid': False, 'advance_payment': False, 'payment_date': False})
            elif rec.state == 'approve' and rec.type == 'suspension':
                for s in rec.suspend_ids:
                    s.installment_id.installment_date = s.installment_date
        self.write({'state': 'draft'})

    def action_refuse(self):
        self.write({'state': 'refuse'})

    def unlink(self):
        for rec in self:
            if rec.state != 'draft':
                raise UserError(_('Sorry you cannot delete a document is not in draft state.'))
        return super(HrLoanPaymentSuspension, self).unlink()


class HrLoanInstallmentLine(models.Model):
    _inherit = 'loan.installment.line'

    advance_payment = fields.Boolean('Advance Payment', default=False)

    def name_get(self):
        return [(install.id, '%s %s' % (install.deduction_line.code, install.installment_date)) for install in self]

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        ctx = self._context
        if ctx.get('unpaid', False):
            args.append(('paid', '=', False))
        if ctx.get('loan_id', False):
            args.append(('deduction_line', '=', ctx.get('loan_id', False)))
        if ctx.get('suspend_ids', []):
            loan_ps = self.env['hr.loan.payment.suspension']
            suspend_ids = loan_ps.resolve_2many_commands('suspend_ids', ctx.get('suspend_ids'))
            exp_instl = [isinstance(s['installment_id'], tuple) and s['installment_id'][0] or s['installment_id']
                         for s in suspend_ids]
            args.append(('id', 'not in', exp_instl))
        return super(HrLoanInstallmentLine, self).name_search(name, args=args, operator=operator, limit=limit)


class HrLoanInstallmentSuspension(models.Model):
    _name = 'hr.loan.installment.suspension'

    pay_suspend_id = fields.Many2one('hr.loan.payment.suspension', 'Payment Rescheduling')
    installment_id = fields.Many2one('loan.installment.line', 'Installment', required=True)
    installment_date = fields.Date('Initial Installment Date', readonly=True)
    date_new = fields.Date('New Installment Date')

    @api.onchange('installment_id')
    def _onchange_installment(self):
        self.installment_date = self.installment_id.installment_date

    @api.constrains('date_new')
    def _check_date_new(self):
        if self.pay_suspend_id.loan_id.request_type.refund_from == 'salary':
            lst_salary = self.pay_suspend_id.loan_id.deduction_lines.filtered(
                lambda r: r.payment_date != False and not r.advance_payment).sorted(lambda i: i.payment_date)
            if not lst_salary:
                if self.date_new < self.pay_suspend_id.loan_id.date:
                    raise ValidationError(
                        _('Sorry this loan starts in %s, you cannot reschedule a payment prior to this date.')
                        % (self.pay_suspend_id.loan_id.date,))
                return True
            if self.date_new < lst_salary[-1].payment_date:
                raise ValidationError(_('Sorry the last salary was paid in %s, you cannot reschedule '
                                        'a payment prior to this date.') % (lst_salary[-1].payment_date))
        elif self.date_new < self.pay_suspend_id.loan_id.date:
            raise ValidationError(_('Sorry this loan starts in %s, you cannot reschedule a payment prior to this date.')
                                  % (self.pay_suspend_id.loan_id.date,))

    @api.constrains('installment_date', 'date_new', 'pay_suspend_id.no_month_allowed')
    def _check_no_month_allowed(self):
        for rec in self:
            installment_date = str(rec.installment_date)
            stardate_newt_date = str(rec.date_new)
            start_date_1 = dt.strptime(installment_date, "%Y-%m-%d")
            end_date_1 = dt.strptime(stardate_newt_date, "%Y-%m-%d")
            no_of_month = relativedelta.relativedelta(end_date_1, start_date_1).months
            no_of_days = relativedelta.relativedelta(end_date_1, start_date_1).days
            rec1 = rec.pay_suspend_id.no_month_allowed * 30
            rec2 = no_of_month * 30 + no_of_days
            if rec2 > rec1:
                raise ValidationError(_('Sorry this loan is greater than the number of allowed months %s')
                                      % rec.pay_suspend_id.no_month_allowed)
