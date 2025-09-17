# -*- coding: utf-8 -*-

from datetime import datetime
from datetime import timedelta
import calendar
from dateutil.relativedelta import relativedelta
from odoo.tools.translate import _
from odoo import models, fields, api, exceptions


class ReturnFromLeave(models.Model):
    _name = 'return.from.leave'
    _rec_name = 'employee_id'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    state = fields.Selection(selection=[("draft", _("Draft")),
                                        ("submit", _("Submit")),
                                        ("review", _("Direct Manager")),
                                        ("confirm", _("HR Manager")),
                                        ("approve", _("Approved")),
                                        ("refuse", _("Refused"))], default='draft')
    from_hr_department = fields.Boolean()
    # employee_id = fields.Many2one(comodel_name='hr.employee')
    real_start_date_working = fields.Datetime()
    diff_days = fields.Float(compute="onchange_dates", store=False)
    cause = fields.Char()
    decision = fields.Selection(selection=[("deduct", _("Deduct from Leave Balance")),
                                           ("other", _("Deduct form Annual Leave")),
                                           ("law", _("Create Unpaid Leave"))])
    leave_request_id = fields.Many2one(comodel_name='hr.holidays')
    leave_date_from = fields.Datetime(related='leave_request_id.date_from', store=True, readonly=True)
    leave_date_to = fields.Datetime(compute="_compute_dates_of_leave", store=True, readonly=True)
    attachment_ids = fields.One2many('ir.attachment', 'return_leave_id')
    official_days = fields.Float(default=0.0)
    settling_leave_id = fields.Many2one(comodel_name='hr.holidays', string='Decision settling Leave',
                                        domain=[('id', 'in', [])], readonly=True)
    alternative_emp_id = fields.Many2one('hr.employee', string='Alternative Employee')
    employee_id = fields.Many2one('hr.employee', 'Employee', default=lambda item: item.get_user_id())
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

    def unlink(self):
        for item in self:
            if item.state != 'draft':
                raise exceptions.Warning(_('You can not delete record in state not in draft'))
        return super(ReturnFromLeave, self).unlink()

    @api.onchange('employee_id')
    def _get_leaves_related_date(self):
        for item in self:
            leaves_ids = self.env['hr.holidays'].search([('employee_id', '=', item.employee_id.id),
                                                         ('state', '=', 'validate1'),
                                                         ('type', '=', 'remove'),
                                                         ('return_from_leave', '=', False)
                                                         ]).ids
            if leaves_ids:
                return {'domain': {'leave_request_id': [('id', 'in', leaves_ids)]}}
            else:
                return {'domain': {'leave_request_id': [('id', 'in', [])]}}

    @api.onchange('leave_request_id')
    def _onchange_leave(self):
        self.real_start_date_working = False
        self.diff_days = 0.0
        self.official_days = 0.0

    @api.onchange('leave_request_id', 'decision')
    def _chick_leave_type(self):
        for rec in self:
            if rec.leave_request_id.holiday_status_id.leave_type == 'annual' and rec.decision == 'other':
                raise exceptions.ValidationError(_("Sorry Cannot be Create an Annual Leave from the same annual Leave"))

    @api.depends('leave_request_id')
    def _compute_dates_of_leave(self):
        for request in self:
            request.leave_date_to = request.leave_request_id.date_to

    @api.onchange('real_start_date_working', 'leave_date_to')
    def onchange_dates(self):
        def next_weekday(d, weekday):
            days_ahead = weekday - d.weekday()
            if days_ahead < 0: days_ahead += 7
            return d + timedelta(days_ahead)

        for request in self:
            if request.leave_date_to and request.real_start_date_working:
                date_to = datetime.strptime(str(request.leave_date_to), "%Y-%m-%d %H:%M:%S").date()
                planed_return_dt = (date_to + timedelta(days=1))
                return_date = datetime.strptime(str(request.real_start_date_working), "%Y-%m-%d %H:%M:%S").date()
                if return_date >= planed_return_dt:
                    event_dates, wkns_dates = [], []
                    cln_days = dict(zip(calendar.day_name, range(7)))
                    days_off = [d.name.title() for d in request.employee_id.resource_calendar_id and
                                (request.employee_id.resource_calendar_id.full_day_off or
                                 request.employee_id.resource_calendar_id.shift_day_off) or
                                request.employee_id.company_id.resource_calendar_id and
                                (request.employee_id.company_id.resource_calendar_id.full_day_off or
                                 request.employee_id.company_id.resource_calendar_id.shift_day_off)]
                    exceeded_dates = [planed_return_dt + timedelta(days=i) for i in
                                      range((return_date - date_to).days - 1)]

                    if not request.leave_request_id.holiday_status_id.official_holidays:
                        for event in self.env['hr.holiday.officials'].search(
                                [('active', '=', True), ('state', '=', 'confirm'),
                                 ('date_from', '<', return_date),
                                 ('date_to', '>=', planed_return_dt)]):
                            if event.religion and request.employee_id and \
                                    request.employee_id.religion != event.religion:
                                continue
                            edate_from = datetime.strptime(str(event.date_from), '%Y-%m-%d').date()
                            dlt = datetime.strptime(str(event.date_to), '%Y-%m-%d').date() - edate_from
                            for i in range(dlt.days + 1):
                                check_date = edate_from + timedelta(days=i)
                                # event dates that fall within exceed date
                                if date_to <= check_date < return_date and check_date not in event_dates:
                                    event_dates.append(check_date)
                        request.official_days = len(list(set(event_dates)))

                    # if request.leave_request_id.holiday_status_id.working_days:
                    for exd in exceeded_dates:
                        if exd.strftime('%A') in days_off and exd not in event_dates:wkns_dates.append(exd)
                    if set(exceeded_dates).issubset(set(wkns_dates + event_dates)):
                        request.diff_days = 0.0
                    elif request.leave_request_id.holiday_status_id.working_days:
                        request.diff_days = len(list(set([xd for xd in exceeded_dates
                                                          if xd not in event_dates and xd not in wkns_dates])))
                    else:
                        request.diff_days = len(list(set([xd for xd in exceeded_dates if xd not in event_dates and xd not in wkns_dates])))
                else:
                    raise exceptions.ValidationError(_("Sorry this leave ends by %s.\n"
                                                       "If you plan for an early return kindly apply for leave "
                                                       "cancellation.") % request.leave_request_id.date_to)
            else:
                request.official_days = False
                request.diff_days = 0

    def get_user_id(self):
        employee_id = self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)
        if employee_id:
            return employee_id.id
        else:
            return False


    def draft(self):
        for leave in self:
            if self.settling_leave_id:
                if self.settling_leave_id.state in ('confirm', 'draft', 'refuse', 'validate1'):
                    self.settling_leave_id.refuse()
                    self.settling_leave_id.draft_state()
                    self.settling_leave_id.unlink()
                else:
                    raise exceptions.ValidationError(_("Sorry The link leave cannot be deleted %s After approved")
                                                     % self.settling_leave_id.holiday_status_id.name)
            self.state = 'draft'
            self.leave_request_id.return_from_leave = False

    def act_decision(self):
        for rec in self:
            if rec.diff_days < 1: continue
            request_id = rec.leave_request_id
            if rec.decision == 'law':  # create unpaid leave
                if not request_id.holiday_status_id.unpaid_holiday_id:
                    raise exceptions.ValidationError(_("Sorry no unpaid leave is defined for %s leave kindly set one")
                                                     % request_id.holiday_status_id.name)
                status_id = request_id.holiday_status_id.unpaid_holiday_id.id
            elif rec.decision == 'deduct':  # Deduct from leave balance
                status_id = request_id.holiday_status_id.id
            elif rec.decision == 'other':  # create annual leave
                if not request_id.holiday_status_id.annual_holiday_id:
                    raise exceptions.ValidationError(_("Sorry no annual leave is defined for %s leave kindly set one")
                                                     % request_id.holiday_status_id.name)
                status_id = request_id.holiday_status_id.annual_holiday_id.id

            balance = rec.leave_request_id.search([('employee_id', '=', rec.employee_id.id),
                                                   ('type', '=', 'add'),
                                                   ('holiday_status_id', '=', status_id),
                                                   ('check_allocation_view', '=', 'balance')
                                                   ], order='id desc', limit=1).remaining_leaves or 0.0
            if balance < rec.diff_days:
                raise exceptions.ValidationError(
                    _("Sorry your %s leave balance it is not enough to deduct from it, The balance is %s.")
                    % (request_id.holiday_status_id.name, round(balance, 2)))

            # for the 3 decitions create new leave with days the extra days (late return)
            r = request_id.create({'employee_id': rec.employee_id.id,
                                   'type': 'remove',
                                   'state': 'draft',
                                   'holiday_status_id': status_id,
                                   'replace_by': rec.alternative_emp_id and rec.alternative_emp_id.id or
                                                 rec.leave_request_id.replace_by.id,
                                   'date_from': (fields.Datetime.from_string(request_id.date_to) +
                                                 relativedelta(days=+1)).strftime('%Y-%m-%d 00:00:00'),
                                   'date_to': (fields.Datetime.from_string(rec.real_start_date_working) +
                                               relativedelta(days=-1)).strftime('%Y-%m-%d 00:00:00'), })
            r._onchange_date_from()
            msg = _(
                "This leave is an extension for the leave: <a href=# data-oe-model=hr.holidays data-oe-id=%d>%s</a>") \
                  % (rec.leave_request_id.id, rec.leave_request_id.display_name)
            r.message_post(body=msg)
            r.confirm()
            rec.settling_leave_id = r.id

    def submit(self):
        #self._chick_leave_type()
        #self.act_decision()
        self.state = 'submit'

    def review(self):
        self._chick_leave_type()
        self.act_decision()
        self.state = 'review'

    def confirm(self):
        self.state = 'confirm'

    def approve(self):
        if self.settling_leave_id:
            self.settling_leave_id.write({'return_from_leave': True, 'notes': _('Extend')})
            if self.decision == 'deduct':
                self.settling_leave_id.financial_manager()
            elif self.leave_request_id.state != 'validate1':
                raise exceptions.ValidationError(
                    _("Sorry %s leave is not approved yet. kindly approve it first") % (
                        self.leave_request_id.display_name))
        self.leave_request_id.remove_delegated_access()
        self.leave_request_id.return_from_leave = True
        self.state = 'approve'

    def refuse(self):
        for leave in self:
            if leave.settling_leave_id:
                if leave.settling_leave_id.state in ('confirm', 'draft', 'refuse'):
                    leave.settling_leave_id.refuse()
                    leave.settling_leave_id.draft_state()
                    leave.settling_leave_id.unlink()
                else:
                    raise exceptions.ValidationError(_("Sorry The link leave cannot be deleted %s After approved")
                                                     % leave.settling_leave_id.holiday_status_id.name)
        self.state = 'refuse'


class Attachment(models.Model):
    _inherit = 'ir.attachment'

    return_leave_id = fields.Many2one(comodel_name='return.from.leave')
