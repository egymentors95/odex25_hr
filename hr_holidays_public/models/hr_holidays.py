# -*- coding: utf-8 -*-
import math
from datetime import datetime
import datetime as dt

from odoo import SUPERUSER_ID
from odoo import models, fields, api, _, exceptions
from dateutil.relativedelta import relativedelta
from dateutil import relativedelta
from datetime import timedelta
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT
from odoo.exceptions import AccessError, ValidationError, MissingError, UserError
import calendar
from collections import defaultdict


def daterange(start_date, end_date):
    for n in range(int((end_date - start_date).days)):
        yield start_date + timedelta(n)


class HRHolidays(models.Model):
    _inherit = 'hr.holidays'
    _order = "create_date desc"


    replace_by = fields.Many2one(comodel_name='hr.employee', string="Replace By")
    emp_id = fields.Integer(string="id")
    employee_id = fields.Many2one('hr.employee', 'Employee', default=lambda item: item.get_user_id(), )
    last_employee_contract = fields.Many2one(related='employee_id.contract_id', readonly=True)
    employee_type = fields.Selection(related='employee_id.contract_id.emp_type', store=True, readonly=True)
    issuing_clearance_form = fields.Selection(selection=[('yes', _('Yes')), ('no', _('No'))], default='no')
    issuing_deliver_custdy = fields.Selection(selection=[('yes', _('Yes')), ('no', _('No'))], default='no')
    start_date = fields.Date(string="Start Date", default=fields.Datetime.now())
    end_date = fields.Date(string="End Date")
    notes = fields.Text()
    issuing_exit_return = fields.Selection(selection=[('yes', _('Yes')), ('no', _('No'))], default='no')
    check_allocation_view = fields.Selection(selection=[('allocation', _('Allocation')), ('balance', _('Balance'))])
    exit_return_duration = fields.Float(related='number_of_days_temp')
    permission_request_for = fields.Selection(selection=[('employee', _('For Employee Only')),
                                                         ('family', _('For Family Only')),
                                                         ('all', _('For Employee And Family Only'))])
    issuing_ticket = fields.Selection(selection=[('yes', _('Yes')), ('no', _('No'))], default='no')
    # ticket_cash_request_type = fields.Selection(
    #   selection=[('request_ticket', _('Request Ticket')), ('cash_in_lieu', _('Cash In Lieu'))])
    ticket_cash_request_type = fields.Many2one('hr.ticket.request.type')
    ticket_cash_request_for = fields.Selection(selection=[('employee', _('For Employee Only')),
                                                          ('family', _('For Family Only')),
                                                          ('all', _('For Employee And Family Only'))])
    check_state = fields.Boolean('check', default=True)
    check_related = fields.Boolean('Check Related', default=False)
    leaves_taken = fields.Float(tracking=True)
    remaining_leaves = fields.Float(tracking=False)

    cron_run_date = fields.Date()
    holiday_ids = fields.One2many(comodel_name='hr.inverse.holidays', inverse_name='holiday_id')
    hiring_date = fields.Date(related='employee_id.first_hiring_date', store=True, readonly=True)
    # check_boolean = fields.Boolean(default=True)
    check_unlimit = fields.Boolean()
    holiday_limit_check = fields.Boolean(store=True)

    canceled_duration = fields.Float(readonly=True)
    state = fields.Selection([('draft', _('Draft')),
                              ('confirm', _('Waiting Direct Manager')),
                              ('validate', _('Wait HR Department')),
                              ('approved', _('Wait Approval')),
                              ('validate1', _('Approved')),
                              ('refuse', _('Refused')),
                              ('cancel', _('Cancel'))], default="draft")
    holiday_status_id = fields.Many2one('hr.holidays.status', domain=[('id', 'in', [])])
    number_of_days_temp = fields.Float(
        'Allocation', copy=False, states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]},
        help='Number of days of the leave request according to your working schedule.')
    return_from_leave = fields.Boolean(readonly=True)
    current_date_plus_years = fields.Datetime()
    official_holiday_days = fields.Float('Included Official Holidays', copy=False, readonly=False, default=0,
                                         help='Number of days of official holiday during this period.')
    reconcile_leave = fields.Boolean()
    date_on = fields.Boolean()
    leave_balance = fields.Float('Current Balance', copy=False, compute='_compute_leave_balance', store=True,
                                 readonly=True)
    delegate_acc = fields.Boolean('Delegate Permissions', default=False)
    delegated_group_ids = fields.Many2many('res.groups', string="Delegated Access Groups", )
    delegated_company_ids = fields.Many2many('res.company', string="Delegated Companies", )
    delegated_department_ids = fields.Many2many('hr.department', string="Delegated Departments")

    leave_balance_date = fields.Float(store=True, readonly=True, compute='_leave_balance_date',
                                      help='The Balance Remains until the end date of the current Holiday Request')

    attach_ids = fields.One2many('ir.attachment', 'att_holiday_ids')
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    emp_company_id = fields.Many2one(related='employee_id.company_id')

    emp_number = fields.Char(related='employee_id.emp_no',store=True)

    request_done = fields.Boolean(default=False,readonly=True)
    is_branch = fields.Many2one(related='department_id.branch_name', store=True, readonly=True)

    to_date = fields.Boolean(string='Today',compute='_leave_today_run', store=True)

    def _compute_number_of_days(self):
        res = super(HRHolidays, self)._compute_number_of_days()
        self._leave_today_run()

    @api.depends('date_from','date_to', 'create_date','state')
    def _leave_today_run(self):
        today = datetime.now().date()
        for item in self:
            if item.date_to and item.date_from:
               if item.date_from.date() <= today <= item.date_to.date():
                  item.to_date = True
               else:
                  item.to_date = False

    ## to remove followers ##
    def _remove_followers_holiday(self):
        for rec in self:
            followers = self.env['mail.followers'].search(
                       [('res_id', '=', rec.id),('res_model','=','hr.holidays')])
            followers.sudo().unlink()


    def _check_state_access_right(self, vals):
        if vals.get('state') and vals['state'] not in ['draft', 'confirm', 'cancel'] and not \
                self.env['res.users'].has_group(
                    'hr_holidays_community.group_hr_holidays_user,hr.group_hr_manager,hr_base.group_general_manager'):
            return False
        return True

    def check_annual_balance(self):
        for rec in self:
            if rec.type == "remove":
                annual = rec.env['hr.holidays.status'].search([('leave_type', '=', 'annual')])
                if rec.employee_id and annual:
                    balance = self.env['hr.holidays'].search([('employee_id', '=', rec.employee_id.id), ('type', '=', 'add'),
                                          # ('holiday_status_id', '=', annual.id),
                                          ('holiday_status_id.leave_type', '=', 'annual'),
                                          ('check_allocation_view', '=', 'balance')
                                          ], order='id desc', limit=1).remaining_leaves or 0.0
                    if balance >= 1:
                        raise ValidationError(_("You Can not order this leave and you have annual Leave Balance"))

    def check_balance_per_period(self, rec):
        old_holiday_id = self.env['hr.holidays'].search([('employee_id', '=', rec.employee_id.id), ('type', '=', 'remove'),
                                     ('holiday_status_id', '=', rec.holiday_status_id.id),
                                     ('state', 'not in', ['cancel', 'refuse']),
                                     ], limit=1, order="date_from desc")
        if old_holiday_id:
            old_leave_date_from = datetime.strptime(str(old_holiday_id.date_from),
                                                    DEFAULT_SERVER_DATETIME_FORMAT)
            date_from = datetime.strptime(str(rec.date_from),
                                          DEFAULT_SERVER_DATETIME_FORMAT)
            if old_leave_date_from > date_from:
                date_from = datetime.strptime(str(rec.date_from),
                                              DEFAULT_SERVER_DATETIME_FORMAT)
            date_of_period = date_from + relativedelta.relativedelta(months=rec.holiday_status_id.period_unpaid_leave)
            holiday_ids = self.env['hr.holidays'].search([('employee_id', '=', rec.employee_id.id), ('type', '=', 'remove'),
                                      ('holiday_status_id', '=', rec.holiday_status_id.id),
                                      ('state', 'not in', ['cancel', 'refuse']),
                                      ('date_from', '>=', str(date_from)),
                                      ('date_from', '<=', str(date_of_period))])
            number_days_of_leaves = sum(holiday_ids.mapped('number_of_days_temp')) + rec.number_of_days_temp
            max_allowed = rec.holiday_status_id.unpaid_leave_days_per_period
            if rec.holiday_status_id.type_unpaid == 'termination':
               if number_days_of_leaves > max_allowed:
                  raise ValidationError(_('The number of days of leave exceed the maximum allowed %s') % (max_allowed))

    @api.depends('date_from','date_to', 'holiday_status_id')
    def _leave_balance_date(self):
        for rec in self:
            rec._remove_followers_holiday()
            to_work_days = 0
            to_work_days2 = 0
            leave = rec.holiday_status_id
            current_date = (datetime.utcnow() + timedelta(hours=3)).date()
            if rec.type == 'remove' and rec.employee_id.first_hiring_date and rec.date_from:
                first_hiring_date = datetime.strptime(str(rec.employee_id.first_hiring_date), "%Y-%m-%d").date()
                contract_start_date1 = datetime.strftime(first_hiring_date, DEFAULT_SERVER_DATE_FORMAT)
                contract_start_date = datetime.strptime(str(contract_start_date1), "%Y-%m-%d").date()
                working_days = (current_date - contract_start_date).days + 1
                working_years = working_days / 365
                holiday_duration = 0
                for item in leave.duration_ids:
                    if item.date_from <= working_years < item.date_to:
                        holiday_duration = item.duration
                ###### get last cron date to compute leave_balance_date #
                if leave:
                   balance_holiday = self.env['hr.holidays'].search([('employee_id', '=', rec.employee_id.id), ('type', '=', 'add'),
                                      ('holiday_status_id', '=', leave.id),('check_allocation_view', '=', 'balance')
                                      ], order='id desc', limit=1).holiday_ids

                   if balance_holiday: 
                      last_cron_date = datetime.strptime(str(balance_holiday[-1].cron_run_date), DEFAULT_SERVER_DATE_FORMAT).date()
                      holi_date = (datetime.strptime(str(rec.date_from), "%Y-%m-%d %H:%M:%S")).date()
                      if last_cron_date < holi_date:
                         to_work_days2 = (holi_date - last_cron_date).days
                #else:
                   #to_work_days2 = -(last_cron_date - holi_date).days
                ##### end ########
                '''to_work_days = fields.Datetime.from_string(rec.date_from) > \
                               fields.Datetime.from_string(fields.Datetime.now()) and \
                               (datetime.strptime(str(rec.date_from), "%Y-%m-%d %H:%M:%S") -
                                (datetime.utcnow() + timedelta(hours=3))).days + 1 or 0'''

                upcoming_leave = self.remaining_leaves_of_day_by_date(rec.employee_id, str(current_date), leave , is_month=False, is_years=False) * to_work_days2
                if upcoming_leave > 0 and leave.leave_type == 'annual':
                    rec.leave_balance_date = round(rec.leave_balance + upcoming_leave, 2)
                    exceed_days = leave.number_of_save_days + holiday_duration
                    if rec.leave_balance_date > exceed_days and not (
                            rec.holiday_limit_check or leave.limit or self._context.get('stop_const')):
                        raise ValidationError(
                            _("Sorry the days you are trying to taken exceed tha maximum allowed days to be given"))
                else:
                    rec.leave_balance_date = round(rec.leave_balance, 2)

    @api.constrains('date_from', 'date_to', 'holiday_status_id', 'holiday_limit_check')
    def _check_number_of_days(self):
        for rec in self:
            leave = rec.holiday_status_id
            if rec.type == 'add' and rec.check_allocation_view == 'allocation':
                holidays = self.env['hr.holidays'].search([('type', '=', 'add'),
                                                           ('check_allocation_view', '=', 'allocation'),
                                                           ('holiday_status_id', '=', rec.holiday_status_id.id),
                                                           ('employee_id', '=', rec.employee_id.id),
                                                           ('state', 'not in', ('cancel', 'refuse')),
                                                           ('id', '!=', rec.id)])
                taken = holidays and sum(holidays.mapped('number_of_days_temp')) or 0
                if leave.payslip_type == 'unpaid' and leave.check_annual_holiday:
                    rec.check_annual_balance()
                if leave.leave_annual_type == 'open_balance' \
                        and rec.number_of_days_temp \
                        and (leave.visible_fields
                             and
                             (
                                     leave.number_of_save_days
                                     and leave.number_of_save_days >= 1
                                     and rec.number_of_days_temp > (leave.duration + leave.number_of_save_days - taken)
                             )
                             or (
                                     not leave.number_of_save_days
                                     and leave.number_of_years
                                     and (
                                             (
                                                     leave.number_of_years > 0
                                                     and rec.number_of_days_temp > (leave.duration + (
                                                     leave.duration * leave.number_of_years) - taken)
                                             )
                                             or
                                             (
                                                     leave.number_of_years < 1
                                                     and rec.number_of_days_temp > (leave.duration - taken)
                                             )
                                     )
                             )
                ) \
                        or (not leave.visible_fields and leave.duration and (
                        rec.number_of_days_temp > (leave.duration - taken))):
                    raise ValidationError(_(
                        "Sorry the days you are trying to allocate exceed tha maximum allowed days to be given"))
            elif rec.type == 'remove':
                if leave.payslip_type == 'unpaid' and leave.check_annual_holiday:
                    rec.check_annual_balance()
                    rec.check_balance_per_period(rec)
                if not (rec.employee_id.contract_id and rec.employee_id.first_hiring_date and rec.date_from):
                    raise ValidationError(_('Please make sure employee contract, first hiring date and leave start date'
                                            ' are set.'))
                balance = self.env['hr.holidays'].search([('employee_id', '=', rec.employee_id.id),
                                                          ('type', '=', 'add'),
                                                          ('holiday_status_id', '=', rec.holiday_status_id.id),
                                                          ('check_allocation_view', '=', 'balance')
                                                          ], order='id desc', limit=1)
                if not balance:
                    raise ValidationError(_('Sorry you have no balance'))
                worked_days = ((datetime.utcnow() + timedelta(hours=3)).date() -
                               datetime.strptime(str(rec.employee_id.first_hiring_date), "%Y-%m-%d").date()).days + 1
                #if worked_days < rec.holiday_status_id.number_of_days:
                 #   raise exceptions.Warning(_('Sorry you can not create leave request you have not holidays'))
                #### Delete upcoming_leave  and add up##

                if rec.number_of_days_temp > rec.leave_balance_date and rec.state != 'validate1' and not (
                        rec.holiday_limit_check or leave.limit or self._context.get('stop_const')):

                    raise exceptions.Warning(
                        _('Sorry your request refused your holidays not cover this duration For Employee %s') % (
                            rec.employee_id.name))

                if leave.leave_type == 'hajj':
                    if self.env['ir.module.module'].sudo().search([('state', '=', 'installed'),
                                                                   ('name', '=', 'web_hijri_datepicker')]):
                        if rec.date_to and rec.date_from:
                            hijri_df = rec.employee_id.contract_id.change_current_date_hijri(fields.Date.to_string(
                                fields.Date.from_string(rec.date_from)))
                            hijri_dt = rec.employee_id.contract_id.change_current_date_hijri(fields.Date.to_string(
                                fields.Date.from_string(rec.date_to)))
                            if hijri_df.datetuple()[1] != 12 and hijri_dt.datetuple()[1] != 12:
                                raise exceptions.Warning(
                                    _('Sorry Hajj Leave can only be requested in the month of Zu Alhejja'))

    @api.constrains('date_from', 'date_to', 'holiday_status_id')    
    #@api.constrains('holiday_status_id')
    def _chick_leave_balance(self):
        for rec in self:
            taken_days = 0.0
            if rec.employee_id and rec.holiday_status_id:
                holi_id = self.env['hr.holidays'].search([('employee_id', '=', rec.employee_id.id), ('type', '=', 'add'),
                                      ('holiday_status_id', '=', rec.holiday_status_id.id),
                                      ('check_allocation_view', '=', 'balance')
                                      ], order='id desc', limit=1).id
                taken_days = self.env['hr.holidays'].search([('employee_id', '=', rec.employee_id.id),
                                         ('type', '=', 'add'),
                                         ('holiday_status_id', '=', rec.holiday_status_id.id),
                                         ('check_allocation_view', '=', 'balance')
                                         ], order='id desc', limit=1).leaves_taken
                if taken_days < 0 and rec.type == 'remove':
                    raise exceptions.Warning(_('Sorry the leaves taken is less than zero'))
                if not holi_id and rec.type == 'remove':
                    raise exceptions.Warning(_('There Is No Holiday Balance Record'))

                if rec.holiday_status_id.leave_type == 'sick' and rec.type == 'remove':
                    sickness_leaves = self.env['hr.holidays'].search([('employee_id', '=', rec.employee_id.id),
                                                  ('type', '=', 'add'),
                                                  ('holiday_status_id.leave_type', '=', 'sick'),
                                                  ('holiday_status_id', '!=', rec.holiday_status_id.id),
                                                  ('holiday_status_id.sickness_severity', '<',
                                                   rec.holiday_status_id.sickness_severity),
                                                  ('check_allocation_view', '=', 'balance')
                                                  ])
                    active_leaves = self.env['hr.holidays'].search([('employee_id', '=', rec.employee_id.id),
                                                ('type', '=', 'remove'),
                                                ('holiday_status_id.leave_type', '=', 'sick'),
                                                ('holiday_status_id', '!=', rec.holiday_status_id.id),
                                                ('holiday_status_id.sickness_severity', '<',
                                                 rec.holiday_status_id.sickness_severity),
                                                ('state', 'not in', ('refuse', 'validate1', 'cancel'))
                                                ])
                    if sickness_leaves:
                        msg = ''
                        for sk in sickness_leaves:
                            if sk.remaining_leaves > 0:
                                days = sum(active_leaves.filtered(
                                    lambda t: t.holiday_status_id.id == sk.holiday_status_id.id).mapped(
                                    'number_of_days_temp')) or 0
                                if days < sk.remaining_leaves:
                                    msg += sk.holiday_status_id.name + '\n'
                        if msg:
                            raise exceptions.Warning(_('Sorry you can not request %s leave while you '
                                                       'still have available balance in the following leaves \n %s')
                                                     % (rec.holiday_status_id.name, msg))

                ###############chick other request same holiday type####

                active_leaves_request = self.env['hr.holidays'].search([('employee_id', '=', rec.employee_id.id),
                                                    ('type', '=', 'remove'),
                                                    ('id', '!=', rec.id),
                                                    ('holiday_status_id', '=', rec.holiday_status_id.id),
                                                    ('state', 'not in', ('refuse', 'validate1', 'cancel'))
                                                    ])
                if active_leaves_request and rec.type == 'remove':
                    list_holiday = ''
                    sum_duration = 0.0
                    for lis in active_leaves_request:
                        list_holiday += lis.holiday_status_id.name + '\n'
                        sum_duration += lis.number_of_days_temp
                        #curnet_balance = rec.leave_balance - sum_duration
                        curnet_balance = rec.leave_balance_date - sum_duration
                    if list_holiday and rec.number_of_days_temp > curnet_balance:
                        raise exceptions.Warning(
                            _('Sorry you can not Create Holiday Request while you still have available Holiday request '
                              'in state Not Approve or Refuse Same Type : \n %s') % list_holiday)

                # check end of service
                Module = self.env['ir.module.module'].sudo()
                modules = Module.search([('state', '=', 'installed'), ('name', '=', 'hr_termination')])
                if modules:
                    end_of_service_rec = self.env['hr.termination'].search(
                        [('employee_id', '=', rec.employee_id.id), ('state', 'not in', ('refused', 'draft'))])
                    if end_of_service_rec and rec.type == 'remove':
                        raise exceptions.Warning(
                            _('Sorry ! you can not Create Holiday Request and there is an Employee Termination Request %s') % (
                                rec.employee_id.name))

    @api.depends('holiday_status_id', 'date_from', 'date_to')
    def _compute_leave_balance(self):
        for rec in self:
            balance = 0.0
            if rec.employee_id and rec.holiday_status_id:
                balance = self.env['hr.holidays'].search([('employee_id', '=', rec.employee_id.id), ('type', '=', 'add'),
                                      ('holiday_status_id', '=', rec.holiday_status_id.id),
                                      ('check_allocation_view', '=', 'balance')
                                      ], order='id desc', limit=1).remaining_leaves or 0.0
            rec.leave_balance = balance

    # chick missions for employee or holiday period employee replace

    @api.constrains('replace_by', 'holiday_status_id', 'date_from', 'date_to','state')
    def replace_by_not_holiday(self):
        for rec in self:
            if rec.type == 'remove':
                Module = self.env['ir.module.module'].sudo()
                modules = Module.search([('state', '=', 'installed'), ('name', '=', 'exp_official_mission')])
                modules_permission = Module.search([('state', '=', 'installed'), ('name', '=', 'employee_requests')])
                if modules and rec.holiday_status_id.mission_chick == False:
                    mission_dfrm = self.env['hr.official.mission'].search(
                        [('employee_ids.employee_id', '=', rec.employee_id.id),
                         ('mission_type.special_hours', '!=', 'True'), ('state', '!=', 'refused'),
                         ('employee_ids.date_from', '<=', rec.date_from),
                         ('employee_ids.date_to', '>=', rec.date_from)], order='id desc',
                        limit=1)
                    if mission_dfrm:
                        raise exceptions.Warning(
                            _('Sorry The Employee %s Actually On %s For this Period') % (
                                rec.employee_id.name, mission_dfrm.mission_type.name))

                    mission_dto = self.env['hr.official.mission'].search(
                        [('employee_ids.employee_id', '=', rec.employee_id.id),
                         ('mission_type.special_hours', '!=', 'True'),
                         ('state', '!=', 'refused'), ('employee_ids.date_from', '<=', rec.date_to),
                         ('employee_ids.date_to', '>=', rec.date_to)], order='id desc', limit=1)
                    if mission_dto:
                        raise exceptions.Warning(
                            _('Sorry The Employee %s Actually On %s For this Period') % (
                                rec.employee_id.name, mission_dto.mission_type.name))

                    mission_btw = self.env['hr.official.mission'].search(
                        [('employee_ids.employee_id', '=', rec.employee_id.id),
                         ('mission_type.special_hours', '!=', 'True'),
                         ('state', '!=', 'refused'), ('employee_ids.date_from', '>=', rec.date_from),
                         ('employee_ids.date_from', '<=', rec.date_to)], order='id desc',
                        limit=1)
                    if mission_btw:
                        raise exceptions.Warning(
                            _('Sorry The Employee %s Actually On %s For this Period') % (
                                rec.employee_id.name, mission_btw.mission_type.name))

                    mission_hours = self.env['hr.official.mission'].search(
                        [('employee_ids.employee_id', '=', rec.employee_id.id),
                         ('mission_type.special_hours', '!=', 'True'),
                         ('mission_type.duration_type', '=', 'hours'), ('state', '!=', 'refused'),
                         ('date', '>=', rec.date_from), ('date', '<=', rec.date_to)], order='id desc', limit=1)
                    if mission_hours:
                        raise exceptions.Warning(_('Sorry The Employee %s Actually On %s For this Period') %
                                                 (rec.employee_id.name, mission_hours.mission_type.name))
                if modules_permission:
                    date_to = datetime.strptime(str(rec.date_to), DEFAULT_SERVER_DATETIME_FORMAT)
                    hour = datetime.strptime(str("23:59:00"), "%H:%M:%S").time()
                    date_to = str(datetime.combine(date_to, hour))
                    date_from = datetime.strftime(datetime.strptime(str(rec.date_from), DEFAULT_SERVER_DATETIME_FORMAT),
                                                  DEFAULT_SERVER_DATETIME_FORMAT)
                    clause_1 = ['&', ('date_to', '<=', date_to), ('date_to', '>=', date_from)]
                    clause_2 = ['&', ('date_from', '<=', date_to), ('date_from', '>=', date_from)]
                    clause_3 = ['&', ('date_from', '<=', date_from), ('date_to', '>=', date_to)]
                    final_case = [('employee_id', '=', rec.employee_id.id), ('state', '!=', 'refused'), '|',
                                  '|'] + clause_1 + clause_2 + clause_3
                    permissions_day = self.env['hr.personal.permission'].search(final_case)
                    if permissions_day:
                        raise exceptions.Warning(
                            _('Sorry The Employee %s Actually On Permission For this Period') % rec.employee_id.name)

                if rec.replace_by:
                    holiday_dfrm = self.env['hr.holidays'].search(
                        [('employee_id', '=', rec.replace_by.id), ('type', '=', 'remove'), ('state', '!=', 'refuse'),
                         ('date_from', '<=', rec.date_from), ('date_to', '>=', rec.date_from)], order='id desc',
                        limit=1)

                    holiday_dto = self.env['hr.holidays'].search(
                        [('employee_id', '=', rec.replace_by.id), ('type', '=', 'remove'), ('state', '!=', 'refuse'),
                         ('date_from', '<=', rec.date_to), ('date_to', '>=', rec.date_to)], order='id desc', limit=1)

                    holiday_btw = self.env['hr.holidays'].search(
                        [('employee_id', '=', rec.replace_by.id), ('type', '=', 'remove'), ('state', '!=', 'refuse'),
                         ('date_from', '>=', rec.date_from), ('date_from', '<=', rec.date_to)], order='id desc',
                        limit=1)

                    if holiday_dfrm or holiday_dto or holiday_btw:
                        raise exceptions.Warning(
                            _('Sorry The Replacement Employee %s Actually On Holiday For this Period') % rec.replace_by.name)
                    rec.delegate_acc = True
                else:
                    rec.delegate_acc = False

    def send_email_holiday(self, holiday, emp):
        if holiday.visible_fields and holiday.remained_before > 0 and holiday.leave_type=='annual':
            today = datetime.now().date()
            today = datetime.strptime(str(today), "%Y-%m-%d").date()
            years = today.year
            last_date = datetime.strftime(today, "{0}-12-31".format(years))
            last_date = datetime.strptime(str(last_date), "%Y-%m-%d").date()
            start_days = last_date - timedelta(days=int(holiday.remained_before))
            if today < last_date:
                balance = self.env['hr.holidays'].search([('employee_id', '=', emp.id),
                                                          ('holiday_status_id', '=', holiday.id),
                                                          ('type', '=', 'add'),
                                                          ('check_allocation_view', '=', 'balance')
                                                          ], limit=1, order="id desc")
                holi_balance = balance.remaining_leaves or 0.0
                if today >= start_days < last_date:
                    if holi_balance > holiday.number_of_save_days:
                        if emp.user_id:
                            template = self.env.ref('hr_holidays_public.email_template_holiday_balance', False)
                            template.write({'email_to': emp.user_id.partner_id.email, 'lang': emp.user_id.lang,
                                            'email_cc': '%s' % (self.env.user.company_id.hr_email)})
                            template.send_mail(balance.id)
        if holiday.payslip_type == 'unpaid':
            tomorrow = (fields.Datetime.from_string(fields.Datetime.now()) + timedelta(days=1)).strftime(
                '%Y-%m-%d 00:00:00')
            upcoming_leaves = self.env['hr.holidays'].search([('employee_id', '=', emp.id),
                                           ('type', '=', 'remove'),
                                           ('holiday_status_id', '=', holiday.id),
                                           ('state', '=', 'validate1'),
                                           ('date_from', '=', tomorrow)])
            for up in upcoming_leaves:
                template = self.env.ref('hr_holidays_public.unpaid_leave_email', False)
                template.write({'lang': up.employee_id.parent_id.user_id.lang,
                                'subject': _('%s unpaid leave beginning') % (up.employee_id.name),
                                'email_to': up.employee_id.parent_id.work_email,
                                'email_cc': '%s, %s' % (self.env.user.company_id.hr_email, up.employee_id.work_email)
                                })
                template.send_mail(up.id, force_send=True, raise_exception=False)

    def remaining_leaves_of_day_by_date(self, employee_id, specific_date, item , is_years=False, is_month=False):
        first_hiring_date = datetime.strptime(str(employee_id.first_hiring_date), DEFAULT_SERVER_DATE_FORMAT).date()
        specific_date = datetime.strptime(str(specific_date), DEFAULT_SERVER_DATE_FORMAT).date()
        working_years = relativedelta.relativedelta(specific_date, first_hiring_date).years
        holiday_duration = 0
        num_days = calendar.monthrange(specific_date.year, specific_date.month)[1]
        
        for rec in item.duration_ids:
            if rec.date_from <= working_years < rec.date_to:
                holiday_duration = rec.duration
        if is_years:
            return holiday_duration
        if is_month:
            return holiday_duration / 12
        return (holiday_duration / 12) / num_days

    def calc_not_balance_annual_leave(self, emp, cron_date, is_month=False, is_year=False):
        holiday_status = self.env['hr.holidays.status'].search([('company_id', '=', self.env.user.company_id.id)])
        holiday_current_date_ids = self.env['hr.holidays'] \
                        .search(
                        [('employee_id', '=', emp.id), ('type', '=', 'remove'),
                         ('date_from', '<=', str(cron_date)),
                         ('holiday_status_id', 'in', holiday_status.filtered(lambda h: h.not_balance_annual_leave).ids),
                         ('date_to', '>=', str(cron_date)), ('state', 'not in', ['refuse', 'cancel', 'draft'])])
        return holiday_current_date_ids and 1 or 0
    
    def reset_remaining_leaves(self , current_date, item, emp, already_exist , is_years):
        if self.is_last_day_of_year(current_date):
            dutartion = 0 
            this_year_balance = 0
            if item.number_of_save_days > 0:
                dutartion = item.number_of_save_days
                if is_years:
                    open_year = datetime(current_date.year - 1, 12, 31).date()
                    days_diff = (current_date - open_year).days + 1
                    for index in range(1, days_diff):
                        open_year_date = open_year + timedelta(days=index)
                        this_year_balance += self.remaining_leaves_of_day_by_date(emp, str(open_year_date), item , is_month=False, is_years=False)
            else:
                years_save = item.number_of_years
                if is_years:
                    years_save = item.number_of_years + 1
                open_year = datetime(current_date.year - years_save, 12, 31).date()
                days_diff = (current_date - open_year).days + 1
                
                for index in range(1, days_diff):
                    open_year_date = open_year + timedelta(days=index)
                    dutartion += self.remaining_leaves_of_day_by_date(emp, str(open_year_date), item , is_month=False, is_years=False)
            # fix fix 
            if already_exist.remaining_leaves - this_year_balance > dutartion:
                dutartion = dutartion + this_year_balance
                already_exist.write({'remaining_leaves': dutartion})
    @api.model
    def process_holidays_scheduler_queue(self):
        current_date_run = (datetime.utcnow() + timedelta(hours=3)).date()
        employees = self.env['hr.employee'].search(
            [('state', '=', 'open'), ('company_id', '=', self.env.user.company_id.id)]
        ).filtered(
            lambda emp: emp.first_hiring_date
                        and emp.first_hiring_date <= current_date_run
                        and emp.contract_id
                        and emp.contract_id.emp_type in ('other', 'saudi', 'displaced', 'external', 'external2')
                        and (not emp.contract_id.date_end or emp.contract_id.date_end and emp.contract_id.date_end >= current_date_run))
        holiday_status = self.env['hr.holidays.status'].search([('company_id', '=', self.env.user.company_id.id)])
        for emp in employees:
            already_exist = None
            current_date = (datetime.utcnow() + timedelta(hours=3)).date()
            # current_date = datetime(2025, 12, 31).date()
            first_hiring_date = datetime.strptime(str(emp.first_hiring_date), "%Y-%m-%d").date()
            days = (current_date - first_hiring_date).days + 1
            for item in holiday_status:
                # current_date = datetime(2025, 12, 31).date()
                if days < item.number_of_days:
                    continue
                is_years , is_month = False , False
                if item.balance_type == 'monthly':
                    is_month = True
                if item.balance_type == 'yearly':
                    is_years = True  # True
                self.send_email_holiday(item, emp)
                if item.leave_type == 'annual' and (item.emp_type == 'all' or item.emp_type == emp.contract_id.emp_type):
                    if item.leave_annual_type == 'open_balance':  # or item.leave_annual_type == 'save_annual_year' and item.number_of_holidays_save_years <= 0:
                        already_exist = self.env['hr.holidays'].search([('employee_id', '=', emp.id),
                                                                        ('holiday_status_id', '=', item.id),
                                                                        ('type', '=', 'add'),
                                                                        ('check_allocation_view', '=', 'balance')
                                                                        ], limit=1, order="id desc")
                        create_open_balance = self.env['hr.holidays'].search([('holiday_status_id', '=', item.id),
                                                                        ('type', '=', 'add'),
                                                                        ('check_allocation_view', '=', 'balance')
                                                                        ], order="id desc")
                        if is_years:
                            current_date = current_date.replace(year=current_date.year , month=12, day=31)
                            current_date = datetime.strptime(str(current_date), DEFAULT_SERVER_DATE_FORMAT).date()
                        if is_month:
                            if self.is_last_day_of_month(current_date):
                                current_date = current_date
                            else: 
                                current_date = datetime.strptime(str(current_date), DEFAULT_SERVER_DATE_FORMAT).date()
                                current_date = current_date.replace(day=1) - timedelta(days=1)
                        if not already_exist and len(create_open_balance) > 1  and item.leave_annual_type == 'open_balance':
                        # if not already_exist and  item.leave_annual_type == 'open_balance':
                                balance_leaves = self.remaining_leaves_of_day_by_date(emp, str(first_hiring_date), item , is_month=False, is_years=False)
                                already_exist = self.env['hr.holidays'].create({
                                    'name': 'Yearly Allocation of ' + item.name + ' Leaves',
                                    'employee_id': emp.id,
                                    'holiday_status_id': item.id,
                                    'check_allocation_view': 'balance',
                                    'type': 'add',
                                    'remaining_leaves': balance_leaves,
                                })
                                self.env['hr.inverse.holidays'].create(
                                {'holiday_id': already_exist.id, 'cron_run_date': first_hiring_date, 'balance_leaves':balance_leaves })
                        if already_exist:
                            if not already_exist.holiday_ids:
                                not_balance = 0
                                not_no_balance = 0
                                if not is_years and not is_month:
                                    not_balance = self.remaining_leaves_of_day_by_date(emp, str(current_date), item , is_month=False, is_years=False) 
                                    not_no_balance = self.calc_not_balance_annual_leave(emp, current_date) * not_balance
                                    already_exist.write({
                                            'remaining_leaves': already_exist.remaining_leaves + not_balance - not_no_balance,
                                    })
                                self.env['hr.inverse.holidays'].create({'holiday_id': already_exist.id, 'cron_run_date': current_date, 'balance_leaves':not_balance, 'no_balance_leaves':not_no_balance })
                            holiday = already_exist.holiday_ids[-1]
                            if not holiday.cron_run_date:
                                not_balance = 0
                                not_no_balance = 0
                                if not is_years and not is_month:
                                    not_balance = self.remaining_leaves_of_day_by_date(emp, str(current_date), item , is_month=False, is_years=False) 
                                    not_no_balance = self.calc_not_balance_annual_leave(emp, current_date) * not_balance
                                    already_exist.write({
                                            'remaining_leaves': already_exist.remaining_leaves + not_balance - not_no_balance,
                                    })
                                holiday.write({'cron_run_date': current_date})
                            holiday_cron_run_date = datetime.strptime(str(holiday.cron_run_date ), "%Y-%m-%d").date()
                            if current_date > holiday_cron_run_date or is_years:
                                holiday_cron_run_date = datetime.strptime(str(holiday.cron_run_date), DEFAULT_SERVER_DATE_FORMAT).date()
                                current_date = datetime.strptime(str(current_date), DEFAULT_SERVER_DATE_FORMAT).date()
                                if holiday_cron_run_date >= current_date:
                                    continue
                                delta = current_date - holiday_cron_run_date  # timedelta
                                months_date = holiday_cron_run_date
                                months = (current_date.year - months_date.year) * 12 + (current_date.month - months_date.month) + 1
                                item_values = []
                                year = current_date.year - holiday_cron_run_date.year
                                range_val = []
                                range_val = range(1, delta.days + 1)
                                if is_years:
                                    range_val = range(1, year + 1)
                                    end_day = (holiday_cron_run_date.replace(day=1) + relativedelta.relativedelta(months=1)) - timedelta(days=1)
                                    end_date_cron = (end_day - holiday_cron_run_date).days
                                    if end_date_cron > 0:
                                        no_year_balance , year_balance = 0, 0
                                        for i in range(1, end_date_cron + 1):
                                            cala_date = holiday_cron_run_date + timedelta(days=i)
                                            balance = self.remaining_leaves_of_day_by_date(emp, str(cala_date), item , is_month=False, is_years=False)
                                            no_year_balance = no_year_balance + (self.calc_not_balance_annual_leave(emp, cala_date) * balance)
                                            year_balance = year_balance + balance
                                        already_exist.write({
                                            'name': 'Yearly Allocation of ' + item.name + ' Leaves',
                                            'remaining_leaves': already_exist.remaining_leaves + year_balance - no_year_balance,
                                        })
                                        already_exist.write({'holiday_ids': [(0, 0, {'cron_run_date': end_day, 'balance_leaves':year_balance, 'no_balance_leaves':no_year_balance})]})
                                    complete_month = datetime.strptime(str(already_exist.holiday_ids[-1].cron_run_date), DEFAULT_SERVER_DATE_FORMAT).date()
                                    cron_run_date_y = 12 - complete_month.month
                                    for x in range(1 , cron_run_date_y + 1):
                                        no_year_balance , year_balance = 0, 0
                                        end_day = (complete_month.replace(day=1) + relativedelta.relativedelta(months=x + 1)) - timedelta(days=1)
                                        y = end_day.replace(day=1)
                                        for i in range(0, (end_day - y).days + 1):
                                            cala_date = y + timedelta(days=i)
                                            balance = self.remaining_leaves_of_day_by_date(emp, str(cala_date), item , is_month=False, is_years=False)
                                            no_year_balance = no_year_balance + (self.calc_not_balance_annual_leave(emp, cala_date) * balance)
                                            year_balance = year_balance + balance
                                        already_exist.write({
                                        'name': 'Yearly Allocation of ' + item.name + ' Leaves',
                                        'remaining_leaves': (already_exist.remaining_leaves + year_balance) - no_year_balance,
                                        })
                                        already_exist.write({'holiday_ids': [(0, 0, {'cron_run_date': end_day, 'balance_leaves':year_balance, 'no_balance_leaves':no_year_balance})]})
                                if is_month:
                                    end_day = (holiday_cron_run_date.replace(day=1) + relativedelta.relativedelta(months=1)) - timedelta(days=1)
                                    end_date_cron = (end_day - holiday_cron_run_date).days
                                    if end_date_cron > 0:
                                        no_year_balance , year_balance = 0, 0
                                        for i in range(1, end_date_cron + 1):
                                            cala_date = holiday_cron_run_date + timedelta(days=i)
                                            balance = self.remaining_leaves_of_day_by_date(emp, str(cala_date), item , is_month=False, is_years=False)
                                            no_year_balance = no_year_balance + (self.calc_not_balance_annual_leave(emp, cala_date) * balance)
                                            year_balance = year_balance + balance
                                        already_exist.write({
                                            'name': 'Yearly Allocation of ' + item.name + ' Leaves',
                                            'remaining_leaves': already_exist.remaining_leaves + (year_balance - no_year_balance),
                                        })
                                        already_exist.write({'holiday_ids': [(0, 0, {'cron_run_date': end_day, 'balance_leaves':year_balance, 'no_balance_leaves':no_year_balance})]})
                                    range_val = range(1, months)
                                for i in range_val:
                                    no_year_balance , year_balance = 0, 0
                                    cron_date = holiday_cron_run_date + timedelta(days=i)
                                    balance = self.remaining_leaves_of_day_by_date(emp, str(cron_date), item , is_month=False, is_years=False)
                                    no_year_balance = no_year_balance + (self.calc_not_balance_annual_leave(emp, cron_date) * balance)
                                    year_balance = year_balance + balance
                                    if is_years:
                                        no_year_balance , year_balance = 0, 0
                                        cron_date = holiday_cron_run_date.replace(year=holiday_cron_run_date.year + i , month=12, day=31)
                                        y = cron_date.replace(year=cron_date.year - 1 , month=12, day=31)
                                        for i in range(1, (cron_date - y).days + 1):
                                            cala_date = y + timedelta(days=i)
                                            balance = self.remaining_leaves_of_day_by_date(emp, str(cala_date), item , is_month=False, is_years=False)
                                            no_year_balance = no_year_balance + (self.calc_not_balance_annual_leave(emp, cala_date) * balance)
                                            year_balance = year_balance + balance
                                    if is_month:
                                        cron_date = (holiday_cron_run_date.replace(day=1) + relativedelta.relativedelta(months=i + 1)) - timedelta(days=1)
                                        y = cron_date.replace(day=1)
                                        no_year_balance , year_balance = 0, 0
                                        for i in range(0, (cron_date - y).days + 1):
                                            cala_date = y + timedelta(days=i)
                                            balance = self.remaining_leaves_of_day_by_date(emp, str(cala_date), item , is_month=False, is_years=False)
                                            no_year_balance = no_year_balance + (self.calc_not_balance_annual_leave(emp, cala_date) * balance)
                                            year_balance = year_balance + balance
                                    item_values.append({'cron_run_date': cron_date, 'balance_leaves':year_balance, 'no_balance_leaves':no_year_balance})
                                    already_exist.write({
                                        'name': 'Yearly Allocation of ' + item.name + ' Leaves',
                                        'remaining_leaves':(already_exist.remaining_leaves + year_balance) - no_year_balance,
                                    })
                                already_exist.write({'holiday_ids': [(0, 0, item) for item in item_values]})
                            # TO DO cala dutartion if val days_save == 0 or set days_save BY ABUZAR 
                            # DONE call end method --- 
                            # self.reset_remaining_leaves(current_date, item, emp, already_exist,is_years)
                    elif item.leave_annual_type == 'save_annual_year':
                        # and item.number_of_holidays_save_years > 0:
                        current_date = (datetime.utcnow() + timedelta(hours=3)).date()  # replace with: current_date_time++
                        # current_date = datetime(2025, 12, 31).date()
                        current_date_val = current_date.year
                        old_year_date_val = current_date.year - 1  # previous year
                        end_of_save_year = datetime.strftime(current_date, "{0}-12-31 23:59:59".format(old_year_date_val))  # previous_year_end
                        end_of_save_year_value = datetime.strptime(str(end_of_save_year), "%Y-%m-%d 23:59:59").date()  # previous_year_end Date
                        start_of_new_year = datetime.strftime(first_hiring_date, "{0}-01-01".format(current_date_val))
                        start_of_save_year_value = datetime.strptime(str(start_of_new_year), "%Y-%m-%d").date()  # start of new year
                        working_days_old = (end_of_save_year_value - first_hiring_date).days + 1  # working days till end prv year عدد ايام عمل الموظف الي السنة الحالية
                        employee_working_years = item.number_of_holidays_save_years * 365  # balance of prev years to give?
                        
                        if working_days_old >= employee_working_years:
                            
                            remaining_leaves_of_day = self.remaining_leaves_of_day_by_date(emp, str(current_date), item , is_month=False, is_years=False)
                            already_exist = self.env['hr.holidays'].search([('employee_id', '=', emp.id),
                                                        ('holiday_status_id', '=', item.id),
                                                        ('type', '=', 'add'),
                                                        ('check_allocation_view', '=', 'balance')
                                                        ], limit=1, order="id desc")
                            if already_exist:
                                """
                                        Important note: 
                                            we are no longer saving years but carrying balance from year to the next only;
                                            according to Bakri Request done by Yousra.
                                """
                                if is_years:
                                    current_date = current_date.replace(year=current_date.year , month=12, day=31)
                                    current_date = datetime.strptime(str(current_date), DEFAULT_SERVER_DATE_FORMAT).date()
                                if is_month:
                                    if self.is_last_day_of_month(current_date):
                                        current_date = current_date
                                    else: 
                                        current_date = datetime.strptime(str(current_date), DEFAULT_SERVER_DATE_FORMAT).date()
                                        current_date = current_date.replace(day=1) - timedelta(days=1)
                                if not already_exist.holiday_ids:
                                    self.env['hr.inverse.holidays'].create({'holiday_id': already_exist.id, 'cron_run_date': current_date, })
                                holiday = already_exist.holiday_ids[-1]
                                if holiday.cron_run_date:
                                    cron_run_date1 = datetime.strptime(str(holiday.cron_run_date), DEFAULT_SERVER_DATE_FORMAT).date()
                                    current_date = datetime.strptime(str(current_date), DEFAULT_SERVER_DATE_FORMAT).date()
                                    if cron_run_date1 > current_date:
                                        continue
                                    delta = current_date - cron_run_date1  # timedelta
                                    months_date = cron_run_date1
                                    year = current_date.year - cron_run_date1.year
                                    months = (current_date.year - months_date.year) * 12 + (current_date.month - months_date.month) + 1
                                    item_values = []
                                    range_val = []
                                    range_val = range(1, delta.days + 1)
                                    if is_years:
                                        if year <= item.number_of_holidays_save_years:
                                            range_val = range(1, year + 1)
                                            end_day = (cron_run_date1.replace(day=1) + relativedelta.relativedelta(months=1)) - timedelta(days=1)
                                            end_date_cron = (end_day - cron_run_date1).days
                                            if end_date_cron > 0:
                                                no_year_balance , year_balance = 0, 0
                                                for i in range(1, end_date_cron + 1):
                                                    cala_date = cron_run_date1 + timedelta(days=i)
                                                    balance = self.remaining_leaves_of_day_by_date(emp, str(cala_date), item , is_month=False, is_years=False)
                                                    no_year_balance = no_year_balance + (self.calc_not_balance_annual_leave(emp, cala_date) * balance)
                                                    year_balance = year_balance + balance
                                                already_exist.write({
                                                    'name': 'Yearly Allocation of ' + item.name + ' Leaves',
                                                    'remaining_leaves': already_exist.remaining_leaves + year_balance - no_year_balance,
                                                })
                                                already_exist.write({'holiday_ids': [(0, 0, {'cron_run_date': end_day, 'balance_leaves':year_balance, 'no_balance_leaves':no_year_balance})]})
                                            
                                            complete_month = datetime.strptime(str(already_exist.holiday_ids[-1].cron_run_date), DEFAULT_SERVER_DATE_FORMAT).date()
                                            cron_run_date_y = 12 - complete_month.month
                                            for x in range(1, cron_run_date_y + 1):
                                                no_year_balance , year_balance = 0, 0
                                                end_day = (complete_month.replace(day=1) + relativedelta.relativedelta(months=x + 1)) - timedelta(days=1)
                                                y = end_day.replace(day=1)
                                                for i in range(0, (end_day - y).days + 1):
                                                    cala_date = y + timedelta(days=i)
                                                    balance = self.remaining_leaves_of_day_by_date(emp, str(cala_date), item , is_month=False, is_years=False)
                                                    no_year_balance = no_year_balance + (self.calc_not_balance_annual_leave(emp, cala_date) * balance)
                                                    year_balance = year_balance + balance
                                                already_exist.write({
                                                'name': 'Yearly Allocation of ' + item.name + ' Leaves',
                                                'remaining_leaves': (already_exist.remaining_leaves + year_balance) - no_year_balance,
                                                })
                                                already_exist.write({'holiday_ids': [(0, 0, {'cron_run_date': end_day, 'balance_leaves':year_balance, 'no_balance_leaves':no_year_balance})]})
                                        else:
                                            cron_run_date1 = current_date.replace(year=current_date.year - item.number_of_holidays_save_years, month=12, day=31)
                                            range_val = range(0, item.number_of_holidays_save_years + 1)
                                    if is_month:
                                        if year <= item.number_of_holidays_save_years:
                                            end_day = (cron_run_date1.replace(day=1) + relativedelta.relativedelta(months=1)) - timedelta(days=1)
                                            end_date_cron = (end_day - cron_run_date1).days
                                            if end_date_cron > 0:
                                                no_year_balance , year_balance = 0, 0
                                                for i in range(1, end_date_cron + 1):
                                                    cala_date = cron_run_date1 + timedelta(days=i)
                                                    balance = self.remaining_leaves_of_day_by_date(emp, str(cala_date), item , is_month=False, is_years=False)
                                                    no_year_balance = no_year_balance + (self.calc_not_balance_annual_leave(emp, cala_date) * balance)
                                                    year_balance = year_balance + balance
                                                already_exist.write({
                                                    'name': 'Yearly Allocation of ' + item.name + ' Leaves',
                                                    'remaining_leaves': already_exist.remaining_leaves + (year_balance - no_year_balance),
                                                })
                                                already_exist.write({'holiday_ids': [(0, 0, {'cron_run_date': end_day, 'balance_leaves':year_balance, 'no_balance_leaves':no_year_balance})]})
                                            range_val = range(1, months)
                                        else:
                                            cron_run_date1 = current_date.replace(year=current_date.year - item.number_of_holidays_save_years , month=1, day=31)
                                            range_val = range(0, (item.number_of_holidays_save_years) * 12 + (current_date.month - cron_run_date1.month) + 1)
                                    for i in range_val:
                                        no_year_balance , year_balance = 0, 0
                                        cron_date = cron_run_date1 + timedelta(days=i)
                                        balance = self.remaining_leaves_of_day_by_date(emp, str(cron_date), item , is_month=False, is_years=False)
                                        no_year_balance = no_year_balance + (self.calc_not_balance_annual_leave(emp, cron_date) * balance)
                                        year_balance = year_balance + balance
                                        if is_years:
                                            no_year_balance , year_balance = 0, 0
                                            cron_date = cron_run_date1.replace(year=cron_run_date1.year + i , month=12, day=31)
                                            y = cron_date.replace(year=cron_date.year - 1 , month=12, day=31)
                                            for i in range(1, (cron_date - y).days + 1):
                                                cala_date = y + timedelta(days=i)
                                                balance = self.remaining_leaves_of_day_by_date(emp, str(cala_date), item , is_month=False, is_years=False)
                                                no_year_balance = no_year_balance + (self.calc_not_balance_annual_leave(emp, cala_date) * balance)
                                                year_balance = year_balance + balance
                                        if is_month:
                                            cron_date = (cron_run_date1.replace(day=1) + relativedelta.relativedelta(months=i + 1)) - timedelta(days=1)
                                            y = cron_date.replace(day=1)
                                            no_year_balance , year_balance = 0, 0
                                            for i in range(0, (cron_date - y).days + 1):
                                                cala_date = y + timedelta(days=i)
                                                balance = self.remaining_leaves_of_day_by_date(emp, str(cala_date), item , is_month=False, is_years=False)
                                                no_year_balance = no_year_balance + (self.calc_not_balance_annual_leave(emp, cala_date) * balance)
                                                year_balance = year_balance + balance
                                        item_values.append({'cron_run_date': cron_date, 'balance_leaves':year_balance, 'no_balance_leaves':no_year_balance})
                                        already_exist.write({
                                            'name': 'Yearly Allocation of ' + item.name + ' Leaves',
                                            'remaining_leaves':(already_exist.remaining_leaves + year_balance) - no_year_balance,
                                        })
                                    already_exist.write({'holiday_ids': [(0, 0, item) for item in item_values]})
                                else:
                                    holiday.write({'cron_run_date': current_date, 'balance_leaves':remaining_leaves_of_day })
                                    already_exist.write({
                                        'name': 'Yearly Allocation of ' + item.name + ' Leaves',
                                        'remaining_leaves': already_exist.remaining_leaves + float(remaining_leaves_of_day),
                                    })
                            else:
                                year_balance = 0
                                no_year_balance = 0
                                start_of_save_year_value = start_of_save_year_value.replace(year=(current_date.year - item.number_of_holidays_save_years))
                                working_days_new = ((current_date - start_of_save_year_value).days + 1) 
                                if not is_years and  not is_month:
                                    for index in range(0, working_days_new):
                                        current_date = start_of_save_year_value + timedelta(days=index)
                                        balance = self.remaining_leaves_of_day_by_date(emp, str(current_date), item , is_month=False, is_years=False)
                                        no_year_balance = no_year_balance + (self.calc_not_balance_annual_leave(emp, current_date) * balance)
                                        year_balance = year_balance + balance
                                if is_years:
                                    year_balance = 0
                                    remaining_leaves_of_day = 0
                                    current_date = current_date.replace(year=current_date.year , month=12, day=31)
                                    year_new = (current_date.year - first_hiring_date.year)
                                    year_new = min(year_new, item.number_of_holidays_save_years) + 1
                                    y = current_date.replace(year=current_date.year - year_new , month=12, day=31)
                                    for i in range(1, (current_date - y).days + 1):
                                        cala_date = y + timedelta(days=i)
                                        balance = self.remaining_leaves_of_day_by_date(emp, str(cala_date), item , is_month=False, is_years=False)
                                        no_year_balance = no_year_balance + (self.calc_not_balance_annual_leave(emp, cala_date) * balance)
                                        year_balance = year_balance + balance
                                if is_month:
                                    year_balance = 0
                                    remaining_leaves_of_day = 0
                                    current_date = (current_date.replace(day=1) + relativedelta.relativedelta(months=0)) - timedelta(days=1)
                                    first_hiring_date = datetime.strptime(str(emp.first_hiring_date), "%Y-%m-%d").date()
                                    remaining_leaves_of_day = self.remaining_leaves_of_day_by_date(emp, str(current_date), item , is_month=is_month, is_years=is_years)
                                    months_date = first_hiring_date
                                    months_new = (current_date.year - months_date.year) * 12 + current_date.month - months_date.month
                                    save_month = item.number_of_holidays_save_years * 12
                                    min_months = min(months_new, save_month)
                                    if months_new > save_month:
                                        last_date = current_date.replace(year=current_date.year - 1, month=12, day=31)
                                        open_years_month = (current_date.year - last_date.year) * 12 + current_date.month - last_date.month
                                        min_months = min_months + open_years_month
                                    y = (current_date - relativedelta.relativedelta(months=min_months - 1)).replace(day=1)
                                    for i in range(0, (current_date - y).days + 1):
                                        cala_date = y + timedelta(days=i)
                                        balance = self.remaining_leaves_of_day_by_date(emp, str(cala_date), item , is_month=False, is_years=False)
                                        no_year_balance = no_year_balance + (self.calc_not_balance_annual_leave(emp, cala_date) * balance)
                                        year_balance = year_balance + balance
                                already_exist = self.env['hr.holidays'].create({
                                    'name': 'Yearly Allocation of ' + item.name + ' Leaves',
                                    'employee_id': emp.id,
                                    'holiday_status_id': item.id,
                                    'check_allocation_view': 'balance',
                                    'type': 'add',
                                    'remaining_leaves': year_balance - no_year_balance,
                                })
                                self.env['hr.inverse.holidays'].create({'holiday_id': already_exist.id, 'cron_run_date': current_date, 'balance_leaves':year_balance , 'no_balance_leaves':no_year_balance })
                        else:
                            if is_years:
                                current_date = current_date.replace(year=current_date.year , month=12, day=31)
                                current_date = datetime.strptime(str(current_date), DEFAULT_SERVER_DATE_FORMAT).date()
                            if is_month:
                                current_date = (current_date.replace(day=1) + relativedelta.relativedelta(months=0)) - timedelta(days=1)
                            days_of_new_employee = (current_date - first_hiring_date).days + 1
                            if days_of_new_employee >= item.number_of_days:
                                already_exist = self.env['hr.holidays'].search([('employee_id', '=', emp.id),
                                                                                ('holiday_status_id', '=', item.id),
                                                                                ('type', '=', 'add'),
                                                                                ('check_allocation_view', '=', 'balance')
                                                                                ], limit=1, order="id desc")
                                if not already_exist:
                                    balance_leaves = self.remaining_leaves_of_day_by_date(emp, str(first_hiring_date), item , is_month=False, is_years=False)
                                    already_exist = self.env['hr.holidays'].create({
                                            'name': 'Yearly Allocation of ' + item.name + ' Leaves',
                                            'employee_id': emp.id,
                                            'holiday_status_id': item.id,
                                            'check_allocation_view': 'balance',
                                            'type': 'add',
                                            'remaining_leaves': balance_leaves,
                                        })
                                    self.env['hr.inverse.holidays'].create(
                                            {'holiday_id': already_exist.id, 'cron_run_date': first_hiring_date, 'balance_leaves':balance_leaves })
                                    if not is_years and not is_month:
                                        working_days_new = ((current_date - first_hiring_date).days) + 1
                                        year_balance = already_exist.remaining_leaves or 0 
                                        no_balance = 0
                                        for index in range(1, working_days_new):
                                            current_date = first_hiring_date + timedelta(days=index)
                                            balance = self.remaining_leaves_of_day_by_date(emp, str(current_date), item , is_month=False, is_years=False)
                                            no_balance = no_balance + self.calc_not_balance_annual_leave(emp, current_date) * balance
                                            year_balance = year_balance + balance
                                        already_exist.holiday_ids[-1].cron_run_date = current_date
                                        already_exist.holiday_ids[-1].balance_leaves = year_balance
                                        already_exist.holiday_ids[-1].no_balance_leaves = no_balance
                                        already_exist.remaining_leaves = year_balance - no_balance
                                if already_exist:
                                    if not already_exist.holiday_ids:
                                        current_date_new = (datetime.utcnow() + timedelta(hours=3)).date()
                                        balance_leaves = self.remaining_leaves_of_day_by_date(emp, str(current_date_new), item , is_month=False, is_years=False)
                                        self.env['hr.inverse.holidays'].create({'holiday_id': already_exist.id, 'cron_run_date': current_date_new, 'balance_leaves':balance_leaves })
                                        holiday.write({'cron_run_date': current_date, })
                                        already_exist.write({
                                            'name': 'Yearly Allocation of ' + item.name + ' Leaves',
                                            'remaining_leaves': already_exist.remaining_leaves + balance_leaves,
                                        })
                                    else:
                                        holiday = already_exist.holiday_ids[-1]
                                        if holiday.cron_run_date:
                                            cron_run_date1 = datetime.strptime(str(holiday.cron_run_date), DEFAULT_SERVER_DATE_FORMAT).date()
                                            if cron_run_date1 >= current_date:
                                                continue
                                            current_date1 = datetime.strptime(str(current_date), DEFAULT_SERVER_DATE_FORMAT).date()
                                            delta = current_date1 - cron_run_date1  # timedelta
                                            months_date = cron_run_date1
                                            months = (current_date1.year - months_date.year) * 12 + current_date1.month - months_date.month
                                            year = current_date1.year - cron_run_date1.year 
                                            item_values = []
                                            range_val = []
                                            range_val = range(1, delta.days + 1)
                                            if is_years:
                                                range_val = range(1, year + 1)
                                                end_day = (cron_run_date1.replace(day=1) + relativedelta.relativedelta(months=1)) - timedelta(days=1)
                                                end_date_cron = (end_day - cron_run_date1).days
                                                if end_date_cron > 0:
                                                    balance_leaves = 0
                                                    no_year_balance = 0
                                                    start_date = (end_day - cron_run_date1).days + 1
                                                    for index in range(1, start_date):
                                                        calc_date = cron_run_date1 + timedelta(days=index)
                                                        balance = self.remaining_leaves_of_day_by_date(emp, str(calc_date), item , is_month=False, is_years=False)
                                                        no_year_balance = no_year_balance + (self.calc_not_balance_annual_leave(emp, calc_date) * balance)
                                                        balance_leaves = balance_leaves + balance 
                                                    # balance_leaves = balance_leaves - no_year_balance
                                                    already_exist.write({
                                                        'name': 'Yearly Allocation of ' + item.name + ' Leaves',
                                                        'remaining_leaves': already_exist.remaining_leaves + balance_leaves - no_year_balance,
                                                    })
                                                    already_exist.write({'holiday_ids': [(0, 0, {'cron_run_date': end_day, 'balance_leaves':balance_leaves, 'no_balance_leaves':no_year_balance})]})
                                                complete_month = datetime.strptime(str(already_exist.holiday_ids[-1].cron_run_date), DEFAULT_SERVER_DATE_FORMAT).date()
                                                cron_run_date_y = 12 - complete_month.month
                                                for x in range(1, cron_run_date_y + 1):
                                                    end_day = (complete_month.replace(day=1) + relativedelta.relativedelta(months=x + 1)) - timedelta(days=1)
                                                    balance_leaves = 0
                                                    no_year_balance = 0
                                                    start_date = (end_day - end_day.replace(day=1)).days + 1
                                                    for index in range(0, start_date):
                                                        calc_date = end_day.replace(day=1) + timedelta(days=index)
                                                        balance = self.remaining_leaves_of_day_by_date(emp, str(calc_date), item , is_month=False, is_years=False)
                                                        no_year_balance = no_year_balance + (self.calc_not_balance_annual_leave(emp, calc_date) * balance)
                                                        balance_leaves = balance_leaves + balance
                                                    # balance_leaves = balance_leaves - no_year_balance
                                                    already_exist.write({
                                                    'name': 'Yearly Allocation of ' + item.name + ' Leaves',
                                                    'remaining_leaves': already_exist.remaining_leaves + balance_leaves - no_year_balance
                                                    })
                                                    already_exist.write({'holiday_ids': [(0, 0, {\
                                                        'cron_run_date': end_day, \
                                                        'balance_leaves':balance_leaves, \
                                                        'no_balance_leaves':no_year_balance})]})
                                            if is_month:
                                                balance_leaves = 0
                                                no_year_balance = 0
                                                end_day = (cron_run_date1.replace(day=1) + relativedelta.relativedelta(months=1)) - timedelta(days=1)
                                                end_date_cron = (end_day - cron_run_date1).days
                                                if end_date_cron > 0:
                                                    for index in range(1, end_date_cron + 1):
                                                        calc_date = cron_run_date1 + timedelta(days=index)
                                                        balance = self.remaining_leaves_of_day_by_date(emp, str(calc_date), item , is_month=False, is_years=False)
                                                        no_year_balance = no_year_balance + (self.calc_not_balance_annual_leave(emp, calc_date) * balance)   
                                                        balance_leaves = balance_leaves + balance                                        
                                                    # balance_leaves = balance_leaves - no_year_balance
                                                    already_exist.write({
                                                        'name': 'Yearly Allocation of ' + item.name + ' Leaves',
                                                        'remaining_leaves': already_exist.remaining_leaves + balance_leaves - no_year_balance,
                                                    })
                                                    already_exist.write({'holiday_ids': [(0, 0, {'cron_run_date': end_day, 'balance_leaves':balance_leaves, 'no_balance_leaves':no_year_balance})]})                                                
                                                range_val = range(1, months + 1)
                                            for i in range_val:
                                                cron_date = cron_run_date1 + timedelta(days=i)
                                                balance_leaves = self.remaining_leaves_of_day_by_date(emp, str(cron_date), item , is_month=False, is_years=False)
                                                no_year_balance = self.calc_not_balance_annual_leave(emp, cron_date) * balance_leaves
                                                if is_years:
                                                    cron_date = cron_run_date1.replace(year=cron_run_date1.year + i , month=12, day=31)
                                                if is_month:
                                                    cron_date = (cron_run_date1.replace(day=1) + relativedelta.relativedelta(months=i + 1)) - timedelta(days=1)
                                                if current_date >= cron_date:
                                                    if is_month:
                                                        balance_leaves = 0
                                                        no_year_balance = 0
                                                        start_date = cron_date.replace(day=1)
                                                        start_days = (cron_date - cron_date.replace(day=1)).days + 1
                                                        for index in range(0, start_days):
                                                            calc_date = start_date + timedelta(days=index)
                                                            balance = self.remaining_leaves_of_day_by_date(emp, str(calc_date), item , is_month=False, is_years=False)
                                                            no_year_balance = no_year_balance + (self.calc_not_balance_annual_leave(emp, calc_date) * balance)
                                                            balance_leaves = balance_leaves + balance 
                                                    if is_years:
                                                        balance_leaves = 0
                                                        no_year_balance = 0
                                                        start_date = cron_date.replace(year=cron_date.year - 1)
                                                        start_date_number = (cron_date - start_date).days + 1
                                                        for index in range(1, start_date_number):
                                                            calc_date = start_date + timedelta(days=index)
                                                            balance = self.remaining_leaves_of_day_by_date(emp, str(calc_date), item , is_month=False, is_years=False)
                                                            no_year_balance = no_year_balance + (self.calc_not_balance_annual_leave(emp, calc_date) * balance)
                                                            balance_leaves = balance_leaves + balance 
                                                    remaining_leaves_of_day = balance_leaves - no_year_balance
                                                    item_values.append({ 'cron_run_date': cron_date, 'balance_leaves':balance_leaves, 'no_balance_leaves':no_year_balance})
                                                    already_exist.write({
                                                        'name': 'Yearly Allocation of ' + item.name + ' Leaves',
                                                        'remaining_leaves': already_exist.remaining_leaves + float(balance_leaves - no_year_balance),
                                                    })
                                            already_exist.write({'holiday_ids': [(0, 0, item) for item in item_values]})
                                        else:
                                            current_date_new = (datetime.utcnow() + timedelta(hours=3)).date()
                                            holiday.write({'cron_run_date': current_date_new})
                    self.reset_remaining_leaves(current_date, item, emp, already_exist, is_years)
                        
                elif item.leave_type != 'annual' and (item.gender == 'both' or item.gender == emp.gender):
                    if days >= item.number_of_days:
                        current_date = (datetime.utcnow() + timedelta(hours=3)).date()
                        already_exist = self.env['hr.holidays'].search([('employee_id', '=', emp.id),
                                                                        ('holiday_status_id', '=', item.id),
                                                                        ('type', '=', 'add'),
                                                                        ('check_allocation_view', '=', 'balance')
                                                                        ], limit=1, order="id desc")
                        remaining_leaves = item.duration
                        if already_exist:
                            # Renewal Balance of Sick Leave
                            self.renewal_balance_sick_leave(emp, item, already_exist, current_date)
                            # Renewal Balance of Unpaid Leave
                            self.renewal_balance_unpaid_leave(emp, item, already_exist, current_date)
                            # Renewal Balance of  Last Day OF Year
                            # leave_type = ['exam','death'] # Just set type leave in list add new Leave 
                            self.renewal_balance_leaves_last_day_of_year(current_date, item, already_exist , emp)
                            # Renewal Balance of  daily
                            #renewal_daily_leave_type = ['death', 'new_baby']  # Just set type leave in list add new Leave 
                            self.renewal_balance_leaves_daily(current_date, item, already_exist )
                        else:
                            hr_holidays = self.env['hr.holidays'].create({
                                'name': 'Yearly Allocation of ' + item.name + ' Leaves',
                                'employee_id': emp.id,
                                'holiday_status_id': item.id,
                                'remaining_leaves': remaining_leaves,
                                'check_allocation_view': 'balance',
                                'type': 'add'
                            })
                            self.env['hr.inverse.holidays'].create({'holiday_id': hr_holidays.id,
                                                                    'cron_run_date': current_date,
                                                                    'balance_leaves':remaining_leaves})
    
    def is_last_day_of_month(self, date):
        # Get the last day of the month for the given date
        last_day_of_month = (date.replace(day=1) \
                            .replace(month=date.month % 12 + 1, day=1) \
                            -timedelta(days=1)).day
        # Return True if the given date is the last day of the month, False otherwise
        return date.day == last_day_of_month

    def is_last_day_of_year(self, date):
        # Get the last day of the year for the given date
        last_day_of_year = datetime(date.year, 12, 31).date()
        # Check if the given date is the same as the last day of the year
        return date == last_day_of_year

    def renewal_balance_leaves_daily(self , current_date, item, already_exist ):
        renewal_daily_leave_type = ['death', 'new_baby'] # Just set type leave in list add new Leave 
        if (item.leave_type in renewal_daily_leave_type) and (already_exist.remaining_leaves != item.duration):
            duration = item.duration
            already_exist.write({'remaining_leaves': duration })
            self.env['hr.inverse.holidays'].create({'holiday_id': already_exist.id,
                                                        'cron_run_date': current_date,
                                                        'balance_leaves':duration})

    def renewal_balance_leaves_last_day_of_year(self , current_date, item, already_exist , emp):
        leave_type = ['exam', 'marriage','parental','emergency']#'death']  # Just set type leave in list add new Leave 
        if (item.leave_type in leave_type) and (already_exist.remaining_leaves < item.duration):
            duration = item.duration  # >= already_exist.remaining_leaves and item.duration  or already_exist.remaining_leaves
            # current_date = datetime(2024, 12, 31).date()
            
            cron_run_date = current_date
            if already_exist.holiday_ids:
                holiday = already_exist.holiday_ids[-1]
                cron_run_date = datetime.strptime(str(holiday.cron_run_date or current_date), DEFAULT_SERVER_DATE_FORMAT).date()
            current_date = current_date + timedelta(days=1)
            current_date = current_date.replace(year=current_date.year , month=12, day=31)  # last day curent year
            start_date = current_date.replace(day=1).replace(month=1)

            domain = [
                        ('employee_id', '=', emp.id),
                        ('type', '=', 'remove'),
                        ('date_from', '<=', str(current_date)),
                        ('date_to', '>=', str(start_date)),
                        ('state', 'in', ['validate1']),  # Added comma here
                        ('holiday_status_id', '=', item.id),  # Fixed typo in the variable name
                    ]
            diff_years = current_date.year - cron_run_date.year
            holiday_current_date_ids = self.env['hr.holidays'].read_group(domain, ['date_from', 'number_of_days'], ['date_from:year'])
            if (diff_years >= 0) and  (current_date > cron_run_date):
                days = (current_date - start_date).days + 1
                total_day = 0
                if holiday_current_date_ids:
                    for day in range(0, days):
                        calc_date = start_date + timedelta(days=day)
                        holiday_current_date_ids = self.env['hr.holidays'].search([
                        ('employee_id', '=', emp.id),
                        ('type', '=', 'remove'),
                        ('date_from', '<=', str(calc_date)),
                        ('date_to', '>=', str(calc_date)),
                        ('state', 'in', ['validate1']),  # Added comma here
                        ('holiday_status_id', '=', item.id),  # Fixed typo in the variable name
                    ])
                        if holiday_current_date_ids:
                            total_day = total_day + 1
                remaining_leaves = duration - total_day
                already_exist.write({'remaining_leaves': remaining_leaves > 0 and remaining_leaves  or 0 })
                self.env['hr.inverse.holidays'].create({'holiday_id': already_exist.id,
                                                        'cron_run_date': current_date,
                                                        'balance_leaves':duration})    
    
    def renewal_balance_sick_leave(self, emp, item, already_exist, current_date):
        if item.leave_type != 'sick':
            return True
        # current_date = datetime(2024, 11, 23).date()
        while True:
            # old_sick_leave = self._get_latest_approved_leave(emp, item)

            # if not old_sick_leave:
            #     break
            cron_run_date = emp.first_hiring_date
            if already_exist.holiday_ids:
                cron_run_date = already_exist.holiday_ids[-1].cron_run_date

            old_sick_leave = self._get_latest_approved_leave_after_date(emp, item, cron_run_date)
            
            if not old_sick_leave:
                break

            holiday_id = old_sick_leave[-1]
            date_from = fields.Date.from_string(holiday_id.date_from)
            next_years = date_from.replace(year=date_from.year + 1)
            number_of_years = relativedelta.relativedelta(current_date, date_from).years
            if number_of_years >= 1:
                self._create_inverse_holiday(already_exist, next_years)
                remaining_leaves = self._calculate_remaining_leaves(emp , item, next_years)
                already_exist.write({
                    'name': f'Yearly Allocation of {item.name} Leaves',
                    'remaining_leaves': remaining_leaves,
                })
            else:
                break

        return True

    def _get_latest_approved_leave(self, emp, item):
        domain = [
            ('employee_id', '=', emp.id),
            ('holiday_status_id', '=', item.id),
            ('type', '=', 'remove'),
            ('state', 'in', ['validate1'])
        ]
        return self.env['hr.holidays'].search(domain, limit=1, order="date_from desc")

    def _get_latest_approved_leave_after_date(self, emp, item, date):
        domain = [
            ('employee_id', '=', emp.id),
            ('holiday_status_id', '=', item.id),
            ('type', '=', 'remove'),
            ('state', 'in', ['validate1']),
            ('date_from', '>', str(date))
        ]
        return self.env['hr.holidays'].search(domain, order="date_from desc")

    def _create_inverse_holiday(self, already_exist, next_years):
        self.env['hr.inverse.holidays'].create({
            'holiday_id': already_exist.id,
            'cron_run_date': next_years,
        })

    def _calculate_remaining_leaves(self, emp,item, next_years):
        domain = [
            ('employee_id', '=', emp.id),
            ('holiday_status_id', '=', item.id),
            ('type', '=', 'remove'),
            ('state', 'in', ['validate1']),
            ('date_from', '<=', str(next_years.replace(year=next_years.year + 1))),
            ('date_from', '>', str(next_years))
        ]
        old_sick_leave = self.env['hr.holidays'].search(domain, order="date_from desc")
        return float(item.duration) - sum(old_sick_leave.mapped('number_of_days_temp'))

    def renewal_balance_unpaid_leave(self, emp, item, already_exist, current_date):
        if item.type_unpaid == 'termination':
            if already_exist.holiday_ids:
                last_update_date = datetime.strptime(str(already_exist.holiday_ids[-1].cron_run_date),
                                                     DEFAULT_SERVER_DATE_FORMAT)
                next_run_date = current_date.replace(year=last_update_date.year + item.period_giving_balance)
                if current_date >= next_run_date:
                    already_exist.write({
                        'name': 'Yearly Allocation of ' + item.name + ' Leaves',
                        'remaining_leaves': float(item.duration),
                    })
                    self.env['hr.inverse.holidays'].create({'holiday_id': already_exist.id,
                                                            'cron_run_date': current_date, })
        return True

    @api.onchange('employee_id')
    def _get_leaves_ids(self):
        for item in self:
            item.holiday_status_id = False
            genders, emp_types, durations = ['both', ], ['all', ], ['all', ]
            genders.append(item.employee_id.gender)
            emp_types.append(item.employee_type)
            domain = [('active', '=', True), ('gender', 'in', genders), ('emp_type', 'in', emp_types)]
            if item.employee_id.contract_id.contract_description == 'permanent':
                durations.append(item.employee_id.contract_id.contract_duration)
                domain += [('contract_duration', 'in', durations)]
            return {'domain': {'holiday_status_id': [('id', 'in', self.env['hr.holidays.status'].search(domain).ids)]}}

    def draft_state(self):
        for item in self:
            item._remove_followers_holiday()
            have_cancel_request = self.env['leave.cancellation'].search([('leave_request_id', '=', item.id),
                                                                         ('state', 'not in', ('draft', 'refuse'))])
            have_return_from_leave = self.env['return.from.leave'].search(
                [('leave_request_id', '=', item.id), ('state', 'not in', ('draft', 'refuse'))])
            if have_cancel_request:
                raise exceptions.Warning(_("You can't set this request to draft as it's already have a cancel request"))
            if have_return_from_leave:
                raise exceptions.Warning(_("You can't set this request to draft as it's already have a return from "
                                           "leave request"))

            Module = self.env['ir.module.module'].sudo()
            modules_reconcile = Module.search([('state', '=', 'installed'), ('name', '=', 'exp_payroll_loans')])
            if modules_reconcile:
                have_reconcile_leaves = self.env['reconcile.leaves'].search(
                    [('yearly_vacation', '=', item.id), ('state', 'not in', ('draft', 'refuse'))])

                if have_reconcile_leaves:
                    raise ValidationError(
                        _("You can't set this request to draft as it's already have Reconcile Holiday"))

            if item.state == 'validate1':
                item.reconcile_holiday_balance()
                item.remove_delegated_access()
                item.write({'state': 'draft','request_done':False})
                item.call_cron_function()
                self.check_allocation_balance_annual('addition')
            # if item.state == 'validate1':
            #     self.reconcile_holiday_balance()
        self.write({'state': 'draft'})

    def confirm(self):
        for item in self:
            self._compute_leave_balance()
            item._remove_followers_holiday()
            ## ticket allowance per year ###
            if item.issuing_ticket == 'yes':
                current_date = (datetime.utcnow() + timedelta(hours=3)).date()
                if item.employee_id.contract_id.hiring_date:
                   employee_date = datetime.strptime(str(item.employee_id.contract_id.hiring_date), "%Y-%m-%d").date()
                else:
                   employee_date = datetime.strptime(str(item.employee_id.contract_id.date_start), "%Y-%m-%d").date()
                last_ticket = self.env['hr.ticket.request'].search(
                    [('employee_id', '=', item.employee_id.id), ('state', 'not in', ['draft', 'refuse'])],
                    order='id desc', limit=1)
                if last_ticket:
                    last_ticket_date = datetime.strptime(str(last_ticket.request_date), "%Y-%m-%d").date()
                    dif2 = relativedelta.relativedelta(current_date, last_ticket_date)
                    dif_ticket_date = dif2.years * 12 + dif2.months
                    if dif_ticket_date < item.employee_id.contract_id.period_ticket:
                        raise exceptions.Warning(_(
                            'Sorry The employee can not be given a ticket allowance until contractual year after the previous ticket'))

                dif1 = relativedelta.relativedelta(current_date, employee_date)
                dif_employee_date = dif1.years * 12 + dif1.months
                if dif_employee_date < item.employee_id.contract_id.period_ticket and item.type == 'remove':
                    raise exceptions.Warning(_(
                        'Sorry The employee can not be given a ticket allowance unless a contractual year has been established'))

            if item.issuing_deliver_custdy == 'yes' and item.type == 'remove':
                Module = self.env['ir.module.module'].sudo()
                emp_modules = Module.search([('state', '=', 'installed'), ('name', '=', 'exp_employee_custody')])
                petty_cash_modules = Module.search(
                    [('state', '=', 'installed'), ('name', '=', 'hr_expense_petty_cash')])
                if emp_modules:
                    custody_ids = self.env['custom.employee.custody'].search(
                        [('employee_id', '=', item.employee_id.id),
                         ('state', 'not in', ['done', 'refuse', 'draft'])]).ids
                    if custody_ids:
                        raise exceptions.Warning(_(
                            'Sorry employee have custody he must deliver his custody to take this request'))
                if petty_cash_modules:
                    payment_ids = self.env['petty.cash'].search(
                        [('partner_id', '=', self.employee_id.user_id.partner_id.id),
                         ('state', 'in', ['submit', 'direct', 'fm', 'ceo', 'accepted', 'validate'])]).ids

                    if payment_ids:
                        raise exceptions.Warning(_(
                            'Sorry employee have custody he must deliver his custody to take this request'))
            if item.holiday_status_id.attach_chick == True and item.type == 'remove':
                if item.attach_ids:
                    for rec in item.attach_ids:
                        if not rec.datas:
                            raise exceptions.Warning(_('Attach the attachment to the Document %s') % (rec.name))
                else:
                    raise exceptions.Warning(_('Sorry This %s requires a Documents To Be Attached To Approve') % (
                        item.holiday_status_id.name))

        self.set_date()
        self._chick_leave_balance()
        self._check_number_of_days()
        self.write({'state': 'confirm'})

    def hr_manager(self):
        self._compute_leave_balance()
        self._remove_followers_holiday()
        if not self.replace_by and self.type == 'remove':
            if self.holiday_status_id.alternative_chick == True and self.number_of_days_temp >= self.holiday_status_id.alternative_days:
               raise exceptions.Warning(_('Select employee Replacement before The approve holiday Request'))
            if self.delegate_acc == True:
               raise exceptions.Warning(_('The replacement Employee Must be entered To Giving him Access'))
        if self.holiday_status_id.attach_chick == True and self.type == 'remove':
            if self.attach_ids:
                for rec in self.attach_ids:
                    if not rec.datas:
                        raise exceptions.Warning(_('Attach the attachment to the Document %s') % (rec.name))
            else:
                raise exceptions.Warning(
                    _('Sorry This %s requires a Documents To Be Attached To Approve') % (self.holiday_status_id.name))
        #The Approval For The Direct Manager only
        for rec in self:
           manager = rec.sudo().employee_id.parent_id
           hr_manager = rec.sudo().employee_id.company_id.hr_manager_id
           if manager:
              if manager.user_id.id == rec.env.uid or hr_manager.user_id.id == rec.env.uid:
                 rec._chick_leave_balance()
                 rec.write({'state': 'validate'})
              else:
                  raise exceptions.Warning(_("Sorry, The Approval For The Direct Manager '%s' Only OR HR Manager!")%(rec.employee_id.parent_id.name))
           else:
               rec._chick_leave_balance()
               rec.write({'state': 'validate'})

        #self._chick_leave_balance()
        #self.write({'state': 'validate'})

    def approved(self):
        self.check_sickness_leave_approval()
        self._chick_leave_balance()
        self.write({'state': 'approved'})

    def financial_manager(self):
        for item in self:
            item._remove_followers_holiday()
            if not item.replace_by and item.type == 'remove':
                if item.holiday_status_id.alternative_chick == True and item.number_of_days_temp >= item.holiday_status_id.alternative_days:
                   raise exceptions.Warning(_('Select employee Replacement before The approve holiday Request'))
                if item.delegate_acc == True:
                   raise exceptions.Warning(_('The replacement Employee Must be entered To Giving him Access'))

            current_date = (datetime.utcnow() + timedelta(hours=3)).date()
            employee_balance = self.env['hr.holidays'].search([('employee_id', '=', item.employee_id.id),
                                                               ('holiday_status_id', '=', item.holiday_status_id.id),
                                                               ('type', '=', 'add'),
                                                               ('check_allocation_view', '=', 'balance')],
                                                              order='id desc', limit=1)
            employee_allocation = self.env['hr.holidays'].search([('employee_id', '=', item.employee_id.id),
                                                                  ('holiday_status_id', '=', item.holiday_status_id.id),
                                                                  ('type', '=', 'add'),
                                                                  ('check_allocation_view', '=', 'allocation')],
                                                                 order='id desc', limit=1)
            if employee_balance:
                if item.type == 'remove' and item.request_done==False:
                    employee_balance.write({
                        'remaining_leaves': employee_balance.remaining_leaves - item.number_of_days_temp,
                        'leaves_taken': employee_balance.leaves_taken + item.number_of_days_temp,
                    })
                    if item.issuing_ticket == 'yes':
                        self.env['hr.ticket.request'].create({
                            'employee_id': item.employee_id.id,
                            'leave_request_id': item.id,
                            'request_for': item.ticket_cash_request_for,
                            'request_type': item.ticket_cash_request_type.id,
                            # 'state':item.submit,
                        })

                    if item.issuing_exit_return == 'yes':
                        self.env['hr.exit.return'].create({
                            'employee_id': item.employee_id.id,
                            'leave_request_id': item.id,
                            'request_for': item.ticket_cash_request_for,
                            # 'state':item.request,
                        })
                    if item.issuing_clearance_form == 'yes':
                        self.env['hr.clearance.form'].create({
                            'employee_id': item.employee_id.id,
                            'leave_request_id': item.id,
                            'request_for': item.ticket_cash_request_for,
                            'clearance_type': 'vacation',
                            'date_deliver_work': item.date_from,
                            'date': current_date,
                        })
                    # self.env['hr.sick.leave'].create({
                    #     'leave_request': item.name,
                    #     'date_from': item.date_from,
                    #     'date_to':item.date_to,
                    #     'duration':item.number_of_days_temp,
                    #     'status':item.state,
                    #     'allocation_start_date':item.date_from,
                    #     'allocation_end_date':item.date_to,
                    #     'sick_relation':item.employee_id.id
                    #
                    # })
                else:
                    employee_balance.write({
                        'name': 'Yearly Allocation of ' + item.holiday_status_id.name + ' Leaves',
                        'employee_id': item.employee_id.id,
                        'holiday_status_id': item.holiday_status_id.id,
                        'remaining_leaves': employee_balance.remaining_leaves + employee_allocation.number_of_days_temp,
                        'type': 'add',
                    })
            else:
                hr_holidays = self.env['hr.holidays'].create({
                    'name': 'Yearly Allocation of ' + item.holiday_status_id.name + ' Leaves',
                    'number_of_days_temp': employee_allocation.number_of_days_temp,
                    'employee_id': item.employee_id.id,
                    'holiday_status_id': item.holiday_status_id.id,
                    'remaining_leaves': employee_allocation.number_of_days_temp,
                    'check_allocation_view': 'balance',
                    'type': 'add',
                })
                self.env['hr.inverse.holidays'].create(
                    {'holiday_id': hr_holidays.id,
                     'cron_run_date': current_date, })
            # if item.delegate_acc:
            #     item.delegate_access()

        self._chick_leave_balance()
        self.check_sickness_leave_approval()
        self.write({'state': 'validate1','request_done': True})
        self.send_email()
        self.call_cron_function()
        self.check_allocation_balance_annual('deduction')

    def check_allocation_balance_annual(self, action):
        if self.type == 'remove':
            start_date = datetime.strptime(str(self.date_from), DEFAULT_SERVER_DATETIME_FORMAT)
            end_date = datetime.strptime(str(self.date_to), DEFAULT_SERVER_DATETIME_FORMAT)
            delta = timedelta(days=1)
            if self.holiday_status_id.not_balance_annual_leave:
                balance_holiday_id = self.env['hr.holidays'].search(
                    [('employee_id', '=', self.employee_id.id), ('type', '=', 'add'),
                     ('holiday_status_id.leave_type', '=', 'annual'),
                     ('check_allocation_view', '=', 'balance')
                     ], order='id desc', limit=1)
                while start_date <= end_date:
                    current_date = start_date.strftime("%Y-%m-%d")
                    remaining_leave_to_deduct = self.remaining_leaves_of_day_by_date(self.employee_id, current_date,
                                                                                     balance_holiday_id.holiday_status_id)
                    if action == 'deduction' and \
                            current_date in balance_holiday_id.holiday_ids.mapped('cron_run_date'):
                        balance_holiday_id.write({
                            'remaining_leaves': balance_holiday_id.remaining_leaves - float(remaining_leave_to_deduct)
                        })
                        balance_holiday_id.holiday_ids.filtered(lambda t: t.cron_run_date == current_date).unlink()
                    if action == 'addition' and \
                            current_date not in balance_holiday_id.holiday_ids.mapped('cron_run_date'):
                        balance_holiday_id.write({
                            'remaining_leaves': balance_holiday_id.remaining_leaves + float(remaining_leave_to_deduct)
                        })
                        self.env['hr.inverse.holidays'].create({'holiday_id': balance_holiday_id.id,
                                                                'cron_run_date': current_date, })
                    start_date += delta
        return True

    def send_email(self):
        if self.replace_by:
            template = self.sudo().env.ref('hr_holidays_public.email_template_employee_replace', False)
            template.sudo().send_mail(self.id)

    def check_sickness_leave_approval(self):
        for leave in self:
            if leave.type == 'remove' and leave.holiday_status_id.leave_type == 'sick':
                emp_sickness = self.env['hr.holidays'].search([('employee_id', '=', self.employee_id.id),
                                            ('type', '=', 'remove'),
                                            ('state', 'not in', ('refuse', 'cancel', 'validate1')),
                                            ('holiday_status_id.leave_type', '=', 'sick'),
                                            ('holiday_status_id', '!=', self.holiday_status_id.id),
                                            ('holiday_status_id.sickness_severity', '<',
                                             self.holiday_status_id.sickness_severity)]
                                           )
                if emp_sickness:
                    msg = ''
                    for sk in emp_sickness:
                        msg += sk.display_name + ' - ' + sk.date_from + '\n'
                    raise exceptions.Warning(_('Sorry you can not approve this leave while following '
                                               'leaves are not approved yet \n %s') % (msg))

    def call_cron_function(self):
        if self.date_from and self.date_to and self.type == 'remove':
            transaction = self.env['hr.attendance.transaction'].sudo()
            start_date = datetime.strptime(str(self.date_from), "%Y-%m-%d %H:%M:%S")
            end_date = datetime.strptime(str(self.date_to), "%Y-%m-%d %H:%M:%S")
            delta = end_date - start_date
            today = datetime.now().date()
            today = datetime.strptime(str(today), "%Y-%m-%d").date()
            for i in range(delta.days + 1):
                day = start_date + timedelta(days=i)
                if today >= day.date():
                   transaction.process_attendance_scheduler_queue(day, self.employee_id)

    def cancel(self):
        for item in self:
            have_cancel_request = self.env['leave.cancellation'].search(
                [('leave_request_id', '=', item.id), ('state', 'not in', ('draft', 'refuse'))])
            have_return_from_leave = self.env['return.from.leave'].search(
                [('leave_request_id', '=', item.id), ('state', 'not in', ('draft', 'refuse'))])
            if have_cancel_request:
                raise exceptions.Warning(
                    _("You can't set this request to draft as it's already have a cancel request\n" "Please contact with your administrator"))
            if have_return_from_leave:
                raise exceptions.Warning(_(
                    "You can't set this request to draft as it's already have a return from leave request\n" "Please contact with your administrator"))
        self._chick_leave_balance()
        self.reconcile_holiday_balance()
        self.remove_delegated_access()
        self.write({'state': 'cancel'})

    def reconcile_holiday_balance(self):
        for holiday in self:
            domain = [('check_allocation_view', '=', 'balance'),
                      ('employee_id', '=', holiday.employee_id.id),
                      ('holiday_status_id', '=', holiday.holiday_status_id.id),
                      ('type', '=', 'add')]
            balance = self.env['hr.holidays'].search(domain, order='id desc', limit=1)
            domain[0] = ('check_allocation_view', '=', 'allocation')
            allocation = self.env['hr.holidays'].search(domain, order='id desc', limit=1)
            if balance:
                if holiday.type == 'remove':
                    balance.write({
                        'remaining_leaves': balance.remaining_leaves + holiday.number_of_days_temp,
                        'leaves_taken': balance.leaves_taken - holiday.number_of_days_temp,
                    })
                    [self.env[model].search([('employee_id', '=', holiday.employee_id.id),
                                             ('leave_request_id', '=', holiday.id)]).unlink() \
                     for model in ['hr.ticket.request', 'hr.exit.return', 'hr.clearance.form']]
                else:
                    balance.write({'remaining_leaves': balance.remaining_leaves - allocation.number_of_days_temp, })


    def refuse(self):
        for item in self:
            item._remove_followers_holiday()
            have_cancel_request = self.env['leave.cancellation'].search(
                [('leave_request_id', '=', item.id), ('cancellation_type', '!=', 'cancel'), ('state', 'not in', ('draft', 'refuse'))])
            have_return_from_leave = self.env['return.from.leave'].search(
                [('leave_request_id', '=', item.id), ('state', 'not in', ('draft', 'refuse'))])
            if have_cancel_request:
                raise exceptions.Warning(
                    _("You can't set this request to draft as it's already have a cancel request\n"
                      "Please contact with your administrator"))
            if have_return_from_leave:
                raise exceptions.Warning(_(
                    "You can't set this request to draft as it's already have a return from leave request\n"
                    "Please contact with your administrator"))

            Module = self.env['ir.module.module'].sudo()
            modules_reconcile = Module.search([('state', '=', 'installed'), ('name', '=', 'exp_payroll_loans')])
            if modules_reconcile:
                have_reconcile_leaves = self.env['reconcile.leaves'].search(
                    [('yearly_vacation', '=', item.id), ('state', 'not in', ('draft', 'refuse'))])

                if have_reconcile_leaves:
                    raise ValidationError(_("You can't set this request to draft"
                                            " as it's already have Reconcile Holiday"))

            if item.state == 'validate1':
                item.reconcile_holiday_balance()
                item.remove_delegated_access()
                item.call_cron_function()
                self.check_allocation_balance_annual('addition')
                #Need Review
                self.write({'request_done': False})

            item.write({'state': 'refuse'})

    def direct_manager_refused(self):
        for rec in self:
            manager = rec.sudo().employee_id.parent_id
            hr_manager = rec.sudo().employee_id.company_id.hr_manager_id
            if manager:
                if manager.user_id.id == rec.env.uid or hr_manager.user_id.id == rec.env.uid:
                   rec.refuse()
                else:
                    raise exceptions.Warning(_("Sorry, The Refuse For The Direct Manager '%s' Only OR HR Manager!") % (manager.name))
            else:
                 rec.refuse()

    @api.onchange('holiday_status_id')
    def _get_holiday_related_date(self):
        for item in self:
            if item.employee_id.first_hiring_date:
                leaves_ids = self.env['hr.holidays'].search([('employee_id', '=', item.employee_id.id),
                                                             ('state', '=', 'validate1'),
                                                             ('type', '=', 'remove'),
                                                             ('holiday_status_id.used_once', '=', True)])
                for leave_id in leaves_ids:
                    if item.holiday_status_id == leave_id.holiday_status_id:
                        raise exceptions.Warning(_('Sorry you used this type of leave before and it used for once'))
                if item.holiday_status_id.exit_return_permission and item.employee_id.check_nationality == False:
                    item.issuing_exit_return = 'yes'
                    item.check_related = True
                else:
                    item.issuing_exit_return = 'no'
                    item.check_related = False
                if item.holiday_status_id.issuing_ticket and item.employee_id.check_nationality == False:
                    item.issuing_ticket = 'yes'
                    item.check_related = True
                else:
                    item.issuing_ticket = 'no'
                    item.check_related = False
                hiring_valu = datetime.strptime(str(self.employee_id.first_hiring_date), "%Y-%m-%d")
                current_date = (datetime.utcnow() + timedelta(hours=3)).date()
                different_years = relativedelta.relativedelta(current_date, hiring_valu).years
                if not self.holiday_status_id:
                    self.check_unlimit = False
                elif self.holiday_status_id.advance_request_years <= different_years:
                    self.check_unlimit = True
                else:
                    self.check_unlimit = False
                if item.holiday_status_id.issuing_clearance_form:
                    item.issuing_clearance_form = 'yes'
                else:
                    item.issuing_clearance_form = 'no'
                if item.holiday_status_id.issuing_deliver_custody:
                    item.issuing_deliver_custdy = 'yes'
                else:
                    item.issuing_deliver_custdy = 'no'
                if item.holiday_status_id.include_weekend and item.date_to: self.include_weekend()

    def _check_state_access_right(self, vals):
        """
            override the function to allow division manager to confirm employee's holiday.
        """

        if vals.get('state') and vals['state'] not in ['draft', 'confirm', 'cancel'] \
                and not (self.env['res.users'].has_group('hr_holidays_community.group_hr_holidays_user') or
                         self.env['res.users'].has_group('hr_base.group_division_manager')):
            return False
        return True

    def get_user_id(self):
        employee_id = self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)
        if employee_id:
            return employee_id.id
        else:
            return False

    @api.model
    def _get_employee_domain(self):
        if self.env.user.id != SUPERUSER_ID:
            employee_id = self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1).ids
            if employee_id:
                return [('id', 'in', employee_id)]
            else:
                return [('id', 'in', [])]
        else:
            employee_id = self.env['hr.employee']
            if employee_id:
                return employee_id.id
            else:
                return False

    @api.onchange('employee_id')
    def _onchange_employee(self):
        self.department_id = self.employee_id.department_id
        self.emp_id = self.employee_id.id

    def unlink(self):
        for i in self:
            if i.state != 'draft':
                raise exceptions.Warning(_('You can not delete record in state not in draft'))

            if i.check_allocation_view == 'balance' and i.leaves_taken > 0:
                raise exceptions.Warning(_('You can not delete Balance records and there is leave taken'))
        return super(HRHolidays, self).unlink()

    def _get_number_of_days(self, date_from, date_to, employee_id, official_event=True, working_days=False):

        """ Returns a float equals to the timedelta between two dates given as string."""
        from_dt = fields.Datetime.from_string(date_from)
        to_dt = fields.Datetime.from_string(date_to)
        if not employee_id: return 0.0
        employee = self.env['hr.employee'].browse(employee_id)
        # if not employee.is_calender:
        #     return employee.get_work_days_count(from_dt, fields.Datetime.from_string(date_to) + timedelta(hours=23))
        time_delta = to_dt - from_dt
        time_delta = math.ceil(time_delta.days + 1 + float(time_delta.seconds) / 86400)
        if not official_event or working_days:
            hlist = []
            for i in range((to_dt - from_dt).days + 1): hlist.append(from_dt.date() + timedelta(days=i))
        if official_event is False:
            # dont count official holidays in the holiday
            dlist = []
            for event in self.env['hr.holiday.officials'].search([('active', '=', True), ('state', '=', 'confirm'),
                                                                  ('date_from', '<=', date_to),
                                                                  ('date_to', '>=', date_from)]):
                if event.religion and employee_id and employee.religion != event.religion: continue
                edate_from = datetime.strptime(str(event.date_from), '%Y-%m-%d').date()
                dlt = datetime.strptime(str(event.date_to), '%Y-%m-%d').date() - edate_from
                for i in range(dlt.days + 1): dlist.append(edate_from + timedelta(days=i))
            time_delta = len(list(set(hlist) - set(dlist)))
            self.official_holiday_days = len([rec for rec in dlist if rec >= from_dt.date() and rec <= to_dt.date()])
        if working_days:
            wkends = employee.resource_calendar_id.full_day_off or employee.resource_calendar_id.shift_day_off
            wknd_days = [d.name.lower() for d in wkends]
            rlist = official_event is False and dlist and list(set(hlist) - set(dlist)) or hlist
            for dt in rlist:
                if dt.strftime('%A').lower() in wknd_days: time_delta -= 1
        return time_delta

    def set_date(self):
        for item in self:
            if item.date_from and item.date_to:
                current_date = (datetime.utcnow() + timedelta(hours=3))
                date_from_value = datetime.strptime(str(item.date_from), "%Y-%m-%d %H:%M:%S")
                date_to_value = datetime.strptime(str(item.date_to), "%Y-%m-%d %H:%M:%S")

                user = self.env.user

                # Check if user is **NOT** in the HR group
                # self.env.user.has_group(

                if date_to_value < date_from_value:
                    raise exceptions.Warning(_('Sorry Date TO must be bigger than Date From'))

                if not self.env.user.has_group("hr.group_hr_user"):
                    if (date_from_value - current_date).days + 1 < item.holiday_status_id.request_before:
                        raise exceptions.Warning(_('Sorry your request must be before  %s Days of your leave') \
                                                 % item.holiday_status_id.request_before)

                # if date_to_value < date_from_value:
                #     raise exceptions.Warning(_('Sorry Date TO must be bigger than Date From'))
                # if (date_from_value - current_date).days + 1 < item.holiday_status_id.request_before:
                #     raise exceptions.Warning(_('Sorry your request must be before  %s Days of your leave') \
                #                              % item.holiday_status_id.request_before)


                self.number_of_days_temp = self._get_number_of_days(item.date_from, item.date_to, self.employee_id.id,
                                                                    self.holiday_status_id.official_holidays,
                                                                    self.holiday_status_id.working_days)
                if item.number_of_days_temp < item.holiday_status_id.minimum_duration:
                    raise exceptions.Warning(_('Sorry duration must be bigger than or equal to %s Days') \
                                             % item.holiday_status_id.minimum_duration)

    @api.onchange('date_from')
    def _onchange_date_from(self):
        if self.date_from:
            self.date_from = fields.Datetime.from_string(self.date_from).replace(hour=0, minute=0, second=0,
                                                                                 microsecond=0)
        if self.holiday_status_id.include_weekend:
            self.include_weekend()
        self.date_on = True
        self.set_date()

    @api.onchange('date_from')
    def _onchange_date_from_2(self):
        if self.date_to:
           self.date_to = False 
           self.number_of_days_temp = False

    @api.onchange('date_to')
    def _onchange_date_to(self):
        """ Update the number_of_days. """
        if self.date_to:
            self.date_to = fields.Datetime.from_string(self.date_to).replace(hour=0, minute=0, second=0, microsecond=0)
        self.date_on = True
        self.set_date()

    @api.onchange('number_of_days_temp')
    def _get_end_date(self, context=None):
        if self.date_on:
            self.date_on = False
            return
        for item in self:
            if item.number_of_days_temp:
                if item.date_from:
                    self.date_to = (datetime.strptime(str(item.date_from), "%Y-%m-%d %H:%M:%S") +
                                    dt.timedelta(days=item.number_of_days_temp - 1))
                    self.set_date()
                    if item.number_of_days_temp < item.holiday_status_id.minimum_duration:
                        raise exceptions.Warning(_(
                            'Sorry duration must be bigger than or equal to %s Days') % item.holiday_status_id.minimum_duration)
    
    @api.constrains('date_from')
    def _check_include_weekend(self):
        if self.holiday_status_id.include_weekend:
            prev_holiday = self.env['hr.holidays'].search([('employee_id', '=', self.employee_id.id),
                                        ('holiday_status_id', '=', self.holiday_status_id.id),
                                        ('date_to', '<', self.date_from),
                                        ('type', '=', 'remove'),
                                        ('state', '!=', 'refuse')], limit=1, order="date_to desc")
            if not prev_holiday: return
            if not self.date_from : return
            date_from, last_dt_to = fields.Date.from_string(self.date_from), fields.Date.from_string(prev_holiday.date_to)
            days_btwn = (date_from - last_dt_to).days - 1
            if days_btwn < 1: return
            count, dates_btwn, wknd_days = 0, [], [d.name.lower() for d in
                                                self.employee_id.resource_calendar_id.full_day_off]
            for r in range(days_btwn): dates_btwn.append(date_from + relativedelta.relativedelta(days=-(r + 1)))
            if days_btwn > len(wknd_days) or dates_btwn[0].strftime('%A').lower() not in wknd_days: return
            for dt in dates_btwn:
                if dt.strftime('%A').lower() in wknd_days: count += 1
            if count == days_btwn: 
                raise exceptions.Warning(_('Sorry, it is not possible to request a leave at the beginning of the week, as there is a leave before it that ends at the end of the week, and the leave includes the holiday.'))

    def include_weekend(self):
        prev_holiday = self.env['hr.holidays'].search([('employee_id', '=', self.employee_id.id),
                                    ('holiday_status_id', '=', self.holiday_status_id.id),
                                    ('type', '=', 'remove'),
                                    ('state', '!=', 'refuse')], limit=1, order="date_to desc")
        if not prev_holiday: return
        if not self.date_from : return
        date_from, last_dt_to = fields.Date.from_string(self.date_from), fields.Date.from_string(prev_holiday.date_to)
        days_btwn = (date_from - last_dt_to).days - 1
        if days_btwn < 1: return
        count, dates_btwn, wknd_days = 0, [], [d.name.lower() for d in
                                               self.employee_id.resource_calendar_id.full_day_off]
        for r in range(days_btwn): dates_btwn.append(date_from + relativedelta.relativedelta(days=-(r + 1)))
        if days_btwn > len(wknd_days) or dates_btwn[0].strftime('%A').lower() not in wknd_days: return
        for dt in dates_btwn:
            if dt.strftime('%A').lower() in wknd_days: count += 1
        if count == days_btwn: self.date_from = date_from + relativedelta.relativedelta(days=-count)

    def delegate_access(self):
        for rec in self:
            if not rec.employee_id.user_id: raise exceptions.Warning(
                _('Kindly set a user for employee %s') % (rec.employee_id.name))
            if not rec.replace_by.user_id: raise exceptions.Warning(
                _('Kindly set a user or employee for replace by %s') % (rec.replace_by.name))
            group_ids = list(
                set(rec.employee_id.user_id.groups_id.ids) - set(rec.sudo().replace_by.user_id.groups_id.ids))
            rec.replace_by.user_id.sudo().write({'groups_id': [(4, g) for g in group_ids]})
            rec.sudo().write({'delegated_group_ids': [(6, 0, group_ids)], })
            allowed_comp = set(rec.employee_id.user_id.company_ids.ids) - set(
                rec.sudo().replace_by.user_id.company_ids.ids)
            # if allowed_comp:
            rec.replace_by.user_id.sudo().write({'company_ids': [(4, c) for c in allowed_comp]})
            rec.delegated_company_ids = [(6, 0, list(allowed_comp))]
            dept_ids = rec.employee_id.department_id.search(
                [('manager_id', '=', rec.employee_id.id), ('active', '=', True)])
            for d in dept_ids: d.sudo().write({'manager_id': rec.replace_by.id, }, )
            rec.delegated_department_ids = [(6, 0, dept_ids.ids)]

    def remove_delegated_access(self):
        for rec in self:
            groups, companies = rec.delegated_group_ids.ids, rec.delegated_company_ids.ids
            departments, manager, holiday = rec.delegated_department_ids.ids, rec.employee_id.id, rec
            while (holiday):
                rec.remove_access(holiday, groups, companies, departments, manager)
                holiday = holiday.search([('employee_id', '=', holiday.replace_by.id), ('type', '=', 'remove'),
                                          ('date_from', '<=', fields.Date.today()),
                                          ('date_to', '>=', fields.Date.today()),
                                          ('state', '=', 'validate1')])

    def remove_access(self, holiday, groups, companies, departments, manager):
        if set(holiday.delegated_group_ids.ids) & set(groups):
            holiday.replace_by.user_id.sudo().write({'groups_id': [(3, g) for g in groups]})
            holiday.delegated_group_ids = [(3, g) for g in groups]
        if set(holiday.delegated_department_ids.ids) & set(departments):
            for d in holiday.department_id.search([('id', 'in', departments)]): d.sudo().write(
                {'manager_id': manager, }, )
            holiday.delegated_department_ids = [(3, d) for d in departments]
        if set(holiday.delegated_company_ids.ids) & set(companies):
            holiday.replace_by.user_id.sudo().write({'company_ids': [(3, c) for c in companies]})
            holiday.delegated_company_ids = [(3, c) for c in companies]

    def _process_delegation_access(self):
        """cron for Handling Delegation Access Process"""
        holiday = self.env['hr.holidays']
        start_day_holiday = holiday.search([('delegate_acc', '=', True),
                                            ('date_from', '=', fields.Date.today()),
                                            ('state', '=', 'validate1')])
        end_day_holiday = holiday.search([('delegate_acc', '=', True),
                                          ('date_to', '=', fields.Date.today()),
                                          ('state', '=', 'validate1')])

        if start_day_holiday:
            start_day_holiday.delegate_access()
        if end_day_holiday:
            end_day_holiday.remove_delegated_access()


class HRINVERSHolidays(models.Model):
    _name = 'hr.inverse.holidays'

    holiday_id = fields.Many2one(comodel_name='hr.holidays')
    cron_run_date = fields.Date()
    balance_leaves = fields.Float(string='Balance')
    no_balance_leaves = fields.Float(string='No Balance')


class holidaysAttach(models.Model):
    _inherit = 'ir.attachment'

    att_holiday_ids = fields.Many2one(comodel_name='hr.holidays')

    
    @api.onchange('att_holiday_ids')
    def _onchange_att_holiday_ids(self):
        if self.att_holiday_ids:
            self.res_model = self.att_holiday_ids._name
            self.res_id = self.att_holiday_ids.id

    @api.model
    def check(self, mode, values=None):
        """Restricts the access to an ir.attachment, according to referred model
        In the 'document' module, it is overriden to relax this hard rule, since
        more complex ones apply there.
        """
        # collect the records to check (by model)
        model_ids = defaultdict(set)            # {model_name: set(ids)}
        require_employee = False
        if self:
            self._cr.execute('SELECT res_model, res_id, create_uid, public FROM ir_attachment WHERE id IN %s', [tuple(self.ids)])
            for res_model, res_id, create_uid, public in self._cr.fetchall():
                if public and mode == 'read':
                    continue
                if not (res_model and res_id):
                    if create_uid != self._uid:
                        require_employee = True
                    continue
                model_ids[res_model].add(res_id)
        if values and values.get('res_model') and values.get('res_id'):
            model_ids[values['res_model']].add(values['res_id'])

        # check access rights on the records
        for res_model, res_ids in model_ids.items():
            # ignore attachments that are not attached to a resource anymore
            # when checking access rights (resource was deleted but attachment
            # was not)
            if res_model not in self.env:
                require_employee = True
                continue
            elif res_model == 'res.users' and len(res_ids) == 1 and self._uid == list(res_ids)[0]:
                # by default a user cannot write on itself, despite the list of writeable fields
                # e.g. in the case of a user inserting an image into his image signature
                # we need to bypass this check which would needlessly throw us away
                continue
            records = self.env[res_model].browse(res_ids).exists()
            if len(records) < len(res_ids):
                require_employee = True
            # For related models, check if we can write to the model, as unlinking
            # and creating attachments can be seen as an update to the model
            records.check_access_rights('write' if mode in ('create', 'unlink') else mode)
            records.check_access_rule(mode)

        if require_employee:
            if not (self.env.user._is_admin() or self.env.user.has_group('base.group_user') or self._context.get('bypass_check_public_holidays', False)):
                raise AccessError(_("Sorry, you are not allowed to access this document."))
    
    # @api.model
    # def create(self, values):
    #     print("**********************************************create")
    #     result = super(holidaysAttach, self).create(values)
    #     print("**********************************************result",result)
    #     if result.att_holiday_ids:
    #         result.update({
    #             'res_model': result.att_holiday_ids._name,
    #             'res_id': result.att_holiday_ids.id
    #         })
    #     return result




