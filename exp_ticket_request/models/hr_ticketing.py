# -*- coding:utf-8 -*-

from odoo import models, fields, api, exceptions
from odoo.tools.translate import _
from odoo.exceptions import ValidationError
from odoo.exceptions import UserError


class HrTicketing(models.Model):
    _name = 'hr.ticket.request'
    _rec_name = 'employee_id'
    _description = 'Ticket Request'
    _inherit = ['mail.thread']

    STATE_SELECTION = [
        ('draft', _('Draft')),
        ('submit', _('Direct Manager')),
        ('review', _('Government Relations')),
        ('confirm', _('HR Manager')),
        ('done', _('Financial Manager')),
        ('refuse', _('Refused')),
        #   ('cancelled', _('Cancelled')),
    ]

    from_hr = fields.Boolean(_('Another Employee'))
    estimated_ticket_amount = fields.Float(_('Estimated Cost of Ticket'), )
    contract_type = fields.Selection([('single', 'Single'),
                                      ('marriage', 'Married'),
                                      ], string='Contract Type', )
    contract_start_date = fields.Date(string='Contract Start Date', related='employee_id.contract_id.date_start',
                                      readonly=True)
    contract_end_date = fields.Date(string='Contract End Date', related='employee_id.contract_id.date_end',
                                    readonly=True)
    contract_duration = fields.Selection(related='employee_id.contract_id.contract_duration', readonly=True)

    ticket_degree = fields.Selection([
        ('first', 'First'),
        ('first_reduced', 'First reduced'),
        ('economic', 'Economic'),
        ('business', 'Business'),
        ('other', 'Other'),
    ], string='Tickets Degree')

    request_for = fields.Selection(
        [('employee', 'For Employee Only'), ('family', 'For Family Only'), ('all', 'For Employee and Family'), ],
        _('Request For'))
    note = fields.Text(string='Notes')
    state = fields.Selection(STATE_SELECTION, string='Status', default='draft', tracking=True)
    leave_ticket = fields.Boolean(string='Leave Ticket')
    passport_issue_place = fields.Char(related='employee_id.place_issuance_passport', string='Passport Issue Place')
    passport_issue_date = fields.Date(related='employee_id.date_issuance_passport', string='Passport Issue Date')
    passport_expiry_date = fields.Date(related='employee_id.expiration_date_passport', string="Passport Expiry Date")
    position_type = fields.Selection([('Consultant_director', _('Managerial')), ('normal', _('Normal Job'))],
                                     _('Position Type'), )
    request_date = fields.Date(string='Request Date', default=fields.Date.today)
    cost_of_tickets = fields.Float(string='Cost Of Tickets')

    # Relational fields
    employee_id = fields.Many2one('hr.employee', string='Employee', default=lambda self: self._employee_get())
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.user.company_id)
    travel_agent = fields.Many2one('airline.agent', string='Travel Agent')
    journal_id = fields.Many2one('account.journal', _('Journal'))
    validators_user_ids = fields.Many2many('res.users', string='Validators')
    # passport_no = fields.Many2one('hr.employee.dependent', string='Passport No.', readonly=True)
    passport_no = fields.Many2one(related='employee_id.passport_id')
    request_type = fields.Many2one('hr.ticket.request.type')
    ticket_check = fields.Boolean(related='request_type.ticket_check')
    air_line = fields.Many2one('hr.airline', string='AirLine')
    attach_ids = fields.One2many('ir.attachment', 'ticket_request_id', string='Attachment')

    job_id = fields.Many2one('hr.job', string='Job Title', related='employee_id.job_id', readonly=True)
    department_id = fields.Many2one('hr.department', string='Department', related='employee_id.department_id',
                                    readonly=True)
    nationality_id = fields.Many2one('res.country', string='Nationality', related='employee_id.country_id',
                                     readonly=True)
    employee_dependant = fields.One2many('hr.employee.dependent', 'contract_id', readonly=True,
                                         related='employee_id.contract_id.employee_dependant')
    move_id = fields.Many2one('account.move')
    mission_check = fields.Boolean()
    ticket_date = fields.Date(string='Ticket Date')
    destination = fields.Many2one('mission.destination', string='Destination')

    def unlink(self):
        for item in self:
            if item.state != 'draft':
                raise exceptions.Warning(_('You can not delete record in state not in draft'))
        return super(HrTicketing, self).unlink()

    def submit(self):
        #if self.employee_id and self.request_for:
            #if self.employee_id.marital == 'single' and self.request_for in ['family', 'all']:
               # raise ValidationError(_('You are single, can not request ticket for family'))
        self.write({'state': 'submit'})

    def review(self):
        self.write({'state': 'review'})

    def confirm(self):
        self.write({'state': 'confirm'})

    def action_done(self):
        if self.cost_of_tickets > 0:
            debit_line_vals = {
                'name': 'debit',
                'debit': self.cost_of_tickets,
                'date': self.request_date,
                'account_id': self.request_type.account_debit_id.id,
                'partner_id': self.employee_id.user_id.partner_id.id,
                'analytic_account_id': self.request_type.analytic_account_id.id,
            }
            credit_line_vals = {
                'name': 'credit',
                'credit': self.cost_of_tickets,
                'date': self.request_date,
                'account_id': self.journal_id.default_account_id.id,
                'partner_id': self.employee_id.user_id.partner_id.id
            }
            if not self.move_id :
               move_id = self.env['account.move'].create({
                   'state': 'draft',
                   'journal_id': self.journal_id.id,
                   'date': self.request_date,
                   'ref': 'Ticket Request for %s' % self.employee_id.name,
                   'line_ids': [(0, 0, debit_line_vals), (0, 0, credit_line_vals)],
                   'res_model': 'hr.ticket.request',
                   'res_id': self.id
               })

               self.write({
                   'state': 'done',
                   'move_id': move_id.id
               })
        else:
            self.write({'state': 'done'})

    def refuse(self):
        self.write({'state': 'refuse'})

    #
    # def cancel(self):
    #  self.write({'state': 'cancelled'})

    def re_draft(self):
        # when redraft cancel the created account move
        if self.move_id:
            if self.move_id.state == 'draft':
                # self.move_id.write({'state': 'canceled'})
                self.move_id.unlink()
                self.write({
                    'state': 'draft',
                    'move_id': False
                })
            else:
                raise exceptions.Warning(
                    _('You can not cancel account move "%s" in state not draft') % self.move_id.name)
        else:
            self.state = 'draft'

    @api.model
    def _employee_get(self):
        employees = self.env['hr.employee'].search([('user_id', '=', self._uid)])
        if len(employees) <= 0:
            raise ValidationError(_('Set This User For Employee Profile'))
        else:
            # if employees[0].contract_id and employees[0].contract_id.emp_type and employees[
            #     0].contract_id.emp_type == 'saudi':
            # raise ValidationError(_('Not allowed to request tickets for the Saudis Employees'))
            return employees[0]

    @api.constrains('request_for')
    def check_request(self):
        if self.employee_id and self.request_for:
            if self.employee_id.marital == 'single' and self.request_for in ['family', 'all']:
                raise ValidationError(_('You are single, can not request ticket for family'))

    # Calculate salary rule on change leave type and save it in cost_of_tickets
    @api.onchange('request_type', 'employee_id', 'destination')
    def calculate_cost_of_tickets(self):
        for item in self:
            item.cost_of_tickets = 0.0
            if item.request_type:
                if item.request_type.allowance_name:
                    if item.employee_id:
                        if item.employee_id.contract_id:
                            item.cost_of_tickets = item.compute_rule(item.request_type.allowance_name,
                                                                     item.employee_id.contract_id)
                        else:
                            raise exceptions.Warning(_('Employee "%s" has no contract') % item.employee_id.name)

                else:
                    if item.destination and item.employee_id:
                        if item.employee_id.contract_id:
                            employee_class = item.employee_id.contract_id.ticket_class_id
                            if employee_class:
                                for line in item.destination.class_ids:
                                    if employee_class == line.ticket_class_id:
                                        item.cost_of_tickets = line.price
                        else:
                            raise exceptions.Warning(_('Employee "%s" has no contract') % item.employee_id.name)

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


class Attachment(models.Model):
    _inherit = 'ir.attachment'

    # Relational fields
    ticket_request_id = fields.Many2one(comodel_name='hr.ticket.request')


class hr_airline(models.Model):
    _name = 'hr.airline'

    name = fields.Char(string='Name')
    ar_name = fields.Char(string='Arabic Name')
    code = fields.Char(string='Code')

    # Relational fields
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.user.company_id)


class hr_airline_city(models.Model):
    _name = 'hr.airline.city'

    name = fields.Char(string='Name')
    ar_name = fields.Char(string='Arabic Name')
    code = fields.Char(string='Code')

    # Relational fields
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.user.company_id)


class HRTicketDependent(models.Model):
    _inherit = 'hr.ticket.dependent'

    ticket_request_line = fields.Many2one(comodel_name='hr.ticket.request')


class airline_agent(models.Model):
    _name = 'airline.agent'
    _rec_name = 'agent_name'

    agent_name = fields.Char(string='Agent Name')
    ar_agent_name = fields.Char(string='Arabic Agent Name')
    account_no = fields.Char(string='Account No.')
    code = fields.Char(string='Code')
    telephone = fields.Char(string='Telephone')
    mobile = fields.Char(string='Mobile')
    fax = fields.Char(string='Fax No.')
    mail = fields.Char(string='E-mail')
    contact_person = fields.Char(string='Contact Person')
    sur_name = fields.Selection([('mr', 'Mr'), ('mrs', 'Mrs'), ('president', 'President')], string='Sur Name')
    # Relational fields
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.user.company_id)

    _sql_constraints = [
        ('code_code_unique', 'unique(code)', 'The agency code must be unique per company !'),
    ]


class HrTicketingType(models.Model):
    _name = 'hr.ticket.request.type'

    name = fields.Char()
    ticket_check = fields.Boolean()

    # relational fields
    allowance_name = fields.Many2one('hr.salary.rule', domain=[('category_id.rule_type', '=', 'allowance')])
    account_debit_id = fields.Many2one('account.account')
    analytic_account_id = fields.Many2one(comodel_name='account.analytic.account',string='Analytic Account')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.user.company_id)
