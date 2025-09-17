# -*- coding: utf-8 -*-
from datetime import date

from odoo import fields, models, _, api
from odoo.tools.translate import _
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta


class HrHolidaysStatus(models.Model):
    _name = 'hr.holidays.status'
    _inherit = ['mail.thread', 'mail.activity.mixin','hr.holidays.status']

    name = fields.Char()
    leave_type = fields.Selection(selection=[('annual', _('Annual')),
                                             ('exception', _('Exception')),
                                             ('sick', _('Sick')),
                                             ('motherhood', _('Motherhood')),
                                             ('hajj', _('Hajj')),
                                             ('new_baby', _('New Baby')),
                                             ('exam', _('Exams')),
                                             ('marriage', _('Marriage')),
                                             ('death', _('Death')),
                                             ('emergency', _('Emergency')), ], tracking=True)
    duration = fields.Integer(tracking=True)
    used_once = fields.Boolean(string='Used Once', tracking=True)
    emp_type = fields.Selection(selection=[('saudi', _('Holiday1')),
                                           ('other', _('Holiday2')), 
                                           ('displaced', _('Holiday3')),
                                           ('external', _('Holiday4')),
                                           ('external2', _('Other')), ('all', _('All'))],string='Annual Leave Entitlement', tracking=True)
    gender = fields.Selection(selection=[('male', _('Male')),
                                         ('female', _('Female')),
                                         ('both', _('Both'))], tracking=True)
    contract_duration = fields.Selection(selection=[('12month', _('12 Months')),
                                                    ('24month', _('24 Months')),
                                                    ('all', _('All'))], string='Contract Duration')
    balance_type = fields.Selection(selection=[
        ('yearly', 'Yearly'),
        ('monthly', 'Monthly'),
        ('daily', 'Daily')
    ], string='Type of leave balance', default='daily', tracking=True)
    request_before = fields.Integer(tracking=True)
    minimum_duration = fields.Float(tracking=True)
    exit_return_permission = fields.Boolean()
    exit_return_permission_duration = fields.Integer()
    issuing_ticket = fields.Boolean()
    issuing_clearance_form = fields.Boolean()
    issuing_deliver_custody = fields.Boolean()
    issuing_loans_reconciliation = fields.Boolean()
    unpaid = fields.Boolean()
    mission_chick = fields.Boolean(tracking=True)
    attach_chick = fields.Boolean(tracking=True)
    alternative_chick = fields.Boolean(default=True,tracking=True)
    alternative_days = fields.Integer(string='Alternative Days')
    limit = fields.Boolean(tracking=True)
    '''color_name = fields.Selection(selection=[('red', _('Red')),
                                             ('blue', _('Blue')),
                                             ('light_green', _('light Green')),
                                             ('Light_blue', _('Light Blue')),
                                             ('light_yellow', _('Light Yellow')),
                                             ('black', _('Black')),
                                             ('brown', _('Brown')),
                                             ('magenta', _('Magenta')),
                                             ('wheat', _('Wheat')), ])'''
    # category_id = fields.Many2one('calender.event.type')

    # new fields for Payroll config
    payslip_type = fields.Selection(selection=[('paid', _('Paid')),
                                               ('unpaid', _('Unpaid')),
                                               ('reconcile', _('Reconcile')),
                                               ('percentage', _('Percentage')),
                                               ('addition', _('Addition')),
                                               ('exclusion', _('Exclusion'))], string='Payslip Type',tracking=True)
    percentage = fields.Float(string='Percentage')
    salary_rules_ids = fields.Many2many('hr.salary.rule', string='Rules',
                                        domain="[('special','!=',True)]")
    leave_annual_type = fields.Selection(
        selection=[('open_balance', _('Opening Balance')), ('save_annual_year', _('Save Annual'))],
        string='Annual Type', default='open_balance',tracking=True)
    number_of_holidays_save_years = fields.Integer(tracking=True)
    number_of_save_days = fields.Integer(tracking=True)

    number_of_days = fields.Integer(default=90,tracking=True)
    number_of_years = fields.Integer(tracking=True)
    visible_fields = fields.Boolean()
    advance_request_years = fields.Integer(tracking=True)
    official_holidays = fields.Boolean(string='Include Official Holidays', default=True ,tracking=True)
    period_ticket = fields.Integer()
    include_weekend = fields.Boolean(string='Include Weekend', default=False)
    unpaid_holiday_id = fields.Many2one('hr.holidays.status', string='Related Unpaid Leave')
    annual_holiday_id = fields.Many2one('hr.holidays.status', string='Related Annual Leave')
    type_unpaid = fields.Selection(selection=[('unpaid', _('Salary Only')),
                                              ('termination', _('Salary and Termination'))])
    check_annual_holiday = fields.Boolean(string="Check annual holiday",tracking=True)
    remained_before = fields.Float(string="Remained Before",tracking=True)
    working_days = fields.Boolean(string='Working Days Only', default=False,tracking=True)
    sickness_severity = fields.Selection(selection=[('1', '1'),
                                                    ('2', '2'),
                                                    ('3', '3'),
                                                    ('4', '4'),
                                                    ], string='Sickness Severity',tracking=True)
    not_balance_annual_leave = fields.Boolean(string="Not Balance Annual Leave")
    duration_ids = fields.One2many('holiday.status.duration', 'holiday_status_id', string="Duration",tracking=True)
    period_giving_balance = fields.Integer("Period of Giving Balance (Years)")
    unpaid_leave_days_per_period = fields.Integer("Maximum Unpaid Leave per Period (Days)")
    period_unpaid_leave = fields.Integer("Period of Maximum Unpaid Leave (Months)")
    exclude_public_holidays = fields.Boolean(string='Exclude Public Holidays', default=True,
                                             help="If enabled, public holidays are skipped in leave days calculation.")

    @api.model
    def _search(self, args, offset=0, limit=None, order=None, count=False, access_rights_uid=None):
        leave_ids = super(HrHolidaysStatus, self)._search(args, offset=offset, limit=limit, order=order,
                                                          count=count, access_rights_uid=access_rights_uid)
        if not count and not order and self._context.get('employee_id'):
            leaves = self.browse(leave_ids)
            sort_key = lambda l: (l.leave_type, l.sickness_severity, l.virtual_remaining_leaves)
            employee_id = self._context.get('employee_id')
            type_holiday = self._context.get('type')
            if type_holiday == "remove":
                balance = self.env['hr.holidays'].search([
                    ('employee_id', '=', int(employee_id)),
                    ('holiday_status_id.leave_type', '!=', 'sick'),
                    ('type', '=', 'add'),
                    ('check_allocation_view', '=', 'balance')
                ]).mapped('holiday_status_id')
                balance_sick = self.env['hr.holidays'].search([
                    ('employee_id', '=', int(employee_id)),
                    ('holiday_status_id.leave_type', '=', 'sick'),
                    ('type', '=', 'add'),
                    ('check_allocation_view', '=', 'balance'),
                    ('remaining_leaves', '>', 0)
                ]).mapped('holiday_status_id').sorted(key=lambda eval: eval.sickness_severity, reverse=False)
                balance_sick = balance_sick and balance_sick[0] or balance_sick
                leaves = balance | balance_sick
            return leaves.sorted(key=sort_key, reverse=False).ids
        return leave_ids

    @api.onchange('number_of_years', 'duration')
    def _check_number_of_save_days(self):
        for rec in self:
            if rec.visible_fields and rec.leave_type != 'annual':
                max_number_day = self.number_of_years * max(self.duration_ids.mapped('duration') or 0)
                if self.number_of_save_days > max_number_day:
                    raise ValidationError(_(
                        "The number of saved days should not exceed max number day"))

    def get_days(self, employee_id):
        result = dict(
            (id, dict(max_leaves=0, leaves_taken=0, remaining_leaves=0, virtual_remaining_leaves=0)) for id in self.ids)
        holidays = self.env['hr.holidays'].search(
            [('employee_id', '=', employee_id), ('holiday_status_id', 'in', self.ids)])
        for holiday in holidays:
            status_dict = result[holiday.holiday_status_id.id]
            if holiday.type == 'add' and holiday.check_allocation_view == 'balance':
                status_dict[
                    'virtual_remaining_leaves'] += holiday.remaining_leaves > 0 and holiday.remaining_leaves or 0.0
                status_dict['max_leaves'] += holiday.remaining_leaves > 0 and holiday.remaining_leaves or 0.0
                status_dict['remaining_leaves'] += holiday.remaining_leaves
            elif holiday.type == 'remove' and holiday.state not in ('cancel', 'validate1', 'refuse'):
                status_dict['virtual_remaining_leaves'] -= holiday.number_of_days_temp
        return result

    @api.onchange('leave_type')
    def change_boll_state(self):
        if self.leave_type == 'hajj' or self.leave_type == 'marriage':
            self.used_once = True
        else:
            self.used_once = False
        if self.leave_type == 'exam' or self.leave_type == 'sick':
            self.attach_chick = True
        else:
            self.attach_chick = False

    @api.onchange('visible_fields')
    def change_save_years(self):
        for holi in self:
            if holi.visible_fields is False:
                holi.number_of_years = 0.0
                holi.number_of_save_days = 0.0

    @api.constrains('number_of_holidays_save_years', 'number_of_years')
    def check_past_years_balance(self):
        for rec in self:
            if rec.number_of_holidays_save_years and rec.number_of_years and \
                    rec.number_of_holidays_save_years > rec.number_of_years:
                raise ValidationError(
                    "Sorry past years balance can not be greater than "
                    "allowed holiday years balance to be carried to next years")

    @api.constrains('alternative_days', 'alternative_chick')
    def check_alternative_days(self):
        for rec in self:
            if rec.alternative_chick==True and rec.alternative_days <= 0:
                raise ValidationError(_("Sorry, The Alternative Employee Days Must Be Greater Than One Day."))


class CalenderEventType(models.Model):
    _name = 'calender.event.type'
    _rec_name = 'name'
    name = fields.Char(string="Name", required=True)


class HrOfficial(models.Model):
    _name = "hr.holiday.official.event"
    name = fields.Char()


class HrHolidaysOfficials(models.Model):
    _name = "hr.holiday.officials"
    _rec_name = 'official_event_id'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    official_event_id = fields.Many2one('hr.holiday.official.event', string='Official Event', required=True)
    date_from = fields.Date(string='Date From', required=True, default=date.today())
    date_to = fields.Date(string='Date To', required=True)
    religion = fields.Selection(selection=[('muslim', 'Muslim'), ('christian', 'Christian'), ('other', 'Other')])
    active = fields.Boolean(default=True)
    state = fields.Selection([('draft', _('Draft')),
                              ('confirm', _('confirm')),
                              ('refuse', _('Refused'))], default="draft",tracking=True)

    @api.constrains('date_to')
    def check_date(self):
        for rec in self:
            if rec.date_to < rec.date_from:
                raise ValidationError(_('Please make sure that date to follows date from'))

    @api.constrains('official_event_id')
    def unique_official_holiday(self):
        for event in self:
            if len(self.search([('active', '=', True), ('official_event_id', '=', event.official_event_id.id),
                                ('date_to', '>=', event.date_from)])) > 1:
                raise ValidationError(_('Sorry you already have an active official holiday %s in the same period')
                                      % event.official_event_id.name)

    def write(self, vals):
        res = super(HrHolidaysOfficials, self).write(vals)
        self.create_transaction_holliday()
        return res

    def update_leave(self):
        holidays_ids = self.env['hr.holidays'].search([
            ('holiday_status_id.official_holidays', '=', False),
            '|', '|',
            '&', ('date_to', '<=', self.date_to),
            ('date_to', '>=', self.date_from),
            '&', ('date_from', '<=', self.date_to),
            ('date_from', '>=', self.date_from),
            '&', ('date_from', '<=', self.date_from),
            ('date_to', '>=', self.date_to),
        ])
        for holidays_id in holidays_ids:
            old_duration = holidays_id.number_of_days_temp
            holidays_id.set_date()
            allocation_balance = self.env['hr.holidays'].search([('type', '=', 'add'),
                                                                 ('holiday_status_id', '=',
                                                                  holidays_id.holiday_status_id.id),
                                                                 ('employee_id', '=', holidays_id.employee_id.id),
                                                                 ('check_allocation_view', '=', 'balance')],
                                                                order='id desc', limit=1)
            if holidays_id.state == 'validate1':
                allocation_balance.write({
                    'remaining_leaves': allocation_balance.remaining_leaves +
                                        (old_duration - holidays_id.number_of_days_temp),
                    'leaves_taken': allocation_balance.leaves_taken + (holidays_id.number_of_days_temp - old_duration)
                })

    def create_transaction_holliday(self):
        if self.date_from and self.date_to:
            start_date = datetime.strptime(str(self.date_from), "%Y-%m-%d")
            end_date = datetime.strptime(str(self.date_to), "%Y-%m-%d")
            delta = end_date - start_date
            for i in range(delta.days + 1):
                day = start_date + timedelta(days=i)
                self.env['hr.attendance.transaction'].process_attendance_scheduler_queue(day)

    @api.model
    def create(self, vals):
        res = super(HrHolidaysOfficials, self).create(vals)
        res.create_transaction_holliday()
        return res

    def confirm(self):
        for rec in self:
            rec.write({'state': 'confirm'})
            rec.update_leave()

    def draft_state(self):
        for rec in self:
            old_state = rec.state
            rec.write({'state': 'draft'})
            if old_state == 'confirm':
                rec.update_leave()

    def refuse(self):
        for rec in self:
            rec.write({'state': 'refuse'})


class HolidayStatusDuration(models.Model):
    _name = 'holiday.status.duration'

    name = fields.Char(translate=True, required=True, string="Name")
    date_from = fields.Integer("From")
    date_to = fields.Integer("To")
    duration = fields.Float("Duration")
    holiday_status_id = fields.Many2one("hr.holidays.status")
