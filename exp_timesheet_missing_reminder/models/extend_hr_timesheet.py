# -*- coding: utf-8 -*-
import datetime
from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta
from odoo import models, fields, api, _, exceptions
from dateutil import relativedelta
from time import gmtime


class HrAttendances(models.Model):
    _inherit = 'resource.calendar'

    check_timesheet = fields.Boolean('Check Timesheet', default=False)

    timesheet_day_before = fields.Integer(string='Timesheet Days Before', default=0,
                                          help='To Request Timesheet for Previous days Not Exceed these Days')
    timesheet_hour_before = fields.Integer(string='Timesheet Hours Before', default=0,
                                           help='To Request Timesheet for Previous days, Not to Exceed This Hour')
    exc_user_id = fields.Many2one(comodel_name="res.users", string='User Exception',
                                  help='This User To Request Timesheet for Exception all Rules')

    @api.constrains('timesheet_day_before', 'timesheet_hour_before')
    def check_date(self):
        if self.timesheet_day_before < 0:
            raise exceptions.Warning(_('Sorry, The Timesheet to Days Before It must be greater than zero.'))
        if self.timesheet_hour_before < 0:
            raise exceptions.Warning(_('Sorry, The Timesheet to Hours Before It must be greater than zero.'))

        if self.timesheet_hour_before > 24:
            raise exceptions.Warning(_('Sorry, The Timesheet to Hours Before It must be less than 24 Hour.'))


class AccountAnalyticLine(models.Model):
    _inherit = 'account.analytic.line'

    @api.constrains('date')
    def check_date(self):
        for each in self:
            emp_calender = each.employee_id.resource_calendar_id
            timesheet_user = emp_calender.exc_user_id.id
            chick_sheet = emp_calender.check_timesheet
            number_day_befor = emp_calender.timesheet_day_before
            number_hour_befor = emp_calender.timesheet_hour_before
            line_date = fields.Date.from_string(each.date)
            yesterday = date.today() - relativedelta.relativedelta(days=number_day_befor)
            hour = gmtime().tm_hour + 3
            if each.sheet_id:
                startdate = datetime.strptime(str(each.sheet_id.date_start), "%Y-%m-%d").date()
                enddate = datetime.strptime(str(each.sheet_id.date_end), "%Y-%m-%d").date()
                if line_date < startdate or line_date > enddate:
                    raise exceptions.Warning(_('Sorry You TimeSheet Lines %s Not In The TimeSheet Period.') % line_date)

            if chick_sheet and timesheet_user != each.env.uid:

                full_day_off = [da.name for da in emp_calender.full_day_off]
                shift_day_off = [da.name for da in emp_calender.shift_day_off]
                day_item = date.today()
                week_day = day_item.strftime('%A').lower()
                prv_day = day_item - timedelta(1)
                prv_weekday = prv_day.strftime('%A').lower()
                line_weekday = line_date.strftime('%A').lower()
                if line_date < yesterday:
                    # in one Shift Full Day:
                    if emp_calender.is_full_day:
                        if prv_weekday not in full_day_off:
                            raise exceptions.Warning(
                                _('Sorry You Can Not Request The TimeSheet Lines %s Earlier Date.') % line_date)
                        if line_weekday not in full_day_off and line_weekday != 'thursday':
                            raise exceptions.Warning(
                                _('Sorry You Can Not Request The TimeSheet Lines %s Earlier Date.') % line_date)
                    # in tow Shift:
                    else:
                        if prv_weekday not in shift_day_off:
                            raise exceptions.Warning(
                                _('Sorry You Can Not Request The TimeSheet Lines %s Earlier Date.') % line_date)
                        if line_weekday not in shift_day_off and line_weekday != 'thursday':
                            raise exceptions.Warning(
                                _('Sorry You Can Not Request The TimeSheet Lines %s Earlier Date.') % line_date)

                if line_date == yesterday and hour > number_hour_befor and line_weekday != 'thursday':
                    raise exceptions.Warning(
                        _('Sorry You Can Not Request The TimeSheet Lines %s The Day After %s Hour') % (
                            line_date, number_hour_befor))
                if line_date > date.today():
                    raise exceptions.Warning(
                        _('Sorry You Can Not Request The TimeSheet Lines %s date in advance.') % line_date)


class ExtendHrTimesheet(models.Model):
    _inherit = 'hr_timesheet.sheet'

    def common_search_model(self, model_name, param1, param2):
        result = ''
        if model_name == 'hr.holidays':
            result = self.env[model_name].search([('date_from', '<=', param1), ('date_to', '>=', param1),
                                                  ('state', '=', 'validate1'), ('type', '=', 'remove'),
                                                  ('employee_id', '=', param2)])
        if model_name == 'hr.official.mission':
            result = self.env[model_name].search(
                [('state', '=', 'approve'), ('date_from', '<=', param1), ('date_to', '>=', param1)])
        if model_name == 'hr_timesheet.sheet':
            result = self.env[model_name].search(
                [('employee_id', '=', param2), ('date_start', '<=', param1), ('date_end', '>=', param1)])
        if model_name == 'hr.personal.permission':
            result = self.env[model_name].search(
                [('employee_id', '=', param2), ('date', '=', param1)])
        return result

    def compute_miss_hour(self, resource_id, total_work_hour, type=None, ):
        miss_hour = 0.0
        if type == 'normal':
            if resource_id.is_full_day:
                xx = resource_id.working_hours - resource_id.break_duration
            else:
                xx = resource_id.shift_one_working_hours + resource_id.shift_two_working_hours - \
                     resource_id.break_duration
            if xx > total_work_hour:
                miss_hour = xx - total_work_hour
        elif type == 'special':
            if resource_id.working_hours > total_work_hour:
                miss_hour = resource_id.working_hours - total_work_hour
        return miss_hour

    def get_common_data(self, type):
        today = date.today()
        date_list = []
        if type == 'day':
            template = 'exp_timesheet_missing_reminder.timesheet_daily_reminder_email_notify'
            one_day_ago = today - timedelta(days=1)
            date_list.append([str(one_day_ago), one_day_ago.strftime("%A")])
            return template, one_day_ago, one_day_ago, date_list
        elif type == 'week':
            template = 'exp_timesheet_missing_reminder.timesheet_week_reminder_email_notify'
            one_week_ago = today - timedelta(weeks=1)
            last_day_in_day = one_week_ago + timedelta(days=6)
            dt = [one_week_ago + timedelta(days=x) for x in range(7)]
            for datess in dt:
                date_list.append([str(datess), datess.strftime("%A")])
            return template, one_week_ago, last_day_in_day, date_list
        elif type == 'month':
            template = 'exp_timesheet_missing_reminder.timesheet_monthly_reminder_email_notify'
            #print('template', template)
            first = today.replace(day=1)
            #print('first',first)
            last_day_month = first - timedelta(days=1)
            #print('last_day_montht', last_day_month)
            first_day = last_day_month + timedelta(days=1)
            #print('first_day', first_day)
            delta = last_day_month - first_day
            #print('delta', delta)
            dt = [first_day + timedelta(days=x) for x in range(delta.days + 1)]
            #print('dtttt', dt)
            for datess in dt:
                date_list.append([str(datess), datess.strftime("%A")])
            #print('datess',template, first_day, last_day_month, date_list )
            return template, first_day, last_day_month, date_list

    def send_message(self, template=None, rec=None, date=[]):
        if not template:
            return
        template = self.env.ref(template, False)
        if not template:
            return
        body = """<div>
                        <p>السلام عليكم ورحمة الله</p>
                        <br/>
                        <p>  السيد\ة  %s  مع التحية</p>
                        <br/>
                        <p> تقرير الأعمال اليومي الخاص بكم في النظام لم يغط  الأوقات المطلوبة منكم حسب الجدول التالي:

، نأمل إبداء الأسباب خلال 
يوم واحد فقط للنظر فيها، وفي حال لم ترسل الأسباب أو أرسلت ولم تكن مقنعة نظاما، سيتم خصم ساعات الغياب من راتبك الشهري.
إن عدم تغطية الأوقات الفعلية لكم بدون أسباب مقبولة منكم هو تقصير تستحقون عليه الإنذار. </p>
                        </div>
                        <center>
                          <table style="margin-top:30px;color:#666666;border: 1px solid black">
                                <thead>
                                    <tr style="color:#9A6C8E; font-size:12px;border: 1px solid black">
                                        <th style="border: 1px solid gray" text-align:right" align="center">الساعات</th>
                                        <th style="border: 1px solid gray" text-align:right" align="center">التاريخ</th>
                                        <th style="border: 1px solid gray" text-align:right;" align="center">الايام</th>
                                    </tr>
                                </thead>
                                <tbody>
                                %% for line in %s:
                                    <tr style="border: 1px solid gray">
                                     <td style="padding: 20px;margin:5px;border: 1px solid gray" align="left">
                                                      ${line[2]}
                                                  </td>
                                        <td style="padding: 20px;margin:5px;border: 1px solid gray" align="left">
                                            ${line[0]}
                                        </td>
                                        <td style="padding: 20px;margin:5px;border: 1px solid gray" align="right">
                                        ${line[1]}
                                        </td>
                                    </tr>
                                %% endfor
                                </tbody>
                            </table>
                            </center>
                        """ % (rec.name, date)
        template.write({'email_to': rec.work_email, 'email_cc': rec.parent_id.work_email, 'body_html': body})
        template.send_mail(rec.id, force_send=True, raise_exception=False)

    def action_send_late_email(self, type):
        #print('type', type)
        template, start_date, last_date, date_list = self.get_common_data(type)
        #print('ssssssss', template, start_date, last_date, date_list)
        final_employee_date = {}
        employees = self.env['hr.employee'].search([('state', '=', 'open'), ('skipp_timesheet_reminder', '=', False)])
        #print('employees', employees)
        for emp in employees:
            employee_day_of = []
            employee_spcial_day = []
            for special_day in emp.resource_calendar_id.special_days:
                employee_spcial_day.append(special_day.name)
            for day_off in emp.resource_calendar_id.full_day_off:
                employee_day_of.append(day_off.name)
            emp_calender = emp.resource_calendar_id
            for day in date_list:
                if day[1].lower() not in employee_day_of:
                    employee_attendance = self.env['hr.attendance.transaction'].search(
                        [('employee_id', '=', emp.id), ('date', '=', day[0])])
                    #print('emp att', employee_attendance)
                    if employee_attendance:
                        employee_spcial_day = []
                        employee_day_of = []
                        for special_day in employee_attendance.calendar_id.special_days:
                            employee_spcial_day.append(special_day.name)
                        for day_off in employee_attendance.calendar_id.full_day_off:
                            employee_day_of.append(day_off.name)
                        emp_calender = employee_attendance.calendar_id
                    holiday_officials_ids = self.env['hr.holiday.officials'].search(
                        [('date_from', '<=', day[0]), ('date_to', '>=', day[0]), ('state', '=', 'confirm')])
                    if not holiday_officials_ids:
                        holidays_id = self.common_search_model('hr.holidays', day[0], emp.id)
                        if not holidays_id:
                            mission_id = self.common_search_model('hr.official.mission', day[0], '')
                            mission = mission_id.filtered(lambda r: r.mission_type.duration_type == 'days')
                            mission_employee = mission.employee_ids.filtered(
                                lambda r: r.employee_id.id == emp.id and r.date_from <= r.date_to)
                            if not mission_employee:
                                day_type = 'normal'
                                calender = emp_calender
                                actual_hour = emp_calender.working_hours - emp_calender.break_duration
                                if not emp_calender.is_full_day:
                                    actual_hour = emp_calender.shift_one_working_hours + \
                                                  emp_calender.shift_two_working_hours - emp_calender.break_duration
                                if day[1].lower() in employee_spcial_day:
                                    day_type = 'special'
                                    spacial_day = emp_calender.special_days.filtered(lambda r: r.name == day[1].lower())
                                    calender = spacial_day
                                    actual_hour = spacial_day.working_hours
                                mission_hour = 0.0
                                permission_hour = 0.0
                                mission_id = self.env['hr.official.mission'].search(
                                    [('state', '=', 'approve'), ('date', '<=', day[0]), ('date', '>=', day[0])])
                                mission = mission_id.filtered(lambda r: r.mission_type.duration_type == 'hours')
                                mission_employee = mission.employee_ids.filtered(
                                    lambda r: r.employee_id.id == emp.id)
                                if mission_employee:
                                    mission_hour = sum(mission_employee.mapped('hours'))
                                permission_ids = self.common_search_model('hr.personal.permission', day[0], emp.id)
                                if permission_ids:
                                    permission_hour = sum(permission_ids.mapped('duration'))
                                timesheet_id = self.common_search_model('hr_timesheet.sheet', day[0], emp.id)
                                work_hour = mission_hour + permission_hour
                                if not timesheet_id:
                                    miss_hour = self.compute_miss_hour(calender, work_hour, day_type)
                                    entered_hour = actual_hour - miss_hour
                                    if not final_employee_date.get(emp.id):
                                        final_employee_date[emp.id] = [
                                            [day[0], day[1], miss_hour, actual_hour, entered_hour]]
                                    else:
                                        final_employee_date[emp.id].append(
                                            [day[0], day[1], miss_hour, actual_hour, entered_hour])
                                else:
                                    x = timesheet_id.timesheet_ids.filtered(lambda r: r.date == day[0])
                                    if not x:
                                        miss_hour = self.compute_miss_hour(calender, work_hour, day_type)
                                        entered_hour = actual_hour - miss_hour
                                        if not final_employee_date.get(emp.id):
                                            final_employee_date[emp.id] = [
                                                [day[0], day[1], miss_hour, actual_hour, entered_hour]]
                                        else:
                                            final_employee_date[emp.id].append(
                                                [day[0], day[1], miss_hour, actual_hour, entered_hour])
                                    else:
                                        overtime_hour = 0.0
                                        timesheet_hour = sum(x.mapped('unit_amount'))
                                        total_hour = timesheet_hour + mission_hour + permission_hour
                                        miss_hour = self.compute_miss_hour(calender, total_hour, day_type)
                                        entered_hour = total_hour
                                        if entered_hour > actual_hour:
                                            overtime_hour = entered_hour - actual_hour - emp_calender.break_duration
                                        if total_hour < actual_hour:
                                            if not final_employee_date.get(emp.id):
                                                final_employee_date[emp.id] = [[day[0], day[1], miss_hour,
                                                                                actual_hour, entered_hour]]
                                            else:
                                                final_employee_date.get(emp.id).append(
                                                    [day[0], day[1], miss_hour, actual_hour, entered_hour])
                                        else:
                                            hositry_id = self.env['hr.employee.history.reminder'].search(
                                                [('employee_id', '=', emp.id),
                                                 ('date', '=', day[0])])
                                            if not hositry_id:
                                                self.env['hr.employee.history.reminder'].create(
                                                    {'employee_id': emp.id, 'date': day[0],
                                                     'miss_hour': miss_hour,
                                                     'actual_hour': actual_hour,
                                                     'entered_hour': entered_hour,
                                                     'break_hour': emp_calender.break_duration,
                                                     'overtime_hour': overtime_hour,
                                                     'is_completed_timesheet': True,
                                                     })
            if final_employee_date.get(emp.id):
                for dates in final_employee_date[emp.id]:
                    hositry_id = self.env['hr.employee.history.reminder'].search([('employee_id', '=', emp.id),
                                                                                  ('date', '=', dates[0])])
                    if not hositry_id:
                        self.env['hr.employee.history.reminder'].create({'employee_id': emp.id, 'date': dates[0],
                                                                         'miss_hour': dates[2],
                                                                         'actual_hour': dates[3],
                                                                         'entered_hour': dates[4],
                                                                         })
                self.send_message(template, emp, final_employee_date[emp.id])
