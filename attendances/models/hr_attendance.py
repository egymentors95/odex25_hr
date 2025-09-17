# -*- coding: utf-8 -*-

from datetime import datetime, timedelta, date

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT as DATETIME_FORMAT
from ast import literal_eval


class HrEmployeeBase(models.AbstractModel):
    _inherit = 'hr.employee.base'

    #################
    hr_presence_state = fields.Selection([
        ('present', 'Present'), #('absent', 'Absent'),
        ('to_define', 'Not Present')],string='Attendance State', compute='_compute_presence_state', default='to_define',store=True)

    hr_icon_display = fields.Selection([
        ('presence_present', 'Present'),
        ('presence_absent_active', 'Present but not active'),
        ('presence_absent', 'Absent'),
        ('presence_to_define', 'Not Present'),
        ('presence_undetermined', 'Undetermined')], compute='_compute_presence_icon')

    @api.depends('resource_calendar_id', 'hr_presence_state')
    def _compute_presence_icon(self):#copy form base hr overritten
        for employee in self:
            if employee.hr_presence_state == 'present':
               icon = 'presence_present'
            elif employee.hr_presence_state == 'absent':
                icon = 'presence_absent'
            else:
                if employee.user_id:
                    icon = 'presence_to_define'
                else:
                    icon = 'presence_undetermined'
            employee.hr_icon_display = icon

    def _compute_presence_state(self):#copy form base hr overritten
        # Check on login
        check_login = literal_eval(self.env['ir.config_parameter'].sudo().get_param('hr.hr_presence_control_login', 'False'))
        employee_to_check_working = self.filtered(lambda e: e.user_id.im_status == 'offline')
        #working_now_list = employee_to_check_working._get_employee_working_now()
        t_date = date.today()
        for employee in self:
            attendance = self.env['attendance.attendance'].sudo().search([
                   ('employee_id', '=', employee.id),('action_date', '=', t_date)], limit=1)
            state = 'to_define'
            if check_login:
                if attendance:
                    state = 'present'
                else:
                   state = 'to_define'
                #if employee.user_id.im_status == 'offline' and not attendance:
                   # state = 'absent'
            employee.hr_presence_state = state

    ###############


class HrAttendances(models.Model):
    _inherit = 'resource.calendar'

    def _get_default_attendance_ids(self):
        return [
            (0, 0, {'name': _('Monday Morning'), 'dayofweek': '0', 'hour_from': 8, 'hour_to': 12}),
            (0, 0, {'name': _('Monday Evening'), 'dayofweek': '0', 'hour_from': 13, 'hour_to': 17}),
            (0, 0, {'name': _('Tuesday Morning'), 'dayofweek': '1', 'hour_from': 8, 'hour_to': 12}),
            (0, 0, {'name': _('Tuesday Evening'), 'dayofweek': '1', 'hour_from': 13, 'hour_to': 17}),
            (0, 0, {'name': _('Wednesday Morning'), 'dayofweek': '2', 'hour_from': 8, 'hour_to': 12}),
            (0, 0, {'name': _('Wednesday Evening'), 'dayofweek': '2', 'hour_from': 13, 'hour_to': 17}),
            (0, 0, {'name': _('Thursday Morning'), 'dayofweek': '3', 'hour_from': 8, 'hour_to': 12}),
            (0, 0, {'name': _('Thursday Evening'), 'dayofweek': '3', 'hour_from': 13, 'hour_to': 17}),
            (0, 0, {'name': _('Friday Morning'), 'dayofweek': '4', 'hour_from': 8, 'hour_to': 12}),
            (0, 0, {'name': _('Friday Evening'), 'dayofweek': '4', 'hour_from': 13, 'hour_to': 17}),
            (0, 0, {'name': _('Saturday Morning'), 'dayofweek': '5', 'hour_from': 8, 'hour_to': 12}),
            (0, 0, {'name': _('Saturday Evening'), 'dayofweek': '5', 'hour_from': 13, 'hour_to': 17}),
            (0, 0, {'name': _('Sunday Morning'), 'dayofweek': '6', 'hour_from': 8, 'hour_to': 12}),
            (0, 0, {'name': _('Sunday Evening'), 'dayofweek': '6', 'hour_from': 13, 'hour_to': 17})
        ]
    name = fields.Char(string='Description')
    is_full_day = fields.Boolean(string='Is Full Day ?', default=True)
    full_min_sign_in = fields.Float(string='Min Sign In')
    full_max_sign_in = fields.Float(string='Max Sign In')
    full_min_sign_out = fields.Float(string='Min Sign out')
    full_max_sign_out = fields.Float(string='Max Sign out')
    full_start_sign_in = fields.Float(string='Start Sign In')
    full_end_sign_in = fields.Float(string='End Sign In')
    full_start_sign_out = fields.Float(string='Start Sign Out')
    full_end_sign_out = fields.Float(string='End Sign Out')
    grace_hour_before_work = fields.Float(string="Grace Hours Before Work")
    grace_hour_after_work = fields.Float(string="Grace Hours After Work")
    working_hours = fields.Float(string='Working Hours')
    working_days = fields.Integer(string='Working Days')
    break_duration = fields.Float("Break Duration", default=0.0)
    end_sign_in = fields.Float(string='Time to calculate today as absence')
    full_day_off = fields.One2many('days.off', 'day_off_attendance')
    shift_day_off = fields.One2many('days.off', 'day_off_attendance')
    special_days = fields.One2many('attendance.special.days', 'special_days_attendance')
    special_days_partcial = fields.One2many('attendance.special.days', 'special_days_attendance')
    deduction_rule = fields.Many2one('hr.salary.rule', string='Deduction Rule')
    active = fields.Boolean(string='Active', default=True)
    employee_ids = fields.One2many('hr.employee', 'resource_calendar_id', string='Employees',
                                   domain=[('state', '=', 'open')])

    # Flexible Days
    is_flexible = fields.Boolean(string='Is Flexible?')
    number_of_flexi_days = fields.Integer(string='Flexible Days')
    total_flexible_hours = fields.Float(string='Total Hours For Flexible Days', compute='compute_flexible_hours')
    noke = fields.Boolean(string='NOC')

    # shift one
    shift_one_min_sign_in = fields.Float(string='Min Sign In')
    shift_one_max_sign_in = fields.Float(string='Max Sign In')
    shift_one_min_sign_out = fields.Float(string='Min Sign out')
    shift_one_max_sign_out = fields.Float(string='Max Sign out')
    shift_one_start_sign_in = fields.Float(string='Start Sign In')
    shift_one_end_sign_in = fields.Float(string='End Sign In')
    shift_one_start_sign_out = fields.Float(string='Start Sign Out')
    shift_one_end_sign_out = fields.Float(string='End Sign Out')
    shift_one_working_hours = fields.Float(string='Working Hours')
    shift_one_break_duration = fields.Float("Break Duration", default=0.0)

    # shift two
    shift_two_min_sign_in = fields.Float(string='Min Sign In')
    shift_two_max_sign_in = fields.Float(string='Max Sign In')
    shift_two_min_sign_out = fields.Float(string='Min Sign out')
    shift_two_max_sign_out = fields.Float(string='Max Sign out')
    shift_two_start_sign_in = fields.Float(string='Start Sign In')
    shift_two_end_sign_in = fields.Float(string='End Sign In')
    shift_two_start_sign_out = fields.Float(string='Start Sign Out')
    shift_two_end_sign_out = fields.Float(string='End Sign Out')
    shift_two_working_hours = fields.Float(string='Working Hours')
    state = fields.Selection([('draft', _('Draft')),
                              ('confirm', _('Confirmed')),
                              ('update', _('Updated'))], string='State', default="draft")
    parent_calendar_id = fields.Many2one('resource.calendar', string='Parent Calender')
    shift_two_break_duration = fields.Float("Break Duration", default=0.0)
    attendance_ids = fields.One2many(
        'resource.calendar.attendance', 'calendar_id', 'Working Time',
        copy=True, default=_get_default_attendance_ids)

    register_before = fields.Integer(string='Attendance Register Before', help="The Maximum Number of Days to Request Missing Attendance")

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        if args is None: args = []
        args.append(('state', '=', 'confirm'))
        return super(HrAttendances, self).name_search(name, args=args, operator=operator, limit=limit)

    def compute_flexible_hours(self):
        for item in self:
            item.total_flexible_hours = 0
            two_shift = item.shift_one_working_hours + item.shift_two_working_hours
            if item.is_flexible is True:
                if item.is_full_day:
                    item.total_flexible_hours = item.working_hours * item.number_of_flexi_days
                else:
                    item.total_flexible_hours = two_shift * item.number_of_flexi_days

    # Constraints for Working hours in two cases (Full or Part Time)

    @api.constrains('working_hours', 'shift_one_working_hours', 'shift_two_working_hours', 'special_days')
    def result_greed_constrains(self):
        for item in self:
            if item.is_full_day:
                hours = item.full_min_sign_out - item.full_min_sign_in
                work_hours = item.working_hours
                if work_hours != hours:
                    raise ValidationError(_('Working Hours must be equal to "%s"') % hours)
                if item.special_days:
                    for line in item.special_days:
                        if not item.is_full_day:
                            hours = line.start_sign_in - line.start_sign_out
                        else:
                            hours = line.start_sign_out - line.start_sign_in
                        if line.working_hours != hours:
                            raise ValidationError(_('Working Hours for special days must be equal to "%s"') % hours)
            else:
                shift_one = self.get_shift_working_hour(self.shift_one_min_sign_in, self.shift_one_min_sign_out)

                shift_two = self.get_shift_working_hour(self.shift_two_min_sign_in, self.shift_two_min_sign_out)
                if item.shift_one_working_hours != shift_one:
                    raise ValidationError(
                        _('Edit Shift(One)  Min  sign in and min sign out to match working hours "%s"') % shift_one)
                if item.shift_two_working_hours > shift_two:
                    raise ValidationError(
                        _('edit Shift(Two) Min  sign in and min sign out to match working hours "%s"') % shift_two)

    def calendar_special_days_change(self):
        parent_spds = self. is_full_day and \
                      self.parent_calendar_id.special_days or self.parent_calendar_id.special_days_partcial
        special_days = self. is_full_day and self.special_days or self.special_days_partcial
        amended = False
        sp_day_list = parent_spds.mapped('name')
        for spd in special_days:
            if spd.name not in sp_day_list:
                amended = True
                break
            parent_spd = parent_spds.filtered(lambda day: day.name == spd.name)
            if spd.start_sign_in != parent_spd.start_sign_in\
                    or spd.end_sign_in != parent_spd.end_sign_in\
                    or spd.start_sign_out != parent_spd.start_sign_out\
                    or spd.end_sign_out != parent_spd.end_sign_out\
                    or spd.working_hours != parent_spd.working_hours\
                    or spd.date_from and not parent_spd.date_from\
                    or not spd.date_from and parent_spd.date_from\
                    or spd.date_from and parent_spd.date_from and spd.date_from != parent_spd.date_from\
                    or spd.date_to and not parent_spd.date_to\
                    or not spd.date_to and parent_spd.date_to\
                    or spd.date_to and parent_spd.date_to and spd.date_to != parent_spd.date_to:
                amended = True
                break
        return amended

    def act_confirm(self):
        if not self.parent_calendar_id: self.state = 'confirm'
        else:
            if self.is_full_day != self.parent_calendar_id.is_full_day \
                    or self.full_min_sign_in != self.parent_calendar_id.full_min_sign_in \
                    or self.full_max_sign_in != self.parent_calendar_id.full_max_sign_in \
                    or self.full_min_sign_out != self.parent_calendar_id.full_min_sign_out \
                    or self.full_max_sign_out != self.parent_calendar_id.full_max_sign_out \
                    or self.working_hours != self.parent_calendar_id.working_hours \
                    or self.working_days != self.parent_calendar_id.working_days \
                    or self.break_duration != self.parent_calendar_id.break_duration \
                    or self.end_sign_in != self.parent_calendar_id.end_sign_in \
                    or self.is_flexible != self.parent_calendar_id.is_flexible \
                    or self.number_of_flexi_days != self.parent_calendar_id.number_of_flexi_days \
                    or self.total_flexible_hours != self.parent_calendar_id.total_flexible_hours \
                    or self.noke != self.parent_calendar_id.noke \
                    or self.shift_one_min_sign_in != self.parent_calendar_id.shift_one_min_sign_in \
                    or self.shift_one_max_sign_in != self.parent_calendar_id.shift_one_max_sign_in \
                    or self.shift_one_min_sign_out != self.parent_calendar_id.shift_one_min_sign_out \
                    or self.shift_one_max_sign_out != self.parent_calendar_id.shift_one_max_sign_out \
                    or self.shift_one_working_hours != self.parent_calendar_id.shift_one_working_hours \
                    or self.shift_two_min_sign_in != self.parent_calendar_id.shift_two_min_sign_in \
                    or self.shift_two_max_sign_in != self.parent_calendar_id.shift_two_max_sign_in \
                    or self.shift_two_min_sign_out != self.parent_calendar_id.shift_two_min_sign_out \
                    or self.shift_two_max_sign_out != self.parent_calendar_id.shift_two_max_sign_out \
                    or self.shift_two_working_hours != self.parent_calendar_id.shift_two_working_hours \
                    or (self.special_days\
                        and (len(self.special_days) != len(self.parent_calendar_id.special_days)\
                             or self.calendar_special_days_change())) \
                    or (self.special_days_partcial \
                        and (len(self.special_days_partcial) != len(self.parent_calendar_id.special_days_partcial) \
                             or self.calendar_special_days_change())) \
                    or not ((len(self.parent_calendar_id.full_day_off) == len(self.full_day_off) ==
                             len(list(set(self.full_day_off.mapped('name'))
                                      & set(self.parent_calendar_id.full_day_off.mapped('name'))))))\
                    or not ((len(self.parent_calendar_id.shift_day_off) == len(self.shift_day_off) ==
                             len(list(set(self.shift_day_off.mapped('name'))
                                      & set(self.parent_calendar_id.shift_day_off.mapped('name')))))):
                self.state = 'confirm'
                self.parent_calendar_id.employee_ids.write({'resource_calendar_id': self.id})
                self.parent_calendar_id.active = False
                for com in self.env['res.company'].search([('resource_calendar_id', '=', self.parent_calendar_id.id)]):
                    com.resource_calendar_id = self.parent_calendar_id.id
            else:
                self.parent_calendar_id.write({'attendance_ids': [(2, at.id, False) for at in self.parent_calendar_id.attendance_ids],})
                self.parent_calendar_id.write({
                    'name': self.parent_calendar_id.name != self.name and self.name or self.parent_calendar_id.name,
                    'deduction_rule': self.parent_calendar_id.deduction_rule.id != self.deduction_rule.id\
                                      and self.deduction_rule.id or self.parent_calendar_id.deduction_rule.id,
                    'active': self.parent_calendar_id.active != self.active and self.active or self.parent_calendar_id.active,
                    'attendance_ids': [(4, at.copy().id) for at in self.attendance_ids],
                    'state': 'confirm'
                })
                calendar_id = self.parent_calendar_id.id
                self.unlink()
                cxt = dict(self.env.context)
                cxt['form_view_initial_mode'] = 'readonly'
                return {
                    'type': 'ir.actions.act_window',
                    'view_type': 'form',
                    'res_model': 'resource.calendar',
                    'view_mode': 'form',
                    'res_id': calendar_id,
                    'context': cxt,
                }

    def act_update(self):
        self.ensure_one()
        new = self.copy({'parent_calendar_id': self.id,
                         'state': 'draft',
                         'full_day_off': [(4, wknd.copy().id) for wknd in self.full_day_off],
                         'special_days': [(4, spd.copy().id) for spd in self.special_days],
                         'attendance_ids': [(4, at.copy().id) for at in self.attendance_ids],
                         })
        self.write({'state': 'update',})
        cxt = dict(self.env.context)
        cxt['form_view_initial_mode'] = 'edit'
        cxt['force_detailed_view'] = True
        return {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'resource.calendar',
            'res_id': new.id,
            'context': cxt,
        }

    @api.constrains('noke', 'is_full_day', 'full_min_sign_in', 'full_max_sign_in', 'full_min_sign_out',
                    'full_max_sign_out', )
    def full_time_constrains(self):
        for rec in self:
            if rec.is_full_day and not rec.noke:
                value = rec.shift_cons_check(rec.full_min_sign_in, rec.full_max_sign_in, rec.full_min_sign_out,
                                             rec.full_max_sign_out)
                if value == 1:
                    raise ValidationError(_("Max sign in should be greater than or equal min sign in"))
                if value == 2:
                    raise ValidationError(_("min sign out should be greater than or equal min sign in"))
                if value == 3:
                    raise ValidationError(_("Max sign out should be greater than or equal min sign out"))

    @api.onchange('shift_one_min_sign_in', 'shift_one_min_sign_out', 'shift_two_min_sign_in',
                  'shift_two_min_sign_out')
    def work_hours(self):
        self.shift_one_working_hours = self.get_shift_working_hour(self.shift_one_min_sign_in,
                                                                   self.shift_one_min_sign_out)

        self.shift_two_working_hours = self.get_shift_working_hour(self.shift_two_min_sign_in,
                                                                   self.shift_two_min_sign_out)

    def get_shift_working_hour(self, min_in, min_out):
        time_start = datetime.strptime(str('{0:02.0f}:{1:02.0f}'.format(*divmod(float(min_in) * 60, 60))), "%H:%M")
        time_end = datetime.strptime(str('{0:02.0f}:{1:02.0f}'.format(*divmod(float(min_out) * 60, 60))), "%H:%M")
        diff = time_end - time_start
        result = diff.seconds / 3600
        return result

    def shift_cons_check(self, min_in, max_in, min_out, max_out):
        # 00:00 issue
        min_in = min_in + 24 if min_in < 1 else min_in
        max_in = max_in + 24 if max_in < 1 else max_in
        min_out = min_out + 24 if min_out < 1 else min_out
        max_out = max_out + 24 if max_out < 1 else max_out
        if min_in > max_in:
            return 1
        if min_in > min_out or max_in > min_out:
            return 2
        if min_out > max_out:
            return 3

    @api.constrains('noke', 'is_full_day', 'shift_one_min_sign_in', 'shift_one_max_sign_in', 'shift_one_min_sign_out',
                    'shift_one_max_sign_out', )
    def shift_one_constrains(self):
        for rec in self:
            if not rec.is_full_day and not rec.noke:
                value = self.shift_cons_check(rec.shift_one_min_sign_in, rec.shift_one_max_sign_in,
                                              rec.shift_one_min_sign_out, rec.shift_one_max_sign_out)
                if value == 1:
                    raise ValidationError(_("Max sign in should be greater than or equal min sign in in shift one"))
                if value == 2:
                    raise ValidationError(_("min sign out should be greater than or equal min sign in in shift one"))
                if value == 3:
                    raise ValidationError(_("Max sign out should be greater than or equal min sign out in shift one"))

    @api.constrains('noke', 'is_full_day', 'shift_two_min_sign_in', 'shift_two_max_sign_in',
                    'shift_two_min_sign_out',
                    'shift_two_max_sign_out')
    def shift_two_constrains(self):
        for rec in self:
            if not rec.is_full_day and not rec.noke:
                value = self.shift_cons_check(rec.shift_two_min_sign_in, rec.shift_two_max_sign_in,
                                              rec.shift_two_min_sign_out, rec.shift_two_max_sign_out)
                if value == 1:
                    raise ValidationError(_("Max sign in should be greater than or equal min sign in in shift two"))
                if value == 2:
                    raise ValidationError(_("min sign out should be greater than or equal min sign in in shift two"))
                if value == 3:
                    raise ValidationError(_("Max sign out should be greater than or equal min sign out in shift two"))


class DaysOff(models.Model):
    _name = 'days.off'

    name = fields.Selection(selection=[('saturday', 'Saturday'),
                                       ('sunday', 'Sunday'),
                                       ('monday', 'Monday'),
                                       ('tuesday', 'Tuesday'),
                                       ('wednesday', 'Wednesday'),
                                       ('thursday', 'Thursday'),
                                       ('friday', 'Friday')], string='Day Off')
    # relation fields
    day_off_attendance = fields.Many2one('resource.calendar')
    shift = fields.Selection(selection=[('both', 'Both'),('one', 'First Shift'), ('two', 'Second Shift')],default='both',string='Shift')


class SpecialDays(models.Model):
    _name = 'attendance.special.days'

    name = fields.Selection(selection=[('saturday', 'Saturday'),
                                       ('sunday', 'Sunday'),
                                       ('monday', 'Monday'),
                                       ('tuesday', 'Tuesday'),
                                       ('wednesday', 'Wednesday'),
                                       ('thursday', 'Thursday'),
                                       ('friday', 'Friday')], string='Day Off')
    start_sign_in = fields.Float(string='Start Sign In')
    end_sign_in = fields.Float(string='End Sign In')
    start_sign_out = fields.Float(string='Start Sign Out')
    end_sign_out = fields.Float(string='End Sign Out')
    working_hours = fields.Float(string='Working Hours')
    # relation fields
    special_days_attendance = fields.Many2one('resource.calendar')
    date_from = fields.Date(string='Date From')
    date_to = fields.Date(string='Date To')
    shift = fields.Selection(selection=[('one', 'First Shift'), ('two', 'Second Shift')], string='Shift')


class ActionReason(models.Model):
    _name = 'attendance.action.reason'

    name = fields.Char(string='Reason')
    type = fields.Selection(selection=[('sign_in', ' Sign In'),
                                       ('sign_out', 'Sign Out')], string='Action Type')


class Attendance(models.Model):
    _name = 'attendance.attendance'
    _rec_name = 'employee_id'
    _order = 'action_date DESC'

    employee_id = fields.Many2one('hr.employee', string="Employee", domain="[('state', '=', 'open')]", required=True,
                                  ondelete='cascade', index=True)
    department_id = fields.Many2one(related="employee_id.department_id", readonly=True, store=True)
    action = fields.Selection(selection=[('sign_in', ' Sign In'),
                                         ('sign_out', 'Sign Out'),
                                         ('action', 'Action')], string='Action', default='sign_in')
    taken = fields.Boolean(string='Taken')
    action_type = fields.Selection(selection=[('manual', 'Manual'),
                                              ('finger_print', 'Finger Print')], string='Action Type')
    action_date = fields.Date(string='Action Date', compute='compute_date', store=True)
    #name = fields.Datetime(string='Date', default=datetime.utcnow())
    name = fields.Datetime(string='Date', default=lambda self: fields.datetime.now())
    action_reason = fields.Many2one('attendance.action.reason', string='Action Reason')

    employee_number = fields.Char(related='employee_id.emp_no', string='Employee Number',store=True)
    company_id = fields.Many2one(related='employee_id.company_id', string='Company')
    is_branch = fields.Many2one(related='department_id.branch_name', store=True, readonly=True)

    is_today = fields.Boolean(string='Is Today', compute='_compute_is_today', store=True)

    @api.depends('action_date')
    def _compute_is_today(self):
        today = datetime.now().date()
        for record in self:
            if record.action_date == today:
               record.is_today = True
            else:
               record.is_today = False

    @api.depends('name')
    def compute_date(self):
        for item in self:
            item.action_date = datetime.now().date()
            datee = datetime.strptime(str(item.name.strftime(DATETIME_FORMAT)), "%Y-%m-%d %H:%M:%S") + timedelta(
                hours=3)
            if datee:
                dt = datee
                item.action_date = dt.strftime('%Y-%m-%d')
            else:
                item.action_date = False


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    def attendance_action_change(self):
        res = super(HrEmployee, self).attendance_action_change()
        action_date = datetime.utcnow()
        if self.state == 'open':
            if self.attendance_state != 'checked_in':
                vals = {
                    'employee_id': self.id,
                    'name': action_date,
                    'action': 'sign_out',
                    'action_date': action_date,
                }
            else:
                vals = {
                    'employee_id': self.id,
                    'name': action_date,
                    'action': 'sign_in',
                    'action_date': action_date,
                }
            self.env['attendance.attendance'].create(vals)
        return res

    def _compute_attendance_state(self):
        for rec in self:
            last = rec.env['attendance.attendance'].search([('employee_id', '=', rec.id), ], order='name desc', limit=1)
            if last.action == 'sign_in':
                rec.attendance_state = 'checked_in'
            else:
                rec.attendance_state = 'checked_out'
