from odoo import models, fields, api, _, exceptions
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare, float_round

from datetime import datetime
import datetime as dt
from datetime import timedelta


class BuyVacation(models.Model):
    _name = "buy.vacation"
    _description = "Buy Vacation"
    _rec_name = 'employee_id'
    _order = 'id desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    employee_id = fields.Many2one('hr.employee', 'Employee', required=True)
    job_id = fields.Many2one(related='employee_id.job_id', readonly=True)
    department_id = fields.Many2one(related='employee_id.department_id', readonly=True)
    date = fields.Date()
    leave_buy = fields.Float('Vacation balance for purchase')
    monthly_salary = fields.Float(store=True)
    notes = fields.Text()
    attach_ids = fields.One2many('ir.attachment', 'att_vacation_ids')
    account_move_id = fields.Many2one('account.move')
    journal_id = fields.Many2one('account.journal', _('Journal'))
    account_debit_id = fields.Many2one('account.account', _('Account'))
    leave_amount = fields.Float()
    leave_balance = fields.Float(string="Current annual leave balance",store=True,)
    # holiday_status_id = fields.Many2one('hr.holidays.status', domain=[('id', 'in', [])])
    state = fields.Selection([('draft', _('Draft')),
                              ('send', _('Send')),
                              ('d_manager', _('Direct Manager')),
                              ('m_manager', _('Management Manager')),
                              ('hr_manager', _('HR Manager')),
                              ('approve', _('Approved')),
                              ('refuse', _('Refused')),
                              ], default="draft",tracking=True)

    @api.onchange("employee_id")
    def _compute_leave_balance(self):
        for rec in self:
            rec.monthly_salary = rec.employee_id.contract_id.total_net
            balance = self.env['hr.holidays'].search([('employee_id', '=', rec.employee_id.id), ('type', '=', 'add'),
                                                      ('holiday_status_id.leave_type', '=', 'annual'),
                                                      ('check_allocation_view', '=', 'balance')
                                                      ], order='id desc', limit=1)
            rec.leave_balance = balance.remaining_leaves

    # get amount of salary day from salary month and get leave buy
    @api.onchange("leave_buy")
    def _compute_leave_amount(self):
        for rec in self:
           rec.monthly_salary = rec.employee_id.contract_id.total_net
           if rec.monthly_salary:
              salary_day = rec.monthly_salary/30
              rec.leave_amount = rec.leave_buy*salary_day

    @api.constrains('leave_buy', 'leave_balance')
    def leave_balance_constrain(self):
        for item in self:
            employee_balance = self.env['hr.holidays'].search(
                [('type', '=', 'add'), ('holiday_status_id.leave_type', '=', 'annual'),
                 ('employee_id', '=', item.employee_id.id), ('check_allocation_view', '=', 'balance')],
                limit=1)
            #if item.leave_buy > item.leave_balance:
              #  raise exceptions.Warning(_('The Days of Leave to buy must equal or less than leave balance'))

            if item.leave_buy > employee_balance.remaining_leaves:
                raise exceptions.ValidationError(_('The Days of Leave to buy must equal or less than remaining leaves'))

    @api.constrains('leave_amount')
    def _check_leave_amount(self):
        if self.leave_amount == 0.0:
            raise ValidationError(_('The leave amount amount cannot be Zero.'))

    def send(self):
        self._compute_leave_balance()
        self.state = 'send'

    def d_manager(self):
        self._compute_leave_balance()
        self.state = 'd_manager'

    def m_manager(self):
        self._compute_leave_balance()
        self.state = 'm_manager'

    def hr_manager(self):
        self._compute_leave_balance()
        self.state = 'hr_manager'

    def approve(self):
        for item in self:
            item._compute_leave_balance()
            employee_balance = self.env['hr.holidays'].search(
                [('type', '=', 'add'), ('holiday_status_id.leave_type', '=', 'annual'),
                 ('employee_id', '=', item.employee_id.id), ('check_allocation_view', '=', 'balance')],
                limit=1)
            employee_balance.write({'remaining_leaves': employee_balance.remaining_leaves - item.leave_buy})
            debit_line_vals = {
                'name': 'debit',
                'debit': item.leave_amount,
                'date': item.date,
                'account_id': item.account_debit_id.id,
                'partner_id': item.employee_id.user_id.partner_id.id
            }
            credit_line_vals = {
                'name': 'credit',
                'credit': item.leave_amount,
                'date': item.date,
                'account_id': item.journal_id.default_account_id.id,
                'partner_id': item.employee_id.user_id.partner_id.id
            }
            move_id = self.env['account.move'].create({
                'state': 'draft',
                'journal_id': item.journal_id.id,
                'date': item.date,
                'ref': 'Buy Vacation for "%s" ' % item.employee_id.name,
                'line_ids': [(0, 0, debit_line_vals), (0, 0, credit_line_vals)]
            })

            self.write({
                'state': 'approve',
                'account_move_id': move_id.id
            })

        self.state = 'approve'

    def refuse(self):
        self.state = 'refuse'

    def draft_state(self):
        for item in self:
            employee_balance = self.env['hr.holidays'].search(
                [('type', '=', 'add'), ('holiday_status_id.leave_type', '=', 'annual'),
                 ('employee_id', '=', item.employee_id.id), ('check_allocation_view', '=', 'balance')],
                limit=1)
            employee_balance.write({'remaining_leaves': employee_balance.remaining_leaves + item.leave_buy})
            if item.account_move_id.state == 'posted':
                raise exceptions.Warning(
                    _('You can not cancel account move "%s" in state not draft') % item.account_move_id.name)
            else:
                item.account_move_id.unlink()
                item.write({
                    'account_move_id': False
                })
                item.account_debit_id = False
                item.journal_id = False
            item._compute_leave_balance()
            item.write({'state': 'draft'})

    def unlink(self):
        for rec in self:
            if rec.state != 'draft':
                raise UserError(_('You can not delete a record not in draft state'))
        return super(BuyVacation, self).unlink()


class BuyVacationAttach(models.Model):
    _inherit = 'ir.attachment'

    att_vacation_ids = fields.Many2one(comodel_name='buy.vacation')
