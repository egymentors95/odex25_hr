# -*- coding: utf-8 -*-

from datetime import date
from odoo import models, fields, api, _, exceptions


class hr_exit_return(models.Model):
    _name = "hr.exit.return"
    _rec_name = 'employee_id'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    state = fields.Selection(selection=[
        ("draft", "Draft"),
        ("request", "Employee Request"),
        ("send", "Direct Manager"),
        ("confirm", "Government Relations"),
        ("done", "Approved"),
        ("refuse", "Refuse")
    ], default='draft', tracking=True)
    from_hr = fields.Boolean()
    contract_duration = fields.Selection(selection=[("12", _("12 Month")), ("24", _("24 Month"))])
    request_for = fields.Selection(selection=[
        ("employee", "For Employee Only"), ("family", "For Family Only"), ("all", "For Employee and Family")
    ])
    without_leave = fields.Boolean()
    on_employee_fair = fields.Boolean()

    entry_visa_no = fields.Char(related='employee_id.visa_no')
    border_no = fields.Char(related='employee_id.permit_no')
    first_date = fields.Date()
    visa_no = fields.Char()
    visa_duration = fields.Float()
    exit_return_type = fields.Selection(selection=[
        ("one", _("One Travel")),
        ("multi", "Multi Travel"),
        ("final", "Final Exit")
    ])
    cost = fields.Float()
    travel_before_date = fields.Date()
    arrival_before_date = fields.Date()
    note = fields.Text()

    # relational fields
    employee_dependant = fields.One2many('hr.employee.dependent', 'contract_id',
                                         related='contract_id.employee_dependant')
    account_journal_id = fields.Many2one(comodel_name='account.journal')
    account_debit_id = fields.Many2one(comodel_name='account.account')
    attach_ids = fields.One2many('ir.attachment', 'attach_ids_exit_return')

    employee_id = fields.Many2one('hr.employee', default=lambda item: item.get_user_id())
    job_id = fields.Many2one(comodel_name='hr.job', related='employee_id.job_id')
    department_id = fields.Many2one(comodel_name='hr.department', related='employee_id.department_id')
    nationality_id = fields.Many2one(comodel_name='res.country', related='employee_id.country_id')
    contract_id = fields.Many2one(comodel_name='hr.contract', related='employee_id.contract_id')
    account_move_id = fields.Many2one(comodel_name='account.move')

    iqama_end_date = fields.Date(related="employee_id.iqama_number.expiry_date",string='Identity End Date', readonly=True)
    iqama_number = fields.Char(related="employee_id.iqama_number.iqama_id",string='Identity Number', readonly=True)

    # @api.onchange('employee_id')
    # def _get_leave_request_domain(self):
    #     self.leave_request_id = False
    #     if self.employee_id and self.request_for:
    #         if self.employee_id.marital == 'single' and self.request_for in ['family', 'all']:
    #             raise exceptions.Warning(_('You are single, can not request ticket for family'))
    #         if self.employee_id.contract_id.contract_status == 'marriage' and self.request_for in ['family', 'all']:
    #             dependant_list = []
    #             if self.employee_id.contract_id.employee_dependant:
    #                 for item in self.employee_id.contract_id.employee_dependant:
    #                     dependant_list.append(item.id)
    #                 self.employee_dependant = self.env['hr.employee.dependent'].browse(dependant_list)

    @api.constrains('travel_before_date', 'arrival_before_date')
    def date_constraint(self):
        for item in self:
            if item.arrival_before_date and item.travel_before_date:
                if item.travel_before_date > item.arrival_before_date:
                    raise exceptions.Warning(_('Date Travel Must be Less Than Date Arrival'))

    def request(self):
        self.state = 'request'

    def send(self):
        self.state = 'send'

    def draft(self):
        # check if the moved journal entry if un posted then delete
        for item in self:
            if item.account_move_id:
                if item.account_move_id.state == 'draft':
                    item.account_move_id.state = 'canceled'
                    item.account_move_id = False
                    self.state = 'draft'
                else:
                    raise exceptions.Warning(_(
                        'You can not re-draft Exit and return because account move with ID "%s" in state Posted')
                                             % item.account_move_id.id)
            else:
                self.state = 'draft'

    def hr_manager(self):
        if not self.on_employee_fair:
            if self.cost <= 0:
                raise exceptions.Warning(_('The Cost Of Exit and Return Should Be Greater Than Zero'))
            self.state = 'confirm'
        else:
            self.state = 'done'

    def financial_manager(self):
        for item in self:
            if item.on_employee_fair == False and item.cost > 0:
                debit_line_vals = {
                    'name': 'debit',
                    'debit': item.cost,
                    'account_id': item.account_debit_id.id,
                    'partner_id': item.employee_id.user_id.partner_id.id
                }
                credit_line_vals = {
                    'name': 'credit',
                    'credit': item.cost,
                    'account_id': item.account_journal_id.default_account_id.id,
                    'partner_id': item.employee_id.user_id.partner_id.id
                }
                if not item.account_move_id:
                   move_id = self.env['account.move'].create({
                       'state': 'draft',
                       'journal_id': item.account_journal_id.id,
                       'date': date.today(),
                       'ref': 'Exit and Return',
                       'line_ids': [(0, 0, debit_line_vals), (0, 0, credit_line_vals)],
                       'res_model': 'hr.exit.return',
                       'res_id': self.id
                   })
                   self.account_move_id = move_id.id

        self.state = 'done'

    def refuse(self):
        self.state = 'refuse'

    # overrite unlink function
    def unlink(self):
        for i in self:
            if i.state != 'draft':
                raise exceptions.Warning(_('You can not delete record in state not in draft'))
        return super(hr_exit_return, self).unlink()

    def get_user_id(self):
        employee_id = self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)
        if employee_id:
            return employee_id.id
        else:
            return False


class hr_exit_return_attach(models.Model):
    _inherit = "ir.attachment"

    # inverse field to hr.exit.return
    attach_ids_exit_return = fields.Many2one(comodel_name='hr.exit.return')
