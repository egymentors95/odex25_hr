# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
from odoo import models, fields, api, _
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT as DATETIME_FORMAT, float_round
from odoo.exceptions import UserError


class HrAttendanceTransactions(models.Model):
    _name = 'hr.attendance.transaction'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'employee_id'
    _order = 'date DESC'

    date = fields.Date(string='Day')
    lateness = fields.Float(widget='float_time')
    early_exit = fields.Float(widget='float_time')
    is_absent = fields.Boolean(string='Absent', store=True)
    sign_in = fields.Float()
    sign_out = fields.Float()
    approve_exit_out = fields.Boolean(string='Approve Early Exit',)
    approve_lateness = fields.Boolean(string='Approve Lateness',)
    employee_id = fields.Many2one('hr.employee', 'Employee Name', default=lambda item: item.get_user_id(), index=True)
    break_duration = fields.Float(string='Break Duration', default=0)
    total_absent_hours = fields.Float()
    calendar_id = fields.Many2one('resource.calendar', 'Calendar', readonly=True)
    office_hours = fields.Float(string='Attending Hours', default=0)
    official_hours = fields.Float(string='Official Hours', default=0)
    plan_hours = fields.Float(string='Planned Hours', default=0)
    carried_hours = fields.Float(string='Carried Hours', default=0)
    temp_exit = fields.Float(string='Temporary Exit Hours')
    temp_lateness = fields.Float(string='Temporary Lateness Hours')
    additional_hours = fields.Float(compute='get_additional_hours', string='Additional Hours', default=0, store=True)

    sequence = fields.Integer()
    attending_type = fields.Selection([('in_cal', 'within Calendar'),
                                       ('out_cal', 'out Calendar')], string='Attending Type', default="in_cal")
    company_id = fields.Many2one(related='employee_id.company_id')
    employee_number = fields.Char(related='employee_id.emp_no', string='Employee Number', store=True)
    department_id = fields.Many2one(related='employee_id.department_id', string='Department Name', store=True)
    is_branch = fields.Many2one(related='department_id.branch_name', store=True, readonly=True)

    has_sign_in = fields.Boolean(readonly=True)
    has_sign_out = fields.Boolean(readonly=True)

    '''to_date = fields.Boolean(string='Today',compute='_attendance_today', store=True)

    @api.depends('date','employee_id')
    def _attendance_today(self):
        today = datetime.now().date()
        for item in self:
            if item.date==today:
               item.to_date = True
            else:
               item.to_date = False'''

    @api.depends('employee_id', 'plan_hours', 'office_hours')
    def get_additional_hours(self):
        for rec in self:
            rec.additional_hours = 0
            if not rec.sign_in:
               rec.office_hours = rec.total_mission_hours
               rec.official_hours = rec.total_mission_hours
            if rec.office_hours > rec.plan_hours:
                rec.additional_hours = rec.office_hours - rec.plan_hours

                # rec.carried_hours = rec.office_hours - rec.plan_hours
    def get_shift_timings(self, item):
        calendar = item.calendar_id

        if calendar.is_full_day:
            min_sign_in = calendar.full_min_sign_in
            full_max_sign_in = calendar.full_max_sign_in
            max_sign_out = calendar.full_max_sign_out
            working_hours = calendar.working_hours
        else:
            if item.sequence == 1:
                min_sign_in = calendar.shift_one_min_sign_in
                full_max_sign_in = calendar.shift_one_max_sign_in
                max_sign_out = calendar.shift_one_max_sign_out
                working_hours = calendar.shift_one_working_hours
            elif item.sequence == 2:
                min_sign_in = calendar.shift_two_min_sign_in
                full_max_sign_in = calendar.shift_two_max_sign_in
                max_sign_out = calendar.shift_two_max_sign_out
                working_hours = calendar.shift_two_working_hours
            else:
                min_sign_in = max_sign_out = working_hours = None  # or default fallback

        return min_sign_in, full_max_sign_in , max_sign_out, working_hours

    def _compute_expected_times(self, item):
        """Helper function to compute expected sign-in and sign-out times based on calendar settings."""
        expected_sign_in = 0
        expected_sign_out = 0

        full_max_sign_in = item.calendar_id.full_max_sign_in
        full_min_sign_in = item.calendar_id.full_min_sign_in
        working_hours = item.calendar_id.working_hours

        if not item.calendar_id.is_full_day:
            if item.sequence == 1:
                full_max_sign_in = item.calendar_id.shift_one_max_sign_in
                full_min_sign_in = item.calendar_id.shift_one_min_sign_in
                working_hours = item.calendar_id.shift_one_working_hours
            elif item.sequence == 2:
                full_max_sign_in = item.calendar_id.shift_two_max_sign_in
                full_min_sign_in = item.calendar_id.shift_two_min_sign_in
                working_hours = item.calendar_id.shift_two_working_hours

        if item.sign_in < full_min_sign_in:
            expected_sign_in = full_min_sign_in
        elif full_min_sign_in <= item.sign_in <= full_max_sign_in:
            expected_sign_in = item.sign_in
        elif item.sign_in > full_max_sign_in:
            expected_sign_in = full_max_sign_in

        expected_sign_out = expected_sign_in + working_hours
        return expected_sign_in, expected_sign_out
    
    def set_lateness_and_exit(self, item , expected_sign_in=None , expected_sign_out=None):
        if not expected_sign_in and not expected_sign_out:
            expected_sign_in, expected_sign_out = self._compute_expected_times(item)

        is_late_sign_in = item.sign_in > expected_sign_in
        is_early_sign_out = item.sign_out > 0.0 and item.sign_out < expected_sign_out
        # Calculate lateness and exit time
        temp_lateness = (item.sign_out > 0.0 and is_late_sign_in) and (item.sign_in - expected_sign_in) or 0
        temp_exit = is_early_sign_out and (expected_sign_out - item.sign_out) or 0
        # Determine whether to approve lateness and exit
        approve_lateness = is_late_sign_in
        approve_exit_out = is_early_sign_out
        item.write({
            'temp_lateness': temp_lateness,
            'lateness': temp_lateness,
            'temp_exit': temp_exit,
            'early_exit': temp_exit,
            # 'office_hours': office_hours,
            'approve_lateness': approve_lateness,
            'approve_exit_out': approve_exit_out
        })

    def set_lateness_and_exit_zero(self, item , sign_in=None , sign_out=None):
        item.write({'sign_in': sign_in, 'sign_out': sign_out})
        self.set_lateness_and_exit(item)
        item.write({'sign_in': 0, 'sign_out': 0})
    
    def update_absence_status(self, item):
        working_hours = self._calculate_working_hours(item)
        item.update({'official_hours': working_hours})
        item.update({'is_absent': False})
        if not item.public_holiday and not item.is_official and not item.approve_personal_permission and not item.normal_leave:
            # # Mark as absent if working hours are less than the expected sign-in time
            if self._is_absent_due_to_working_hours(item, working_hours) or self._is_absent_due_to_no_sign_in_sign_out(item, working_hours):
                # self._update_absent_status(item)
                item.update({'is_absent': True})
        if item.official_id and  item.sign_in == 0.0 and item.sign_out == 0.0 \
            and not item.public_holiday \
                and not item.approve_personal_permission \
                    and not item.normal_leave \
                        and item.official_id.mission_type.absent_attendance:
            item.update({'is_absent': True})
                
        self.get_additional_hours()

    def _get_day_transactions(self, item):
        """ Helper method to fetch day transactions for an employee on a given date """
        return self.env['hr.attendance.transaction'].search([
            ('date', '=', item.date),
            ('attending_type', '=', 'in_cal'),
            ('employee_id', '=', item.employee_id.id)
        ])

    def _calculate_working_hours(self, day_trans):
        """ Helper method to calculate total working hours """
        day_trans.update({'office_hours': sum(day_trans.mapped('office_hours')) +  sum(day_trans.mapped('total_mission_hours'))})
        return (
            sum(day_trans.mapped('office_hours')) +  sum(day_trans.mapped('total_permission_hours'))
        )

    def _is_absent_due_to_working_hours(self, item, working_hours):
        """ Check if the employee is absent based on working hours """
        return (working_hours < item.calendar_id.end_sign_in and not item.calendar_id.is_flexible) \
            or (item.calendar_id.is_flexible and working_hours == 0.0)

    def _is_absent_due_to_no_sign_in_sign_out(self, item, working_hours):
        """ Check if the employee is absent based on missing sign-in and sign-out """
        return (working_hours == 0.0 and item.sign_in == 0.0 and item.sign_out == 0.0
                and not item.calendar_id.is_flexible)

    def _update_absent_status(self, day_trans):
        """ Helper method to mark transactions as absent """
        day_trans.filtered(lambda t: not t.public_holiday and not t.is_official and not t.normal_leave and not t.approve_personal_permission).update({'is_absent': True})
    
    def old(self): 
        # @api.depends('employee_id')
        # def get_hours(self):
        #     module = self.env['ir.module.module'].sudo()
        #     official_mission_module = module.search([('state', '=', 'installed'), ('name', '=', 'exp_official_mission')])
        #     holidays_module = module.search([('state', '=', 'installed'), ('name', '=', 'hr_holidays_public')])

        #     for item in self:
        #         item.is_absent = False
        #         item.total_absent_hours = 0

        #         # Skip attendance calculations for holidays, leaves, official missions
        #         if (item.attending_type == 'out_cal'
        #             or (holidays_module and (item.public_holiday or item.normal_leave))
        #             or (official_mission_module and item.is_official and item.official_id.mission_type.duration_type == 'days')):
                    
        #             item.write({
        #                 'temp_lateness': 0.0,
        #                 'temp_exit': 0.0,
        #                 'break_duration': 0.0,
        #                 'is_absent': False
        #             })
        #             if holidays_module and (item.public_holiday or item.normal_leave):
        #                 item.write({
        #                     'is_official': False,
        #                     'official_id': False,
        #                     'total_mission_hours': 0.0,
        #                     'approve_personal_permission': False,
        #                     'personal_permission_id': False,
        #                     'total_permission_hours': 0.0
        #                 })
        #             continue

        #         # Normal attendance processing
        #         day_trans = self.env['hr.attendance.transaction'].search([
        #             ('date', '=', item.date),
        #             ('attending_type', '=', 'in_cal'),
        #             ('employee_id', '=', item.employee_id.id)
        #         ])

        #         working_hours = (
        #             sum(day_trans.mapped('office_hours')) +
        #             sum(day_trans.mapped('total_mission_hours')) +
        #             sum(day_trans.mapped('total_permission_hours'))
        #         )
        #         item.update({'official_hours':working_hours})

        #         if not item.public_holiday:
        #             if (working_hours < item.calendar_id.end_sign_in and not item.calendar_id.is_flexible) \
        #                     or (item.calendar_id.is_flexible and working_hours == 0.0):
        #                 day_trans.filtered(lambda t: not t.public_holiday).update({'is_absent': True})
        #             if (working_hours == 0.0 and item.sign_in == 0.0 and item.sign_out == 0.0
        #                     and not item.calendar_id.is_flexible):
        #                 day_trans.filtered(lambda t: not t.public_holiday).update({'is_absent': True})

        #         if item.calendar_id.is_flexible:
        #             item.write({
        #                 'temp_lateness': 0.0,
        #                 'temp_exit': 0.0,
        #                 'official_hours': item.office_hours
        #             })

        #         ################### Break Duration Fix ####################
        #         if item.break_duration and item.calendar_id.break_duration:
        #             item.write({'break_duration': item.break_duration})

        #         if item.break_duration < 0:
        #             item.break_duration = 0

        #         # Call additional hour calculations
        #         self.get_additional_hours()

        # @api.depends('employee_id')
        # def get_hours(self):
        #     module = self.env['ir.module.module'].sudo()
        #     official_mission_module = module.search([('state', '=', 'installed'), ('name', '=', 'exp_official_mission')])
        #     holidays_module = module.search([('state', '=', 'installed'), ('name', '=', 'hr_holidays_public')])
        #     expected_sign_in = 0
        #     expected_sign_out = 0
        #     for item in self:
        #         item.is_absent = False
        #         item.approve_exit_out = False
        #         # item.is_official = False
        #         # item.total_absent_hours = 0
        #         # item.official_id = False
        #         # item.total_mission_hours = 0.0
        #         # item.approve_personal_permission = False
        #         # item.personal_permission_id = False
        #         # item.total_permission_hours = 0.0
        #         item.approve_lateness = False
        #         item.lateness = False
        #         item.early_exit = False
        #         item.total_absent_hours = 0

        #         if item.attending_type == 'out_cal' \
        #                 or holidays_module and (item.public_holiday or item.normal_leave) \
        #                 or official_mission_module and item.is_official and item.official_id.mission_type.duration_type == 'days':
        #             item.write({'temp_lateness': 0.0, 'temp_exit': 0.0, 'break_duration': 0.0, 'is_absent': False})
        #             if holidays_module and (item.public_holiday or item.normal_leave):
        #                 item.write({'is_official': False, 'official_id': False, 'total_mission_hours': 0.0,
        #                             'approve_personal_permission': False, 'personal_permission_id': False,
        #                             'total_permission_hours': 0.0})
        #         else:
        #             # noke
        #             # item.write({'temp_lateness': 0.0, 'temp_exit': 0.0, 'break_duration': 0.0, 'is_absent': False})
        #             day_trans = self.env['hr.attendance.transaction'].search([('date', '=', item.date),
        #                                      ('attending_type', '=', 'in_cal'),
        #                                      ('employee_id', '=', item.employee_id.id)])
        #             working_hours = sum(day_trans.mapped('official_hours')) \
        #                             + sum(day_trans.mapped('total_mission_hours')) \
        #                             + sum(day_trans.mapped('total_permission_hours'))

        #             if not item.public_holiday:
        #                 if working_hours < item.calendar_id.end_sign_in and not item.calendar_id.is_flexible \
        #                         or item.calendar_id.is_flexible and working_hours == 0.0:
        #                     day_trans.filtered(lambda t: t.public_holiday == False).update({'is_absent': True})
        #                 if working_hours == 0.0 and item.sign_in == 0.0 and item.sign_out == 0.0 and not item.calendar_id.is_flexible:
        #                     day_trans.filtered(lambda t: t.public_holiday == False).update({'is_absent': True})
        #         if item.calendar_id.is_flexible:
        #             item.write({'temp_lateness': 0.0, 'temp_exit': 0.0, 'official_hours': item.office_hours})
        #         # if item.temp_lateness:
        #         #     item.approve_lateness = True
        #         # if item.temp_exit:
        #         #     item.approve_exit_out = True
        #         #################### Fix lateness,exit_out start #######################
        #         if item.temp_lateness or item.temp_exit:  # solve one cases and add other case #TODO
        #             full_max_sign_in = item.calendar_id.full_max_sign_in
        #             full_min_sign_in = item.calendar_id.full_min_sign_in
        #             working_hours = item.calendar_id.working_hours
        #             if not item.calendar_id.is_full_day:
        #                 if item.sequence == 1:
        #                     full_max_sign_in = item.calendar_id.shift_one_max_sign_in
        #                     full_min_sign_in = item.calendar_id.shift_one_min_sign_in
        #                     working_hours = item.calendar_id.shift_one_working_hours
        #                 if item.sequence == 2:
        #                     full_max_sign_in = item.calendar_id.shift_two_max_sign_in
        #                     full_min_sign_in = item.calendar_id.shift_two_min_sign_in
        #                     working_hours = item.calendar_id.shift_two_working_hours

        #             is_late_sign_in = item.sign_in > full_max_sign_in
        #             if item.sign_in < full_min_sign_in:
        #                 expected_sign_in = full_min_sign_in
        #             if item.sign_in >= full_min_sign_in and item.sign_in <= full_max_sign_in:
        #                 expected_sign_in = item.sign_in
        #             if is_late_sign_in:
        #                 expected_sign_in = full_max_sign_in
        #             expected_sign_out = expected_sign_in + working_hours
        #             is_early_sign_out = item.sign_out > 0.0 and item.sign_out < expected_sign_out
        #             item.temp_lateness = item.sign_out > 0.0 and is_late_sign_in and item.sign_in - expected_sign_in or 0
        #             item.temp_exit = is_early_sign_out and expected_sign_out - item.sign_out or 0
        #             item.approve_lateness = is_late_sign_in
        #             item.approve_exit_out = is_early_sign_out

        #             # if item.sign_out == 0.0:
        #             # item.is_absent = True
        #         #################### Fix end #######################
        #         if item.break_duration and item.calendar_id.break_duration:
        #             # item.write({'break_duration': item.break_duration - item.calendar_id.break_duration})  #TODO
        #             item.write({'break_duration': item.break_duration})
        #         if item.break_duration < 0:
        #             item.break_duration = 0
        #         item.manage_mission(    
        #             item.id,
        #             self.convert_float_2time(expected_sign_in, fields.Date.from_string(item.date)),
        #             self.convert_float_2time(expected_sign_out, fields.Date.from_string(item.date)),
        #             self.convert_float_2time(item.sign_in,fields.Date.from_string(item.date)),
        #             self.convert_float_2time(item.sign_out,fields.Date.from_string(item.date)),
        #             False
        #         )
        #         item.lateness = item.temp_lateness
        #         item.early_exit = item.temp_exit
        #         self.get_additional_hours()   
        pass
    
    def get_sign_time(self, sign):
        ''' Func: return time as float considering timezone(fixed 3)'''

        # DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
        TIME_FORMAT = "%H:%M:%S"
        TIME_ZONE_FORMAT = '%Y-%m-%d %H:%M:%S.%f'
        sign_offsit = datetime.strptime(str(sign), DATETIME_FORMAT) + timedelta(hours=3)
        sign_zone = datetime.strptime(sign_offsit.strftime(TIME_ZONE_FORMAT), TIME_ZONE_FORMAT)
        return round(datetime.strptime(sign_zone.strftime(TIME_FORMAT), TIME_FORMAT).time().hour + 
                     datetime.strptime(sign_zone.strftime(TIME_FORMAT), TIME_FORMAT).time().minute / 60.0, 2), sign_zone

    def convert_float_2time(self, time, date=None):
        hour, minute = divmod(time * 60, 60)
        if date:
            if not isinstance(date, datetime): date = fields.Datetime.from_string(date)
            return date.replace(hour=int(hour), minute=int(round(minute)), second=0) - timedelta(hours=3)
        return hour, round(minute)

    def get_day_timing(self, calendar, weekday, wkd_date):
        planed_hours = {'one': 0, 'two': 0}
        if calendar.is_full_day:
            time_list = [0 for i in range(4)]
            sp_timing = self.get_speacial_day_timing(calendar, weekday, wkd_date)
            planed_hours['one'] = (
                                          sp_timing and sp_timing.working_hours or calendar.working_hours) - calendar.break_duration
            time_list[0] = sp_timing and sp_timing.start_sign_in or calendar.full_min_sign_in
            time_list[1] = sp_timing and sp_timing.end_sign_in or calendar.full_max_sign_in
            time_list[2] = sp_timing and sp_timing.start_sign_out or calendar.full_min_sign_out
            time_list[3] = sp_timing and sp_timing.end_sign_out or calendar.full_max_sign_out
        else:
            time_list = [0 for i in range(8)]
            one_sp_timing = self.get_speacial_day_timing(calendar, weekday, wkd_date, 'one')
            planed_hours['one'] = (one_sp_timing and one_sp_timing.working_hours or calendar.shift_one_working_hours) \
                                  -calendar.shift_one_break_duration
            two_sp_timing = self.get_speacial_day_timing(calendar, weekday, wkd_date, 'two')
            planed_hours['two'] = (two_sp_timing and two_sp_timing.working_hours or calendar.shift_two_working_hours) \
                                  -calendar.shift_two_break_duration
            time_list[0] = one_sp_timing and one_sp_timing.start_sign_in or calendar.shift_one_min_sign_in
            time_list[1] = one_sp_timing and one_sp_timing.end_sign_in or calendar.shift_one_max_sign_in
            time_list[2] = one_sp_timing and one_sp_timing.start_sign_out or calendar.shift_one_min_sign_out
            time_list[3] = one_sp_timing and one_sp_timing.end_sign_out or calendar.shift_one_max_sign_out
            time_list[4] = two_sp_timing and two_sp_timing.start_sign_in or calendar.shift_two_min_sign_in
            time_list[5] = two_sp_timing and two_sp_timing.end_sign_in or calendar.shift_two_max_sign_in
            time_list[6] = two_sp_timing and two_sp_timing.start_sign_out or calendar.shift_two_min_sign_out
            time_list[7] = two_sp_timing and two_sp_timing.end_sign_out or calendar.shift_two_max_sign_out
        return time_list, planed_hours

    # def get_speacial_day_timing(self, calender, weekday, at_date, shift=None):
    #     sp_days = shift and calender.special_days_partcial or calender.special_days
    #     for spday in sp_days:
    #         if spday.name.lower() == weekday and ((shift and spday.shift == shift) or (not shift and True)):
    #             if spday.date_from and spday.date_to \
    #                     and str(at_date) >= spday.date_from and str(at_date) <= spday.date_to:
    #                 return spday
    #             elif spday.date_from and not spday.date_to and str(at_date) >= spday.date_from:
    #                 return spday
    #             elif not spday.date_from and spday.date_to and str(at_date) <= spday.date_to:
    #                 return spday
    #             elif not spday.date_from and not spday.date_to:
    #                 return spday

    def get_speacial_day_timing(self, calender, weekday, at_date, shift=None):
        # Ensure at_date is a date object
        if isinstance(at_date, str):
            # Adjust the format string to match your date string format
            at_date = datetime.strptime(at_date, "%Y-%m-%d").date()
        sp_days = shift and calender.special_days_partcial or calender.special_days
        for spday in sp_days:
            if spday.name.lower() == weekday and ((shift and spday.shift == shift) or (not shift and True)):
                if spday.date_from and spday.date_to \
                        and at_date >= spday.date_from and at_date <= spday.date_to:
                    return spday
                elif spday.date_from and not spday.date_to and at_date >= spday.date_from:
                    return spday
                elif not spday.date_from and spday.date_to and at_date <= spday.date_to:
                    return spday
                elif not spday.date_from and not spday.date_to:
                    return spday

    def one_day_noke(self, noke_calendar):
        if noke_calendar.is_full_day:
            if noke_calendar.full_min_sign_in <= noke_calendar.full_max_sign_in \
                    < noke_calendar.full_min_sign_out <= noke_calendar.full_max_sign_out: return True
            return False
        else:
            if noke_calendar.shift_one_min_sign_in <= noke_calendar.shift_one_max_sign_in \
                    < noke_calendar.shift_one_min_sign_out <= noke_calendar.shift_one_max_sign_out \
                    < noke_calendar.shift_two_min_sign_in <= noke_calendar.shift_two_max_sign_in \
                    < noke_calendar.shift_two_min_sign_out <= noke_calendar.shift_two_max_sign_out: return True
            return False

    def noke_time_2date(self, time, noke_dt, calendar):
        last_nt = calendar[0]
        if calendar[0] < last_nt:
            noke_dt += timedelta(1)
        if time == 'one_max_in':
            return self.convert_float_2time(calendar[1], noke_dt)
        last_nt = calendar[1]
        if calendar[2] < last_nt:
            noke_dt += timedelta(1)
        if time == 'one_min_out':
            return self.convert_float_2time(calendar[2], noke_dt)
        last_nt = calendar[2]
        if calendar[3] < last_nt:
            noke_dt += timedelta(1)
        if time == 'one_max_out':
            return self.convert_float_2time(calendar[3], noke_dt)
        last_nt = calendar[3]
        if calendar[4] < last_nt:
            noke_dt += timedelta(1)
        if time == 'two_min_in':
            return self.convert_float_2time(calendar[4], noke_dt)
        last_nt = calendar[4]
        if calendar[5] < last_nt:
            noke_dt += timedelta(1)
        if time == 'two_max_in':
            return self.convert_float_2time(calendar[5], noke_dt)
        last_nt = calendar[5]
        if calendar[6] < last_nt:
            noke_dt += timedelta(1)
        if time == 'two_min_out':
            return self.convert_float_2time(calendar[6], noke_dt)
        last_nt = calendar[6]
        if calendar[7] < last_nt:
            noke_dt += timedelta(1)
        if time == 'two_max_out':
            return self.convert_float_2time(calendar[7], noke_dt)

    def prepare_shift(self, at_device, dt, signs_in, signs_out, min_in_dt, max_in_dt, min_out_dt, max_out_dt,
                      shift_dict, next_min_in_dt=None):
        attending_periods, linked_out_ids = [], []
        office_hours, official_hours, break_hours = 0, 0, 0
        at_dict = {'in': 0.0, 'out': 0.0, 'creep': 0}
        if signs_in:
            if not signs_out:
                at_dict['in'] = fields.Datetime.from_string(signs_in[0].name)
                if at_device:
                    at_dict['checkin_device_id'] = signs_in[0].device_id and signs_in[0].device_id.id or False
                    at_dict['checkout_device_id'] = False
                attending_periods.append(at_dict)
                linked_out_ids.append(signs_in[0].id)
            else:
                signs_time = []
                last_official_sign = True
                for sin in signs_in:

                    in_dt = fields.Datetime.from_string(sin.name)
                    for out in signs_out:

                        out_dt = fields.Datetime.from_string(out.name)

                        if signs_time and in_dt < last_out:
                            continue
                        if out_dt >= in_dt and out_dt >= min_in_dt \
                                and ((linked_out_ids and out.id not in linked_out_ids) or not linked_out_ids):

                            creep = next_min_in_dt \
                                    and (out_dt > next_min_in_dt and (out_dt - next_min_in_dt).seconds / 60 / 60) or 0.0
                            at_dic = {'in': in_dt, 'out': out_dt, 'creep': creep}
                            if at_device:
                                at_dic['checkin_device_id'] = sin.device_id and sin.device_id.id or False
                                at_dic['checkout_device_id'] = out.device_id and out.device_id.id or False
                            attending_periods.append(at_dic)

                            at_dic = {}
                            last_out = out_dt
                            linked_out_ids.append(out.id)
                            signs_time.append(in_dt)
                            signs_time.append(out_dt)
                            office_hours += (out_dt - in_dt).seconds / 60 / 60
                            if out_dt <= max_out_dt:
                                official_hours += (out_dt - in_dt).seconds / 60 / 60
                            elif out_dt > max_out_dt and last_official_sign:
                                official_hours += (max_out_dt - in_dt).seconds / 60 / 60
                                last_official_sign = False
                            break

        else:
            if next_min_in_dt:
                signed = False
                for out in signs_out:
                    out_dt = fields.Datetime.from_string(out.name)
                    if out_dt < next_min_in_dt:
                        one_out_dt = out_dt
                        #checkout_device = out.device_id
                        checkout_device = out.device_id if at_device else False
                        linked_out_ids.append(out.id)
                        signed = True
                    else:
                        break
                if not signed:
                    return
                at_dict['out'] = one_out_dt
                if at_device:
                    at_dict['checkin_device_id'] = False
                    at_dict['checkout_device_id'] = checkout_device and checkout_device.id or False
                attending_periods.append(at_dict)

            else:
                at_dict['out'] = fields.Datetime.from_string(signs_out[-1].name)
                if at_device:
                    at_dict['checkin_device_id'] = False
                    at_dict['checkout_device_id'] = signs_out[-1].device_id and signs_out[-1].device_id.id or False
                attending_periods.append(at_dict)

                linked_out_ids.append(signs_out[-1].id)
        if at_device:
            if attending_periods:
                shift_dict['checkin_device_id'] = attending_periods[0]['checkin_device_id']
                shift_dict['checkout_device_id'] = attending_periods[-1]['checkout_device_id']
            else:
                shift_dict['checkin_device_id'] = False
                shift_dict['checkout_device_id'] = False

        if attending_periods:
            sign_in = attending_periods[0]['in']
            sign_out = attending_periods[-1]['out']
        else:
            sign_in = 0.0
            sign_out = 0.0

        # sign_in, sign_out = attending_periods[0]['in'], attending_periods[-1]['out']

        shift_dict['sign_in'] = sign_in and self.get_sign_time(fields.Datetime.to_string(sign_in))[0] or 0.0
        shift_dict['has_sign_in'] = bool(signs_in)
        shift_dict['sign_out'] = sign_out and self.get_sign_time(fields.Datetime.to_string(sign_out))[0] or 0.0
        shift_dict['has_sign_out'] = bool(signs_out)
        shift_dict['sign_in_dt'] = sign_in and sign_in or 0.0
        shift_dict['sign_out_dt'] = sign_out and sign_out or 0.0
        '''shift_dict['temp_lateness'] = sign_in and sign_out and (
                sign_in > max_in_dt and round((sign_in - min_in_dt).seconds / 60 / 60, 2)) or 0.0
        shift_dict['temp_exit'] = sign_in and sign_out and (
                sign_out < min_out_dt and round((max_out_dt - sign_out).seconds / 60 / 60, 2)) or 0.0'''
        ####################
        if sign_in and not sign_out and max_in_dt and sign_in > max_in_dt:
            shift_dict['temp_lateness'] = round((sign_in - max_in_dt).seconds / 60 / 60, 2)
        elif sign_in and sign_out and max_out_dt and \
                sign_in > min_in_dt and min_out_dt <= sign_out <= max_out_dt:
            temp_lateness = round((sign_in - min_in_dt).seconds / 60 / 60, 2) - round(
                (sign_out - min_out_dt).seconds / 60 / 60, 2)
            shift_dict['temp_lateness'] = temp_lateness if temp_lateness > 0 else 0.0
        elif sign_in and sign_out and max_out_dt and \
                sign_in > min_in_dt and sign_out <= min_out_dt:
            temp_lateness = round((sign_in - min_in_dt).seconds / 60 / 60, 2)
            shift_dict['temp_lateness'] = temp_lateness if temp_lateness > 0 else 0.0
        # elif sign_in and sign_out and max_in_dt and max_out_dt and sign_in > max_in_dt and sign_out >= max_out_dt:
        #     temp_lateness = round((sign_in - max_in_dt).seconds / 60 / 60, 2)
        #     shift_dict['temp_lateness'] = temp_lateness if temp_lateness > 0 else 0.0
        elif sign_in and sign_out and max_in_dt and max_out_dt and sign_in > max_in_dt and sign_out >= max_out_dt:
            temp_lateness = round((sign_in - max_in_dt).seconds / 60 / 60, 2)
            shift_dict['temp_lateness'] = temp_lateness
        elif sign_in and sign_out and not max_out_dt and sign_in > min_in_dt and min_out_dt <= sign_out <= max_out_dt:
            shift_dict['temp_lateness'] = round((sign_in - min_in_dt).seconds / 60 / 60, 2)
        else:
            shift_dict['temp_lateness'] = 0.0

        shift_dict['temp_exit'] = sign_in and sign_out and (sign_out < min_out_dt and
                                                            round((min_out_dt - sign_out).seconds / 60 / 60, 2)) or 0.0
        ##############################
        shift_dict['break_duration'] = 0.0
        shift_dict['office_hours'], shift_dict['official_hours'] = office_hours, official_hours
        if sign_in and sign_out and ((next_min_in_dt and sign_in > max_out_dt and sign_out < next_min_in_dt)
                                     or (not next_min_in_dt and sign_in > max_out_dt)):
            shift_dict['attending_type'] = 'out_cal'
        if sign_in or sign_out == 0: shift_dict['is_absent'] = True
        if len(attending_periods) > 1:
            break_periods = []
            del signs_time[0]
            del signs_time[-1]
            for inx, sign_time in enumerate(signs_time):
                if inx % 2 == 0:
                    break_start = sign_time
                else:
                    break_hours += round((sign_time - break_start).seconds / 60 / 60, 2)
                    break_periods.append({'break_start': break_start, 'break_end': sign_time})
            shift_dict['break_duration'] = break_hours
        if attending_periods:
            creep = round(attending_periods[-1]['creep'], 2)
        else:
            creep = 0.0
        if break_hours:
            return {'shift': shift_dict, 'out_ids': linked_out_ids, 'creep': creep, 'break_periods': break_periods}
        return {'shift': shift_dict, 'out_ids': linked_out_ids, 'creep': creep}

    def manage_permission(self, trans_id, shift_in, shift_out, sign_in, sign_out, breaks, state=None):
        #print(trans_id, "*********************manage_permission***********************************")
        trans, feedback = self.browse(trans_id)[0], []       
        # حساب التوقيع المتوقع للدخول والخروج بناء علي بصمة الدخول              
        expected_sign_in, expected_sign_out = self._compute_expected_times(trans)
        # الحصول على أوقات الحضور والانصراف المسموح بها وعدد ساعات العمل
        full_min_sign_in, full_max_sign_in, full_max_sign_out, working_hours = self.get_shift_timings(trans)
        # تحديد الشفت من اعلي زمن دخول الي اعلي زمن خروج للبحث عن اذن خلال الشفت 
        shift_in = self.convert_float_2time(full_min_sign_in, fields.Date.from_string(trans.date))
        shift_out = self.convert_float_2time(full_max_sign_out, fields.Date.from_string(trans.date))
        # إعادة تعيين أي بيانات إذن شخصي قديمة
        if trans.personal_permission_id:
            trans.update({'approve_personal_permission': False, 'personal_permission_id': False, 'total_permission_hours': 0.0})
        # البحث عن الأذونات الشخصية المعتمدة في نفس يوم الحضور
        permissions = self.env['hr.personal.permission'].search(
            [('state', '=', 'approve'), ('employee_id', '=', trans.employee_id.id),
             '|', '|',
             '&', ('date_to', '<=', str(shift_out)), ('date_to', '>=', str(shift_in)),
             '&', ('date_from', '<=', str(shift_out)), ('date_from', '>=', str(shift_in)),
             '&', ('date_from', '<=', str(shift_in)), ('date_to', '>=', str(shift_out))
             ])
        if permissions:
            # إعادة ضبط أوقات بداية ونهاية الشفت بناءً على التوقعات من بصمة الدخول لمعالجة حساب الاذن ان لايتعدي الاذن فتره خارج الدوام 
            shift_in = self.convert_float_2time(expected_sign_in, fields.Date.from_string(trans.date))
            shift_out = self.convert_float_2time(expected_sign_out, fields.Date.from_string(trans.date))
            for perm in permissions:
                perm_time = 0
                perm_time = 0
                time_perm_df = self.get_sign_time(perm.date_from)[0]
                time_perm_dt = self.get_sign_time(perm.date_to)[0]
                perm_df = fields.Datetime.from_string(perm.date_from)
                perm_dt = fields.Datetime.from_string(perm.date_to)
                # معالجة حالات الغياب الكامل اذا كان هناك اذن ,يتم حساب التاخير قبل وقت بداية الاذن ويتم حساب الخروج المبكر بعد نهاية الاذن 
                if trans.sign_in == 0.0 and trans.sign_out == 0.0:
                    total_permission_hours = min (perm.duration, trans.plan_hours)
                    trans.set_lateness_and_exit_zero(trans, time_perm_df, time_perm_dt)
                    perm_dic = {'approve_personal_permission': True, 'personal_permission_id': perm.id, 'total_permission_hours': total_permission_hours }
                    if state != 'check': trans.update(perm_dic)
                    if state is not None:
                        feedback.append({'perm_id': perm.id, 'perm_start': perm_df, 'perm_end': perm_dt, 'type': 'all'})
                    continue
                elif trans.sign_in == 0.0 or trans.sign_out == 0.0:
                    total_permission_hours = min (perm.duration, trans.plan_hours)
                    perm_dic = {'approve_personal_permission': True, 'personal_permission_id': perm.id, 'total_permission_hours': total_permission_hours }
                    if state != 'check': trans.update(perm_dic)
                    if state is not None:
                        feedback.append({'perm_id': perm.id, 'perm_start': perm_df, 'perm_end': perm_dt, 'type': 'all'})
                    continue
                # Handling lateness and exit time adjustments
                elif trans.temp_lateness or trans.temp_exit:
                    # التحقق مما إذا كان وقت بداية الإذن الشخصي (time_perm_df) 
                    # يقع بعد بداية الدوام المسموح بها (full_min_sign_in)،
                    # وقبل توقيت توقيع الدخول الفعلي (trans.sign_in)،
                    # وضمن فترة الحضور المسموح بها (حتى full_max_sign_in).
                    # لحساب دوام الموظف من بداية الاذن الي نهاية الاذن  + ساعات العمل بمعني الاذن فتره صباحية قبل بصمة دخول الموظف
                    if time_perm_df < trans.sign_in  and time_perm_df > full_min_sign_in and time_perm_df <= full_max_sign_in:
                        trans.set_lateness_and_exit(trans, time_perm_df, time_perm_df + working_hours)  # expected_sign_out)
                        #  اعاده احتساب الشفت , بما ان الاذن فتره صباحية اذا الشفت يبداء من بداية الاذن الي بداية الاذن +ساعات العمل 
                        shift_in = self.convert_float_2time(time_perm_df, fields.Date.from_string(trans.date))
                        shift_out = self.convert_float_2time(time_perm_df + working_hours, fields.Date.from_string(trans.date))
                    if trans.temp_lateness:
                        if perm_df <= shift_in and perm_dt >= sign_in:
                            perm_time = round((sign_in - shift_in).seconds / 3600 , 2)
                            perm_start, perm_end = shift_in, sign_in
                        elif perm_df <= shift_in and perm_dt < sign_in and perm_dt > shift_in:
                            perm_time = round((perm_dt - shift_in).seconds / 3600 , 2)
                            perm_start, perm_end = shift_in, perm_dt
                        elif (perm_df > shift_in and perm_dt < sign_in) or sign_in == 0.0 or sign_out == 0.0:
                            perm_time = round((perm_dt - perm_df).seconds / 3600 , 2)
                            perm_start, perm_end = perm_df, perm_dt
                        elif perm_df < sign_in and perm_df > shift_in and perm_dt >= sign_in:
                            perm_time = round((sign_in - perm_df).seconds / 3600 , 2)
                            perm_start, perm_end = perm_df, sign_in
                        if perm_time:
                            perm_lateness_remaining = trans.lateness - perm_time
                            perm_dic = {'approve_personal_permission': True,
                                        'personal_permission_id': perm.id,
                                        'total_permission_hours': perm_time,
                                        'temp_lateness': max(perm_lateness_remaining , 0),
                                        'lateness': max (perm_lateness_remaining , 0),
                                        'approve_lateness': perm_lateness_remaining > 0
                                        }

                            perm_time = 0
                            if state != 'check': trans.update(perm_dic)
                            if state is not None:
                                feedback.append({'perm_id': perm.id, 'perm_start': perm_start, 'perm_end': perm_end, 'type': 'late'})
                    if trans.temp_exit:
                        if perm_df <= sign_out and perm_dt >= shift_out:
                            perm_time = round((shift_out - sign_out).seconds / 60 / 60, 2)
                            perm_start, perm_end = sign_out, shift_out
                        elif perm_df <= sign_out and perm_dt < shift_out and perm_dt > sign_out:
                            perm_time = round((perm_dt - sign_out).seconds / 60 / 60, 2)
                            perm_start, perm_end = sign_out, perm_dt
                        elif perm_df > sign_out and perm_dt >= shift_out and perm_df < shift_out:
                            perm_time = round((shift_out - perm_df).seconds / 60 / 60, 2)
                            perm_start, perm_end = perm_df, shift_out
                        elif perm_df > sign_out and perm_dt < shift_out:
                            perm_time = round((perm_dt - perm_df).seconds / 60 / 60, 2)
                            perm_start, perm_end = perm_df, perm_dt
                        if perm_time:
                            exit_remaining = trans.early_exit - perm_time
                            perm_dic = {
                                'total_permission_hours': perm_time,
                                'personal_permission_id': perm.id,
                                'approve_personal_permission': True,
                                'temp_exit': max(exit_remaining, 0),
                                'early_exit':max(exit_remaining, 0),
                                'approve_exit_out': exit_remaining > 0
                            }
                            perm_time = 0
                            if state != 'check': trans.update(perm_dic)
                            if state is not None:
                                feedback.append(
                                    {'perm_id': perm.id, 'perm_start': perm_start, 'perm_end': perm_end, 'type': 'exit'})
                elif breaks:
                    for brk in breaks:
                        if not (perm_df < perm_dt and brk['break_start'] < brk['break_end']): continue
                        if brk['break_start'] <= perm_df and brk['break_end'] >= perm_dt:
                            perm_time = round((perm_dt - perm_df).seconds / 60 / 60, 2)
                            perm_start, perm_end = perm_df, perm_dt
                        elif brk['break_start'] > perm_df and brk['break_end'] < perm_dt:
                            perm_time = round((brk['break_end'] - brk['break_start']).seconds / 60 / 60, 2)
                            perm_start, perm_end = brk['break_start'], brk['break_end']
                        elif brk['break_start'] <= perm_df and brk['break_end'] < perm_dt and brk[
                            'break_end'] > perm_df:
                            perm_time = round((brk['break_end'] - perm_df).seconds / 60 / 60, 2)
                            perm_start, perm_end = perm_df, brk['break_end']
                        elif brk['break_start'] > perm_df and brk['break_end'] >= perm_dt and brk[
                            'break_start'] < perm_dt:
                            perm_time = round((perm_dt - brk['break_start']).seconds / 60 / 60, 2)
                            perm_start, perm_end = brk['break_start'], perm_dt
                        if perm_time:
                            perm_dic = {'approve_personal_permission': True,
                                        'personal_permission_id': perm.id,
                                        'total_permission_hours': perm_time,
                                        'break_duration': trans.break_duration - perm_time,
                                        }
                            if state != 'check': trans.update(perm_dic)
                            if state is not None:
                                feedback.append(
                                    {'perm_id': perm.id, 'perm_start': perm_start, 'perm_end': perm_end,
                                    'type': 'break'})
            if state is not None: return feedback
    
    def manage_mission(self, trans_id, shift_in, shift_out, sign_in, sign_out, breaks, state=None):
        #print(trans_id, "*********************manage_mission***********************************")
        trans , feedback = self.browse(trans_id)[0] , []
        expected_sign_in, expected_sign_out = self._compute_expected_times(trans)
        full_min_sign_in, full_max_sign_in, full_max_sign_out, working_hours = self.get_shift_timings(trans)
        shift_in = self.convert_float_2time(full_min_sign_in, fields.Date.from_string(trans.date))
        shift_out = self.convert_float_2time(full_max_sign_out, fields.Date.from_string(trans.date))
        if trans.official_id:
            trans.update({'is_official': False, 'official_id': False, 'total_mission_hours': 0.0})
        date_from_time = (shift_in + timedelta(hours=3)).time()
        date_to_time = (shift_out + timedelta(hours=3)).time()
        hour_from = date_from_time.hour + date_from_time.minute / 60.0
        hour_to = date_to_time.hour + date_to_time.minute / 60
        missions = self.env['hr.official.mission'].search([
            ('state', '=', 'approve'),
            ('employee_ids.employee_id', 'in', [trans.employee_id.id]),
            ('employee_ids.date_from', '<=', str(shift_in.date())),
            ('employee_ids.date_to', '>=', str(shift_in.date())),
            '|', '|',
            '&', ('employee_ids.hour_from', '<=', hour_from), ('employee_ids.hour_to', '>=', hour_from),
            '&', ('employee_ids.hour_from', '<=', hour_to), ('employee_ids.hour_to', '>=', hour_to),
            '&', ('employee_ids.hour_from', '>=', hour_from), ('employee_ids.hour_to', '<=', hour_to),
        ])
        if missions:
            shift_in = self.convert_float_2time(expected_sign_in, fields.Date.from_string(trans.date))
            shift_out = self.convert_float_2time(expected_sign_out, fields.Date.from_string(trans.date))
            for mission in missions: 
                emp_mission = mission.employee_ids.filtered(lambda m: m.employee_id.id == trans.employee_id.id)[0]
                mission_df = self.convert_float_2time(emp_mission.hour_from, str(trans.date))
                mission_dt = self.convert_float_2time(emp_mission.hour_to, str(trans.date))
                temp_hour = 0
                miss_time = 0
                # If no sign_in or sign_out, update official mission hours
                # if trans.sign_in == 0.0 or trans.sign_out == 0.0:
                if trans.sign_in == 0.0 and trans.sign_out == 0.0:
                    mission_hours = min(trans.plan_hours, emp_mission.hours)
                    if not mission.mission_type.absent_attendance:
                        trans.set_lateness_and_exit_zero(trans, emp_mission.hour_from, emp_mission.hour_to)
                    miss_dic = {'is_official': True, 'official_id': mission.id, 'total_mission_hours': mission_hours}
                    if state != 'check':trans.update(miss_dic)
                    if state is not None:feedback.append({'mission_id': mission.id, 'miss_start': mission_df, 'miss_end': mission_dt, 'type': 'all'})
                    continue
                elif trans.sign_in == 0.0 or trans.sign_out == 0.0:
                    mission_hours = min(trans.plan_hours, emp_mission.hours)
                    miss_dic = {'is_official': True, 'official_id': mission.id, 'total_mission_hours': mission_hours, }
                    if state != 'check':trans.update(miss_dic)
                    if state is not None:feedback.append({'mission_id': mission.id, 'miss_start': mission_df, 'miss_end': mission_dt, 'type': 'all'})
                    continue
                # Handling lateness and exit time adjustments
                elif trans.temp_lateness or trans.temp_exit:
                    if emp_mission.hour_from <= trans.sign_in  and emp_mission.hour_from >= full_min_sign_in and emp_mission.hour_from <= full_max_sign_in:
                        temp_sign_out = emp_mission.hour_from + working_hours
                        trans.set_lateness_and_exit(trans, emp_mission.hour_from, temp_sign_out)  # expected_sign_out)
                        shift_in = self.convert_float_2time(emp_mission.hour_from, fields.Date.from_string(trans.date))
                        shift_out = self.convert_float_2time(emp_mission.hour_from + working_hours, fields.Date.from_string(trans.date))
                        if temp_sign_out <= trans.sign_out <= full_max_sign_out:
                            temp_hour = trans.sign_out - temp_sign_out
                        if temp_sign_out < trans.sign_out >= full_max_sign_out:
                            temp_hour = full_max_sign_out - temp_sign_out
                    # Handle lateness
                    if trans.temp_lateness:
                        if mission_df <= shift_in and mission_dt >= sign_in:
                            miss_time_late = round((sign_in - shift_in).seconds / 3600, 2)
                            miss_start_late, miss_end_late = shift_in, sign_in
                        elif mission_df <= shift_in and mission_dt < sign_in and mission_dt > shift_in:
                            miss_time_late = round((mission_dt - shift_in).seconds / 3600, 2)
                            miss_start_late, miss_end_late = shift_in, mission_dt
                        elif mission_df > shift_in and mission_dt < sign_in:
                            miss_time_late = round((mission_dt - mission_df).seconds / 3600, 2)
                            miss_start_late, miss_end_late = mission_df, mission_dt
                        elif mission_df < sign_in and mission_df > shift_in and mission_dt >= sign_in:
                            miss_time_late = round((sign_in - mission_df).seconds / 3600, 2)
                            miss_start_late, miss_end_late = mission_df, sign_in
                        else:
                            miss_time_late = 0
                        if miss_time_late :
                            miss_dic = {'is_official': True, 'official_id': mission.id}
                            lateness_remaining = (trans.lateness - miss_time_late) - temp_hour
                            miss_dic.update({
                                'total_mission_hours': miss_time_late,
                                'temp_lateness': max(lateness_remaining , 0),
                                'lateness': max (lateness_remaining , 0),
                                'approve_lateness': lateness_remaining > 0
                            })
                            if state != 'check':
                                trans.update(miss_dic)
                            if state is not None:
                                feedback.append({
                                    'mission_id': mission.id,
                                    'miss_start': miss_start_late,
                                    'miss_end': miss_end_late,
                                    'type': 'late'
                                })
                    # Handle early exit
                    if trans.temp_exit:
                        if mission_df <= sign_out and mission_dt >= shift_out:
                            miss_time_exit = round((shift_out - sign_out).seconds / 3600, 2)
                            miss_start_exit, miss_end_exit = sign_out, shift_out
                        elif mission_df <= sign_out and mission_dt < shift_out and mission_dt > sign_out:
                            miss_time_exit = round((mission_dt - sign_out).seconds / 3600, 2)
                            miss_start_exit, miss_end_exit = sign_out, mission_dt
                        elif mission_df > sign_out and mission_dt >= shift_out and mission_df < shift_out:
                            miss_time_exit = round((shift_out - mission_df).seconds / 3600, 2)
                            miss_start_exit, miss_end_exit = mission_df, shift_out
                        elif mission_df > sign_out and mission_dt < shift_out:
                            miss_time_exit = round((mission_dt - mission_df).seconds / 3600, 2)
                            miss_start_exit, miss_end_exit = mission_df, mission_dt
                        else:
                            miss_time_exit = 0
                        if miss_time_exit :
                            miss_dic = {'is_official': True, 'official_id': mission.id}
                            exit_remaining = trans.early_exit - miss_time_exit
                            miss_dic.update({
                                'total_mission_hours': miss_time_exit,
                                'temp_exit': exit_remaining if exit_remaining > 0 else 0,
                                'early_exit':exit_remaining if exit_remaining > 0 else 0,
                                'approve_exit_out': exit_remaining > 0
                            })
                            
                            if state != 'check':
                                trans.update(miss_dic)
                            if state is not None:
                                feedback.append({
                                    'mission_id': mission.id,
                                    'miss_start': miss_start_exit,
                                    'miss_end': miss_end_exit,
                                    'type': 'exit'
                                })
                # Handling breaks
                elif breaks:
                    for brk in breaks:
                        if mission_df < mission_dt and brk['break_start'] < brk['break_end']:
                            if brk['break_start'] <= mission_df and brk['break_end'] >= mission_dt:
                                miss_time = round((mission_dt - mission_df).seconds / 3600, 2)
                                miss_start, miss_end = mission_df, mission_dt
                            elif brk['break_start'] > mission_df and brk['break_end'] < mission_dt:
                                miss_time = round((brk['break_end'] - brk['break_start']).seconds / 3600, 2)
                                miss_start, miss_end = brk['break_start'], brk['break_end']
                            elif brk['break_start'] <= mission_df and brk['break_end'] < mission_dt and brk['break_end'] > mission_df:
                                miss_time = round((brk['break_end'] - mission_df).seconds / 3600, 2)
                                miss_start, miss_end = mission_df, brk['break_end']
                            elif brk['break_start'] > mission_df and brk['break_end'] >= mission_dt and brk['break_start'] < mission_dt:
                                miss_time = round((mission_dt - brk['break_start']).seconds / 3600, 2)
                                miss_start, miss_end = brk['break_start'], mission_dt

                            if miss_time:
                                miss_dic = {
                                    'is_official': True,
                                    'official_id': mission.id,
                                    'total_mission_hours': miss_time,
                                    'break_duration': trans.break_duration - miss_time,
                                }
                                if state != 'check':
                                    trans.update(miss_dic)
                                if state is not None:
                                    feedback.append(
                                        {'mission_id': mission.id, 'miss_start': miss_start, 'miss_end': miss_end,
                                        'type': 'break'}
                                    )
        trans.update_absence_status(trans)
        if state is not None:
            return feedback

    @api.model
    def process_attendance_scheduler_queue(self, attendance_date=None, attendance_employee=None, send_email=False):
        at_device = self.env['ir.module.module'].sudo().search([('state', '=', 'installed'),
                                                                ('name', '=', 'to_attendance_device_custom')]) \
                    and True or False
        attendance_pool = self.env['attendance.attendance']
        # #remove today from not to day in attendance
        today = datetime.now().date()
        not_today = attendance_pool.search([('is_today', '=', True), ('action_date', '<', today)])
        if not_today:
           for att in not_today:
               att._compute_is_today()
        # #end
        low_date = (datetime.utcnow()).date() if not attendance_date else attendance_date
        if isinstance(low_date, datetime):
            low_date = low_date.date()
        if low_date:
            module = self.env['ir.module.module'].sudo()
            official_mission_module = module.search(
                [('state', '=', 'installed'), ('name', '=', 'exp_official_mission')])
            personal_permission_module = module.search(
                [('state', '=', 'installed'), ('name', '=', 'employee_requests')])
            holidays_module = module.search([('state', '=', 'installed'), ('name', '=', 'hr_holidays_public')])
            if holidays_module:
                holiday_pool = self.env['hr.holidays']
            transactions = self.env['hr.attendance.transaction']

            day_item = low_date
            weekday = day_item.strftime('%A').lower()
            prv_day_item = day_item - timedelta(1)
            prv_weekday = prv_day_item.strftime('%A').lower()
            nxt_day_item = day_item + timedelta(1)
            nxt_weekday = nxt_day_item.strftime('%A').lower()
            if holidays_module:
                public = self.env['hr.holiday.officials'].search([('active', '=', True), ('state', '=', 'confirm'),
                                                                  ('date_from', '<=', day_item),
                                                                  ('date_to', '>=', day_item)])
            employee_list = self.env['hr.employee'].search([('state', '=', 'open')]) \
                if not attendance_employee else attendance_employee

            for employee in employee_list:
                hire = employee.contract_id.hiring_date if employee.contract_id.hiring_date else employee.contract_id.date_start
                if not hire: 
                    continue
                datetime_object = datetime.strptime(str(hire), '%Y-%m-%d').date()
                if employee.contract_id.state != 'end_contract' and datetime_object <= day_item:
                    if datetime_object == day_item:
                        day_item = datetime_object
                    else:
                        day_item = low_date
                    check_trans = self.env['hr.attendance.transaction'].search([
                                           ('date', '=', day_item), ('employee_id', '=', employee.id)])
                    emp_calendar = check_trans and check_trans[0].calendar_id and check_trans[0].calendar_id \
                                   or employee.resource_calendar_id
                    if emp_calendar.is_full_day:
                        attendance_dt = datetime.combine(day_item, datetime.min.time())
                        day_times, planed_hours = self.get_day_timing(emp_calendar, weekday, day_item)
                        one_min_in, one_max_in = day_times[0], day_times[1]
                        one_min_out, one_max_out = day_times[2], day_times[3]
                        one_min_in_dt = self.convert_float_2time(one_min_in, attendance_dt)
                        domain = [('employee_id', '=', employee.id)]
                        if emp_calendar.noke and not self.one_day_noke(emp_calendar):
                            one_max_in_dt = self.noke_time_2date('one_max_in', attendance_dt, day_times)
                            one_min_out_dt = self.noke_time_2date('one_min_out', attendance_dt, day_times)
                            one_max_out_dt = self.noke_time_2date('one_max_out', attendance_dt, day_times)

                            one_max_out_st = fields.Datetime.to_string(one_max_out_dt)
                            domain += [('action_date', 'in', (day_item, day_item + timedelta(1)))]
                            prv_day_times = self.get_day_timing(emp_calendar, prv_weekday, prv_day_item)[0]
                            prv_day_min_out = self.noke_time_2date('one_min_out', attendance_dt - timedelta(1),
                                                                   prv_day_times)
                            prv_day_max_out = self.noke_time_2date('one_max_out', attendance_dt - timedelta(1),
                                                                   prv_day_times)
                            nxt_day_times = self.get_day_timing(emp_calendar, nxt_weekday, nxt_day_item)[0]
                            nxt_day_min_in = self.convert_float_2time(nxt_day_times[0], attendance_dt + timedelta(1))
                            one_in_dom = domain.copy() + [('action', '=', 'sign_in'),
                                                          ('name', '<=', one_max_out_st),
                                                          ('name', '>', str(prv_day_max_out))]
                            out_dom = domain.copy() + [('action', '=', 'sign_out'),
                                                       ('name', '>', str(prv_day_max_out)),
                                                       ('name', '<', str(nxt_day_min_in))]
                        else:
                            one_max_in_dt = self.convert_float_2time(one_max_in, attendance_dt)
                            one_min_out_dt = self.convert_float_2time(one_min_out, attendance_dt)
                            one_max_out_dt = self.convert_float_2time(one_max_out, attendance_dt)
                            one_max_out_st = fields.Datetime.to_string(one_max_out_dt)
                            domain += [('action_date', '=', day_item)]
                            one_in_dom = domain.copy() + [('action', '=', 'sign_in'), ('name', '<=', one_max_out_st)]
                            out_dom = domain.copy() + [('action', '=', 'sign_out')]
                        signs_out = attendance_pool.search(out_dom, order="name asc")
                        one_signs_in = attendance_pool.search(one_in_dom, order="name asc")
                        base_dict = {'date': day_item, 'employee_id': employee.id, 'calendar_id': emp_calendar.id,
                                     'attending_type': 'in_cal'}
                        one_dict, shift_one_extra, force_create = {}, {}, True
                        exist_trans = transactions.search([('date', '=', day_item), ('employee_id', '=', employee.id)])
                        if not (not one_signs_in and not signs_out):
                            if one_signs_in:
                                signs_out = signs_out.filtered(
                                    lambda s: s.name >= one_signs_in[0].name) or attendance_pool
                            one_dict = self.prepare_shift(at_device, attendance_dt, one_signs_in, signs_out,
                                                          one_min_in_dt,
                                                          one_max_in_dt, one_min_out_dt, one_max_out_dt,
                                                          base_dict.copy())
                            if one_dict:
                                shift_one = one_dict['shift']
                                shift_one['sequence'] = 1
                                one_breaks = one_dict.get('break_periods', {})
                                one_in_dt, one_out_dt = shift_one['sign_in_dt'], shift_one['sign_out_dt']
                                del shift_one['sign_in_dt']
                                del shift_one['sign_out_dt']
                                if one_out_dt:
                                    signs_out = signs_out.filtered(lambda s: s.name > (one_out_dt))
                                force_create = False
                                if shift_one.get('attending_type') == 'out_cal':
                                    shift_one_extra = {'sign_in': 0.0, 'sign_out': 0.0, 'date': day_item, 'sequence': 1,
                                                       'employee_id': employee.id, 'calendar_id': emp_calendar.id,
                                                       'attending_type': 'in_cal'}
                        if force_create or not one_dict:
                            shift_one = {'sign_in': 0.0, 'sign_out': 0.0, 'date': day_item, 'employee_id': employee.id,
                                         'is_absent': True, 'calendar_id': emp_calendar.id, 'sequence': 1,
                                         'attending_type': 'in_cal'}
                            one_in_dt, one_out_dt = one_min_in_dt, one_max_out_dt
                            one_breaks = {}
                            force_create = True
                        one_exist_trans = exist_trans and exist_trans.filtered(
                            lambda t: t.sequence == 1 and t.attending_type == shift_one['attending_type']) or False
                        if one_exist_trans:
                            one_exist_trans.update(shift_one)
                            one_trans = one_exist_trans
                        else:
                            one_trans = transactions.create(shift_one)
                        if shift_one_extra:
                            onextra_exist_trans = exist_trans and \
                                                  exist_trans.filtered(
                                                      lambda
                                                          t: t.sequence == 1 and t.attending_type == 'out_cal') or False
                            if onextra_exist_trans:
                                onextra_exist_trans.update(shift_one_extra)
                            else:
                                transactions.create(shift_one_extra)
                        one_trans = exist_trans and \
                                    exist_trans.filtered(
                                        lambda t: t.sequence == 1 and t.attending_type == 'in_cal') or one_trans
                        one_extra_dlt = exist_trans and \
                                        exist_trans.filtered(
                                            lambda t: t.sequence == 1 and t.attending_type == 'out_cal') or False
                        if one_extra_dlt and not shift_one_extra: one_extra_dlt.unlink()
                        one_trans.set_lateness_and_exit(one_trans)
                        if personal_permission_module:
                            if one_trans.temp_lateness or one_trans.temp_exit or one_breaks \
                                    or one_trans.sign_in == 0.0 or one_trans.sign_out == 0.0:
                                one_perm = self.manage_permission(one_trans.id, one_min_in_dt, one_max_out_dt,
                                                                  one_in_dt, one_out_dt, one_breaks, 'inform')
                        if official_mission_module:
                            self.manage_mission(one_trans.id, one_min_in_dt, one_max_out_dt, one_in_dt, one_out_dt,
                                                one_breaks)
                    else:
                        day_times, planed_hours = self.get_day_timing(emp_calendar, weekday, day_item)
                        one_min_in, one_max_in = day_times[0], day_times[1]
                        one_min_out, one_max_out = day_times[2], day_times[3]
                        two_min_in, two_max_in = day_times[4], day_times[5]
                        two_min_out, two_max_out = day_times[6], day_times[7]
                        attendance_dt = datetime.combine(day_item, datetime.min.time())
                        one_min_in_dt = self.convert_float_2time(one_min_in, attendance_dt)
                        domain = [('employee_id', '=', employee.id)]
                        if emp_calendar.noke and not self.one_day_noke(emp_calendar):
                            one_max_in_dt = self.noke_time_2date('one_max_in', attendance_dt, day_times)
                            one_min_out_dt = self.noke_time_2date('one_min_out', attendance_dt, day_times)
                            one_max_out_dt = self.noke_time_2date('one_max_out', attendance_dt, day_times)
                            two_min_in_dt = self.noke_time_2date('two_min_in', attendance_dt, day_times)
                            two_max_in_dt = self.noke_time_2date('two_max_in', attendance_dt, day_times)
                            two_min_out_dt = self.noke_time_2date('two_min_out', attendance_dt, day_times)
                            two_max_out_dt = self.noke_time_2date('two_max_out', attendance_dt, day_times)
                            one_max_out_st = fields.Datetime.to_string(one_max_out_dt)
                            domain += [('action_date', 'in', (day_item, day_item + timedelta(1)))]
                            prv_day_times = self.get_day_timing(emp_calendar, prv_weekday, prv_day_item)[0]
                            prv_day_min_out = self.noke_time_2date('two_min_out', attendance_dt - timedelta(1),
                                                                   prv_day_times)
                            prv_day_max_out = self.noke_time_2date('two_max_out', attendance_dt - timedelta(1),
                                                                   prv_day_times)
                            nxt_day_times = self.get_day_timing(emp_calendar, nxt_weekday, nxt_day_item)[0]
                            nxt_day_min_in = self.convert_float_2time(nxt_day_times[0], attendance_dt + timedelta(1))
                            one_in_dom = domain.copy() + [('action', '=', 'sign_in'),
                                                          ('name', '<=', one_max_out_st),
                                                          ('name', '>', str(prv_day_min_out))]
                            two_in_dom = domain.copy() + [('action', '=', 'sign_in'),
                                                          ('name', '>', one_max_out_st),
                                                          ('name', '<=', str(two_min_out_dt))]
                            out_dom = domain.copy() + [('action', '=', 'sign_out'),
                                                       ('name', '>', str(prv_day_max_out)),
                                                       ('name', '<', str(nxt_day_min_in))]
                        else:
                            one_max_in_dt = self.convert_float_2time(one_max_in, attendance_dt)
                            one_min_out_dt = self.convert_float_2time(one_min_out, attendance_dt)
                            one_max_out_dt = self.convert_float_2time(one_max_out, attendance_dt)
                            two_min_in_dt = self.convert_float_2time(two_min_in, attendance_dt)
                            two_max_in_dt = self.convert_float_2time(two_max_in, attendance_dt)
                            two_min_out_dt = self.convert_float_2time(two_min_out, attendance_dt)
                            two_max_out_dt = self.convert_float_2time(two_max_out, attendance_dt)
                            one_max_out_st = fields.Datetime.to_string(one_max_out_dt)
                            domain += [('action_date', '=', day_item)]
                            one_in_dom = domain.copy() + [('action', '=', 'sign_in'), ('name', '<', one_max_out_st)]
                            two_in_dom = domain.copy() + [('action', '=', 'sign_in'), ('name', '>=', one_max_out_st)]
                            out_dom = domain.copy() + [('action', '=', 'sign_out')]

                        signs_out = attendance_pool.search(out_dom, order="name asc")
                        one_signs_in = attendance_pool.search(one_in_dom, order="name asc")
                        two_signs_in = attendance_pool.search(two_in_dom, order="name asc")
                        base_dict = {'date': day_item, 'employee_id': employee.id, 'calendar_id': emp_calendar.id,
                                     'attending_type': 'in_cal'}
                        one_dict, two_dict, shift_one_extra, shift_two_extra, force_create = {}, {}, {}, {}, True
                        exist_trans = transactions.search([('date', '=', day_item), ('employee_id', '=', employee.id)])
                        if not (not one_signs_in and not signs_out):
                            if one_signs_in:
                                signs_out = signs_out.filtered(
                                    lambda s: s.name > one_signs_in[0].name) or attendance_pool
                            one_dict = self.prepare_shift(at_device, attendance_dt, one_signs_in, signs_out,
                                                          one_min_in_dt,
                                                          one_max_in_dt, one_min_out_dt, one_max_out_dt,
                                                          base_dict.copy(),
                                                          two_min_in_dt)
                            if one_dict:
                                shift_one = one_dict['shift']
                                shift_one['sequence'] = 1
                                one_breaks = one_dict.get('break_periods', {})
                                one_in_dt, one_out_dt = shift_one['sign_in_dt'], shift_one['sign_out_dt']
                                del shift_one['sign_in_dt']
                                del shift_one['sign_out_dt']
                                if one_out_dt: signs_out = signs_out.filtered(lambda s: str(s.name) > str(one_out_dt))
                                force_create = False
                                if shift_one.get('attending_type') == 'out_cal':
                                    shift_one_extra = {'sign_in': 0.0, 'sign_out': 0.0, 'date': day_item, 'sequence': 1,
                                                       'employee_id': employee.id, 'calendar_id': emp_calendar.id,
                                                       'attending_type': 'in_cal'}
                        if force_create or not one_dict:
                            shift_one = {'sign_in': 0.0, 'sign_out': 0.0, 'date': day_item, 'employee_id': employee.id,
                                         'is_absent': True, 'calendar_id': emp_calendar.id, 'sequence': 1,
                                         'attending_type': 'in_cal'}
                            one_in_dt, one_out_dt = one_min_in_dt, one_max_out_dt
                            one_breaks = {}
                            force_create = True
                        if not (not two_signs_in and not signs_out):
                            two_dict = self.prepare_shift(at_device, attendance_dt, two_signs_in, signs_out,
                                                          two_min_in_dt,
                                                          two_max_in_dt, two_min_out_dt, two_max_out_dt, base_dict)
                            if two_signs_in:
                                signs_out = signs_out.filtered(
                                    lambda s: s.name > two_signs_in[0].name) or attendance_pool
                            if two_dict:
                                shift_two = two_dict['shift']
                                shift_two['sequence'] = 2
                                two_breaks = two_dict.get('break_periods', {})
                                two_in_dt, two_out_dt = shift_two['sign_in_dt'], shift_two['sign_out_dt']
                                del shift_two['sign_in_dt']
                                del shift_two['sign_out_dt']
                                force_create = False
                                if shift_two.get('attending_type') == 'out_cal':
                                    shift_two_extra = {'sign_in': 0.0, 'sign_out': 0.0, 'date': day_item, 'sequence': 2,
                                                       'employee_id': employee.id, 'calendar_id': emp_calendar.id,
                                                       'attending_type': 'in_cal'}
                        if force_create or not two_dict:
                            shift_two = {'sign_in': 0.0, 'sign_out': 0.0, 'date': day_item, 'employee_id': employee.id,
                                         'calendar_id': emp_calendar.id, 'sequence': 2, 'attending_type': 'in_cal'}
                            two_in_dt, two_out_dt = two_min_in_dt, two_max_out_dt
                            two_breaks = {}
                            force_create = True
                        if one_dict and one_dict['creep']:
                            # TODO: review cases not to be minus
                            shift_one['official_hours'] += one_dict['creep']
                            if two_dict and shift_two['temp_lateness'] and shift_two.get('attending_type') == 'in_cal':
                                shift_two['break_duration'] += shift_two['temp_lateness'] - one_dict['creep']
                                # shift_two['temp_lateness'] = 0.0
                                shift_two['carried_hours'] = one_dict['creep']
                        one_exist_trans = exist_trans and exist_trans.filtered(
                            lambda t: t.sequence == 1 and t.attending_type == shift_one['attending_type']) or False
                        if one_exist_trans:
                            one_exist_trans.update(shift_one)
                            one_trans = one_exist_trans
                        else:
                            one_trans = transactions.create(shift_one)
                        two_exist_trans = exist_trans and exist_trans.filtered(
                            lambda t: t.sequence == 2 and t.attending_type == shift_two['attending_type']) or False
                        if two_exist_trans:
                            two_exist_trans.update(shift_two)
                            two_trans = two_exist_trans
                        else:
                            two_trans = transactions.create(shift_two)
                        if shift_one_extra:
                            onextra_exist_trans = exist_trans and \
                                                  exist_trans.filtered(
                                                      lambda
                                                          t: t.sequence == 1 and t.attending_type == 'out_cal') or False
                            if onextra_exist_trans:
                                onextra_exist_trans.update(shift_one_extra)
                            else:
                                transactions.create(shift_one_extra)
                        if shift_two_extra:
                            twoxtra_exist_trans = exist_trans and \
                                                  exist_trans.filtered(
                                                      lambda
                                                          t: t.sequence == 2 and t.attending_type == 'in_cal') or False
                            if twoxtra_exist_trans:
                                twoxtra_exist_trans.update(shift_two_extra)
                            else:
                                transactions.create(shift_two_extra)
                        one_trans = exist_trans and \
                                    exist_trans.filtered(
                                        lambda t: t.sequence == 1 and t.attending_type == 'in_cal') or one_trans
                        one_extra_dlt = exist_trans and \
                                        exist_trans.filtered(
                                            lambda t: t.sequence == 1 and t.attending_type == 'out_cal') or False
                        if one_extra_dlt and not shift_one_extra: one_extra_dlt.unlink()
                        two_trans = exist_trans and \
                                    exist_trans.filtered(
                                        lambda t: t.sequence == 2 and t.attending_type == 'in_cal') or two_trans
                        two_extra_dlt = exist_trans and \
                                        exist_trans.filtered(
                                            lambda t: t.sequence == 2 and t.attending_type == 'out_cal') or False
                        if two_extra_dlt and not shift_two_extra: two_extra_dlt.unlink()
                        if personal_permission_module:
                            if one_trans.temp_lateness or one_trans.temp_exit or one_breaks \
                                    or one_trans.sign_in == 0.0 or one_trans.sign_out == 0.0:
                                
                                one_perm = self.manage_permission(one_trans.id, one_min_in_dt, one_max_out_dt,
                                                                  one_in_dt, one_out_dt, one_breaks, 'inform')
                            if two_trans.temp_lateness or two_trans.temp_exit or two_breaks \
                                    or two_trans.sign_in == 0.0 or two_trans.sign_out == 0.0:
                                
                                two_perm = self.manage_permission(two_trans.id, two_min_in_dt, two_max_out_dt,
                                                                  two_in_dt, two_out_dt, two_breaks, 'inform')
                        if official_mission_module:
                            self.manage_mission(one_trans.id, one_min_in_dt, one_max_out_dt, one_in_dt, one_out_dt,
                                                one_breaks)
                            self.manage_mission(two_trans.id, two_min_in_dt, two_max_out_dt, two_in_dt, two_out_dt,
                                                two_breaks)

                    off_list = []
                    day_trans = transactions.search([('date', '=', day_item), ('employee_id', '=', employee.id)])
                    weekend_days = emp_calendar.is_full_day and emp_calendar.full_day_off or emp_calendar.shift_day_off
                    if weekend_days:
                        for day in weekend_days:
                            create = (datetime.strptime(str(day.create_date.strftime(DATETIME_FORMAT)),
                                                        DATETIME_FORMAT) + timedelta(hours=3)).date()
                            off_list.append(day.name.lower())
                            if day.name.lower() == day_item.strftime('%A').lower():
                                for trans in day_trans:
                                    if emp_calendar.noke and create <= datetime.strptime(str(trans.date),
                                                                                         "%Y-%m-%d").date():
                                        trans.update({'public_holiday': True})
                                    else:
                                        if not emp_calendar.is_full_day:
                                            if day.shift == 'one' and trans.sequence == 1:
                                                trans.update({'public_holiday': True})
                                            elif day.shift == 'tow' and trans.sequence == 2:
                                                trans.update({'public_holiday': True})
                                            elif day.shift == 'both':
                                                trans.update({'public_holiday': True})
                                        else:
                                            trans.update({'public_holiday': True})

                            else:
                                for trans in day_trans:
                                    if trans.public_holiday and not trans.public_holiday_id:
                                        trans_wkd = datetime.strptime(str(trans.date), "%Y-%m-%d")
                                        if trans_wkd.strftime(
                                                '%A').lower() not in off_list and not trans.public_holiday_id:
                                            if emp_calendar.noke:
                                                pass
                                            else:
                                                trans.update({'public_holiday': False})
                    else:
                        for trans in day_trans:
                            if trans.public_holiday and not trans.public_holiday_id:
                                if emp_calendar.noke:
                                    pass
                                else:
                                    trans.update({'public_holiday': False})
                    if holidays_module:
                        ptrans = transactions.search([('date', '=', day_item), ('employee_id', '=', employee.id)])
                        public_trans = ptrans.filtered(lambda pk: pk.public_holiday_id)
                        if public:
                            for p in public:
                                for trans in ptrans:
                                    if p.date_from <= trans.date and p.date_to >= trans.date:
                                        trans.update({'public_holiday': True, 'public_holiday_id': p.id})
                        elif public_trans and not public:
                            for trans in public_trans:
                                if trans.public_holiday:
                                    trans.update({'public_holiday': False, 'public_holiday_id': False})
                        emp_stateless_leaves = holiday_pool.search([('employee_id', '=', employee.id),
                                                                    ('type', '!=', 'add'),
                                                                    ('date_from', '<=', str(day_item)),
                                                                    ('date_to', '>=', str(day_item))])
                        leaves = emp_stateless_leaves.filtered(lambda l: l.state == 'validate1')
                        cancelled_leaves = emp_stateless_leaves.filtered(lambda l: l.state != 'validate1')
                        if leaves:
                            for lev in leaves:
                                if lev.date_from and lev.date_to \
                                        and fields.Date.from_string(lev.date_from).strftime('%Y-%m-%d') \
                                        <= str(day_item) <= str(lev.date_to):
                                    for trans in ptrans:
                                        lv_hours = trans.calendar_id.is_full_day and trans.calendar_id.working_hours \
                                                   or trans.sequence == 1 and trans.calendar_id.shift_one_working_hours \
                                                   or trans.sequence == 2 and trans.calendar_id.shift_two_working_hours
                                        trans.update({
                                            'normal_leave': True,
                                            'leave_id': lev.id,
                                            'total_leave_hours': lv_hours,
                                            'break_duration': 0.0,
                                            'public_holiday': False,
                                            'is_absent': False,
                                            'total_absent_hours': 0.0})
                        elif cancelled_leaves:
                            for trans in ptrans:
                                for lev in cancelled_leaves:
                                    if lev.id == trans.leave_id.id:
                                        trans.update(
                                            {'normal_leave': False, 'leave_id': False, 'total_leave_hours': 0.0})
                    for tr in day_trans:
                        if tr.attending_type == 'in_cal':
                            if tr.sequence == 1:
                                tr.plan_hours = planed_hours['one']
                            elif tr.sequence == 2:
                                tr.plan_hours = planed_hours['two']
                        
                        tr.update_absence_status(tr)
                        
                        # tr.update_absence_status(tr)
                    # for employee in employee_list:
                    #     emp_tr = day_trans.filtered(lambda t: t.employee_id == employee)
                    #     template = self.env.ref('attendences.email_template_transaction_state')
                    #     if len(day_trans.filtered(lambda t: t.employee_id == employee)) == 1:
                    #         if emp_tr.is_absent:
                    #             msg = "is absent"
                    #             body = """<div>
                    #             <p>Dear %s ,</p>
                    #             <p> Greetings, we kindly inform you that employee %s %s on %s
                    #             <br/>
                    #             <p>Best regards,</p>
                    #              """ % (employee.parent_id.name, employee.name, msg, emp_tr.date)
                    #             template.write({'body_html': body})
                    #             template.send_mail(emp_tr.id, force_send=True, raise_exception=False)
                    #         if emp_tr.approve_lateness:
                    #             msg = "is late"
                    #             body = """<div>
                    #             <p>Dear %s ,</p>
                    #             <p> Greetings, we kindly inform you that employee %s %s on %s
                    #             <br/>
                    #              <p>Best regards,</p>
                    #              """ % (employee.parent_id.name, employee.name, msg, emp_tr.date)
                    #             template.write({'body_html': body})
                    #             template.send_mail(emp_tr.id, force_send=True, raise_exception=False)
                    #         if emp_tr.approve_exit_out:
                    #             msg = "is exit out"
                    #             body = """<div>
                    #             <p>Dear %s ,</p>
                    #             <p> Greetings, we kindly inform you that employee %s %s on %s
                    #             <br/>
                    #             <p>Best regards,</p>
                    #              """ % (employee.parent_id.name, employee.name, msg, emp_tr.date)
                    #             template.write({'body_html': body})
                    #             template.send_mail(emp_tr.id, force_send=True, raise_exception=False)
                    #     else:
                    #         if all(tr.is_absent for tr in emp_tr):
                    #             if emp_tr and emp_tr[0]:
                    #                 msg = "is absent"
                    #                 body = """<div>
                    #                 <p>Dear %s ,</p>
                    #                 <p> Greetings, we kindly inform you that employee %s %s on %s
                    #                 <br/>
                    #                 <p>Best regards,</p>
                    #                 """ % (employee.parent_id.name, employee.name, msg, emp_tr[0].date)
                    #                 template.write({'body_html': body})
                    #                 template.send_mail(emp_tr[0].id, force_send=True, raise_exception=False)
                    #         if all(tr.approve_lateness for tr in emp_tr):
                    #             if emp_tr and emp_tr[0]:
                    #                 msg = "is later"
                    #                 body = """<div>
                    #                 <p>Dear %s ,</p>
                    #                 <p> Greetings, we kindly inform you that employee %s %s on %s
                    #                 <br/>
                    #                 <p>Best regards,</p>
                    #                 """ % (employee.parent_id.name, employee.name, msg, emp_tr[0].date)
                    #                 template.write({'body_html': body})
                    #                 template.send_mail(emp_tr[0].id, force_send=True, raise_exception=False)
                    #         if all(tr.approve_exit_out for tr in emp_tr):
                    #             if emp_tr and emp_tr[0]:
                    #                 msg = "is exit out"
                    #                 body = """<div>
                    #                 <p>Dear %s ,</p>
                    #                 <p> Greetings, we kindly inform you that employee %s %s on  %s
                    #                 <br/>
                    #                 <p>Best regards,</p>
                    #                 """ % (employee.parent_id.name, employee.name, msg, emp_tr[0].date)
                    #                 template.write({'body_html': body})
                    #                 template.send_mail(emp_tr[0].id, force_send=True, raise_exception=False)

    def get_user_id(self):
        employee_id = self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)
        if employee_id:
            return employee_id.id
        else:
            return False

    @api.model
    def send_lateness_notifications(self):
        today = datetime.now().date()
        yesterday = today - timedelta(days=1)
        yesterday_records = self.env['hr.attendance.transaction'].search([
                                    ('date', '=', yesterday), ('employee_id.finger_print', '=', True)])
        
        email_values = {}
        yesterday_template_id = self.env.ref('attendances.attendance_notification_email_template').id
        for record in yesterday_records:
            if (record.lateness > 0 or
                    record.early_exit > 0 or
                    record.is_absent or
                    (record.sign_out == 0 and record.sign_in != 0) or
                    (record.sign_out != 0 and record.sign_in == 0)):

                if yesterday_template_id:
                    template = self.env['mail.template'].browse(yesterday_template_id)
                    template.send_mail(record.id, force_send=True)

        """ Notification Today No Sign In On time """
        today_records = self.env['hr.attendance.transaction'].search([
                                     ('date', '=', today), ('employee_id.finger_print', '=', True),
                                     ('public_holiday', '=', False), ('normal_leave', '=', False),
                                     ('is_official', '=', False)])
        today_template_id = self.env.ref('attendances.attendance_notification_today_sign_in').id
        for item in today_records:
            if item.sign_in == 0:
               if today_template_id:
                    template = item.env['mail.template'].browse(today_template_id)
                    template.send_mail(item.id, force_send=True)
    # @api.multi
    # def unlink(self):
    #     raise UserError(_('Sorry, you can not delete an attendance transaction manually.'))
    #     return super(HrAttendanceTransactions, self).unlink()
