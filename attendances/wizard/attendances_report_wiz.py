# -*- coding: utf-8 -*-
import pytz
from pytz import timezone
import collections
import datetime
from odoo import fields, models, _,api
from odoo.exceptions import ValidationError

WEEK_DAYS_AR = {
    0: "الاثنين",
    1: "الثلاثاء",
    2: "الاربعاء",
    3: "الخميس",
    4: "الجمعة",
    5: "السبت",
    6: "الاحد",
}

def hhmm(val):
    if not val:
        return "00:00"
    mins = float(val) * 60
    return "{0:02.0f}:{1:02.0f}".format(*divmod(mins, 60))

class AttendancesReport(models.TransientModel):
    _name = "employee.attendance.report"
    _description = "Employee Attendance Report"

    from_date = fields.Date(required=True)
    to_date = fields.Date(required=True)
    employee_ids = fields.Many2many("hr.employee", string="Employees", required=True)
    resource_calender_id = fields.Many2one("resource.calendar", string="Employee work record")
    type = fields.Selection([
        ("late", "Late and Early exit"),
        ("absent", "Absent"),
        ("employee", "Employee"),
    ], default="late", required=True)
    print_totals_only = fields.Boolean(string="Totals only (one line per employee)", default=False)

    def _payload(self):
        return {
            "ids": self.ids,
            "model": self._name,
            "form": {
                "resource_calender_id": self.resource_calender_id.id,
                "from_date": self.from_date,
                "to_date": self.to_date,
                "employee_ids": self.employee_ids.ids,
                "type": self.type,
                "print_totals_only": self.print_totals_only,
            },
        }

    # report_action = 'attendances.action_totals_only_attendance_report' if self.totals_only else 'attendances.action_general_attendance_report'
    # return self.env.ref(report_action).report_action(self)

    # def print_report(self):
    #     if not self.employee_ids:
    #         raise ValidationError(_("Please select Employees Name"))
    #     return self.env.ref("attendances.general_attendance_action_reportt").report_action(self, data=self._payload())

    def print_report(self):
        if not self.employee_ids:
            raise ValidationError(_("Please select Employees Name"))
        if self.print_totals_only == True:
            print("hhhhhhhhhhfff")
            return self.env.ref("attendances.action_totals_only_attendance_reportt").report_action(self, data=self._payload())
        else:
            return self.env.ref("attendances.action_general_attendance_reportt").report_action(self, data=self._payload())



        # return self.env.ref(report_ref).report_action(self, data=self._payload())

    def print_excel_report(self):
        if not self.employee_ids:
            raise ValidationError(_("Please select Employees Name"))
        return self.env.ref("attendances.general_attendance_action_xls").report_action(self, data=self._payload(), config=False)

class ReportAttendancePublic(models.AbstractModel):
    _name = "report.attendances.general_attendances_report_temp"
    _description = "General Attendances Report"

    def get_value(self, data):
        type = data['form']['type']
        print("ggg")
        totals_only = data["form"].get("print_totals_only", False)
        employee_ids = data['form']['employee_ids']
        resource_calender_id = data['form']['resource_calender_id']
        from_date = data['form']['from_date']
        to_date = data['form']['to_date']
        domain = [('date', '>=', from_date), ('date', '<=', to_date)]
        data = []
        final_dic = {}
        key_list = []
        total_dic = {}
        mykey = []

        resource = self.env['resource.calendar'].browse(resource_calender_id)
        if resource and not employee_ids:
            if resource.employee_ids:
                for emp in resource.employee_ids:
                    employee_ids.append(emp.id)
        # if resource_calender_id:
        #     contract_ids = self.env['hr.contract'].search([('state', '=', 'program_directory'), ('resource_calendar_id', '=', resource_calender_id)])
        #     for con in contract_ids:
        #         employee_ids.append(con.employee_id.id)
        # print(">>>>>>>>>>>>>>>>>>>>>>>employeesemployees",employees)
        if employee_ids:
            last_employee_ids = list(set(employee_ids))
            domain.append(('employee_id', 'in', last_employee_ids))
        attendance_transaction_ids = self.env['hr.attendance.transaction'].search(domain)
        employees = attendance_transaction_ids.mapped('employee_id.name')
        employee_ids = attendance_transaction_ids.mapped('employee_id')
        emp_data = []
        for emp in employee_ids:
            emp_data.append({'job': emp.sudo().job_id.name, 'department': emp.department_id.name,
                             'emp_no': emp.emp_no, 'emp_namw': emp.name})
        grouped_data = collections.defaultdict(list)
        emp_data_dict = {}
        for item in emp_data:
            grouped_data[item['emp_namw']].append(item)
        for key, value in grouped_data.items():
            emp_data_dict[key] = list(value)
        if type == 'late':
            for resource in attendance_transaction_ids:
                note = ''
                if resource.is_absent:
                    note = 'غياب'
                elif resource.public_holiday:
                    note = "عطلة رسمية"
                elif resource.official_id:
                    note = resource.official_id.mission_type.name
                elif resource.normal_leave:
                    note = resource.leave_id.holiday_status_id.name
                elif resource.approve_personal_permission:
                    note = resource.personal_permission_id.permission_type_id.name
                elif not resource.public_holiday and not resource.normal_leave:
                    if resource.sign_in and not resource.sign_out:
                        note = 'نسيان بصمة'
                    elif not resource.sign_in and resource.sign_out:
                        note = 'نسيان بصمة'

                data.append({
                    'date': resource.date,
                    'day': WEEK_DAYS_AR[resource.date.weekday()],
                    'sig_in': resource.sign_in,
                    'sig_out': resource.sign_out,
                    'lateness': resource.lateness,
                    'early_exit': resource.early_exit,
                    'extra_hours': resource.additional_hours,
                    'office_hours': resource.office_hours,
                    'note': note,
                    'department': resource.employee_id.department_id.name,
                    'employee_number': resource.employee_number,
                    'calendar_id': resource.calendar_id.name,
                    'employee_id': resource.employee_id,
                    'employee_name': resource.employee_id.name,
                })
            data = sorted(data, key=lambda d: d['date'])
            for emp in employees:
                list_cat = attendance_transaction_ids.filtered(lambda r: r.employee_id.name == emp)
                total_lateness = sum(list_cat.mapped('lateness'))
                total_early_exit = sum(list_cat.mapped('early_exit'))
                total_late_early = str(datetime.timedelta(minutes=total_early_exit + total_lateness))
                total_extra_hours = sum(list_cat.mapped('additional_hours'))
                total_extra_hours = str(datetime.timedelta(minutes=total_extra_hours))
                list_missing_punch = attendance_transaction_ids.filtered(
                    lambda r: r.employee_id.name == emp and
                              not r.public_holiday and
                              not r.normal_leave and
                              ((r.sign_in and not r.sign_out) or (not r.sign_in and r.sign_out))
                )
                total_missing_punch = len(list_missing_punch)

                list_absent = attendance_transaction_ids.filtered(
                    lambda r: r.employee_id.name == emp and r.is_absent == True)
                total_absent = len(list_absent)
                list_not_log_in = attendance_transaction_ids.filtered(
                    lambda r: r.employee_id.name == emp and r.sign_in == 0.0)
                total_not_sig_in = len(list_not_log_in)
                list_not_log_out = attendance_transaction_ids.filtered(
                    lambda r: r.employee_id.name == emp and r.sign_out == 0.0)
                list_leave = attendance_transaction_ids.filtered(
                    lambda r: r.employee_id.name == emp and (r.normal_leave or r.approve_personal_permission))
                total_not_sig_out = len(list_not_log_out)
                total_leave = len(list_leave)
                total_dic[emp] = {'total_lateness': total_lateness, 'total_early_exit': total_early_exit,
                                  "total_extra_hours": total_extra_hours, "total_late_early": total_late_early,
                                  "total_leave": total_leave, 'total_absent': total_absent,
                                  'total_not_sig_in': total_not_sig_in,
                                  'total_not_sig_out': total_not_sig_out,
                                  'total_missing_punch':total_missing_punch}
            grouped = collections.defaultdict(list)
            for item in data:
                grouped[item['employee_name']].append(item)
            for key, value in grouped.items():
                final_dic[key] = list(value)
                key_list.append(key)
            mykey = list(dict.fromkeys(key_list))
            return final_dic, mykey, total_dic, emp_data_dict

        elif type == 'absent':
            for resource in attendance_transaction_ids.filtered(lambda r: r.is_absent == True):
                data.append({
                    'date': resource.date,
                    'employee_name': resource.employee_id.name,
                    'employee_id_department_id_name': resource.employee_id.department_id.name,
                    'day': datetime.datetime.strptime(str(resource.date), '%Y-%m-%d').date().strftime('%A'),
                })
                grouped = collections.defaultdict(list)
                for item in data:
                    grouped[item['employee_id_department_id_name']].append(item)
                for key, value in grouped.items():
                    final_dic[key] = list(value)
                    key_list.append(key)
                mykey = list(dict.fromkeys(key_list))
            return final_dic, mykey, '', emp_data_dict
        elif type == 'employee':
            for emp in employees:
                list_cat = attendance_transaction_ids.filtered(lambda r: r.employee_id.name == emp)
                total_lateness = sum(list_cat.mapped('lateness'))
                total_lateness = str(datetime.timedelta(minutes=total_lateness))
                total_early_exit = sum(list_cat.mapped('early_exit'))
                total_early_exit = str(datetime.timedelta(minutes=total_early_exit))
                total_dic[emp] = {'total_lateness': total_lateness, 'total_early_exit': total_early_exit}
                key_list.append(emp)
            mykey = list(dict.fromkeys(key_list))
            return '', mykey, total_dic, emp_data_dict


    @api.model
    def _get_report_values(self, docids, data=None):
        final_dic, mykey, total, emp_data = self.get_value(data)
        start_date = data['form']['from_date']
        end_date = data['form']['to_date']
        type_ = data['form']['type']
        totals_only = data['form'].get('print_totals_only', False)

        summary_rows = []
        summary_totals = []
        if totals_only:
            domain = [('date', '>=', start_date), ('date', '<=', end_date)]
            emp_ids = data['form']['employee_ids']
            cal_id = data['form']['resource_calender_id']
            if emp_ids:
                domain.append(('employee_id', 'in', list(set(emp_ids))))
            elif cal_id:
                rc = self.env['resource.calendar'].browse(cal_id)
                domain.append(('employee_id', 'in', rc.employee_ids.ids))

            att = self.env['hr.attendance.transaction'].search(domain)
            for emp in att.mapped('employee_id'):
                # lines = att.filtered(lambda l, e=emp: l.employee_id == e)

                emp_att_lines = att.filtered(lambda l: l.employee_id == emp)
                for seq in sorted(set(emp_att_lines.mapped('sequence'))):  # For each shift (1, 2)
                    lines = emp_att_lines.filtered(lambda l: l.sequence == seq)

                    all_days = {l.date for l in lines}
                    absent = {l.date for l in lines if l.is_absent}
                    vacation = {l.date for l in lines if l.normal_leave}

                    holidays = {l.date for l in lines if l.public_holiday}

                    iq = getattr(emp, 'iqama_number', False) or getattr(emp, 'saudi_number', '')
                    calendar_name = lines[0].calendar_id.name if lines and lines[0].calendar_id else ''
                    summary_rows.append({
                        'employee_number': emp.emp_no or '',
                        'name': emp.name,
                        'seq': f"{seq} - {calendar_name}" if seq else '',
                        'iqama': iq.display_name or '',
                        'department': emp.department_id.name,
                        'job': emp.sudo().job_id.name,
                        'days_present': len(all_days - absent - vacation - holidays),
                        'leave_days': len(vacation),
                        'holiday_days': len(holidays),
                        'absent_days': len(absent),

                        'office_hours': hhmm(sum(lines.mapped('office_hours'))),
                        'extra_hours': hhmm(sum(lines.mapped('additional_hours'))),
                        'permission_hours': hhmm(sum(lines.mapped('total_permission_hours'))),
                        'mission_hours': hhmm(sum(lines.mapped('total_mission_hours'))),
                        'lateness_approved': hhmm(sum(lines.filtered(lambda l: l.approve_lateness).mapped('lateness'))),
                        'early_exit_approved': hhmm(sum(lines.filtered(lambda l: l.approve_exit_out).mapped('early_exit'))),

                        'office_hours_int': (sum(lines.mapped('office_hours'))),
                        'extra_hours_int': (sum(lines.mapped('additional_hours'))),
                        'permission_hours_int': (sum(lines.mapped('total_permission_hours'))),
                        'mission_hours_int': (sum(lines.mapped('total_mission_hours'))),
                        'lateness_approved_int': (sum(lines.filtered(lambda l: l.approve_lateness).mapped('lateness'))),
                        'early_exit_approved_int': (sum(lines.filtered(lambda l: l.approve_exit_out).mapped('early_exit'))),

                    })

            summary_totals.append({
                'days_present': sum(row['days_present'] for row in summary_rows),
                'leave_days': sum(row['leave_days'] for row in summary_rows),
                'holiday_days': sum(row['holiday_days'] for row in summary_rows),
                'absent_days': sum(row['absent_days'] for row in summary_rows),

                'office_hours': hhmm(sum(row['office_hours_int'] for row in summary_rows)),
                'extra_hours': hhmm(sum(row['extra_hours_int'] for row in summary_rows)),
                'permission_hours': hhmm(sum(row['permission_hours_int'] for row in summary_rows)),
                'mission_hours': hhmm(sum(row['mission_hours_int'] for row in summary_rows)),
                'lateness_approved':hhmm( sum(row['lateness_approved_int'] for row in summary_rows)),
                'early_exit_approved': hhmm(sum(row['early_exit_approved_int'] for row in summary_rows)),
            })





        return {
            'doc_ids': data['ids'],
            'doc_model': data['model'],
            'date_start': start_date,
            'date_end': end_date,
            'type': type_,
            'data': final_dic,
            'mykey': mykey,
            'emp_data': emp_data,
            'total': total,
            'summary': summary_rows,
            'summary_totals': summary_totals,
            'totals_only': totals_only,
            'print_date': datetime.datetime.now().strftime("%H:%M %m/%d/%Y"),
            'print_user': self.env.user.name,
        }



class ReportAttendancegeneral(models.AbstractModel):
    _name = "report.attendances.general_attendances_report_temp_land"
    _description = "General Attendances Report"

    def get_value(self, data):
        type = data['form']['type']
        totals_only = data["form"].get("print_totals_only", False)
        employee_ids = data['form']['employee_ids']
        resource_calender_id = data['form']['resource_calender_id']
        from_date = data['form']['from_date']
        to_date = data['form']['to_date']
        domain = [('date', '>=', from_date), ('date', '<=', to_date)]
        data = []
        final_dic = {}
        key_list = []
        total_dic = {}
        mykey = []
        resource = self.env['resource.calendar'].browse(resource_calender_id)
        if resource and not employee_ids:
            if resource.employee_ids:
                for emp in resource.employee_ids:
                    employee_ids.append(emp.id)
        # if resource_calender_id:
        #     contract_ids = self.env['hr.contract'].search([('state', '=', 'program_directory'), ('resource_calendar_id', '=', resource_calender_id)])
        #     for con in contract_ids:
        #         employee_ids.append(con.employee_id.id)
        # print(">>>>>>>>>>>>>>>>>>>>>>>employeesemployees",employees)
        if employee_ids:
            last_employee_ids = list(set(employee_ids))
            domain.append(('employee_id', 'in', last_employee_ids))
        attendance_transaction_ids = self.env['hr.attendance.transaction'].search(domain)
        employees = attendance_transaction_ids.mapped('employee_id.name')
        employee_ids = attendance_transaction_ids.mapped('employee_id')
        emp_data = []
        for emp in employee_ids:
            emp_data.append({'job': emp.sudo().job_id.name, 'department': emp.department_id.name,
                             'emp_no': emp.emp_no, 'emp_namw': emp.name})
        grouped_data = collections.defaultdict(list)
        emp_data_dict = {}
        for item in emp_data:
            grouped_data[item['emp_namw']].append(item)
        for key, value in grouped_data.items():
            emp_data_dict[key] = list(value)
        if type == 'late':
            for resource in attendance_transaction_ids:
                note = ''
                if resource.is_absent:
                    note = 'غياب'
                elif resource.public_holiday:
                    note = "عطلة رسمية"
                elif resource.official_id:
                    note = resource.official_id.mission_type.name
                elif resource.normal_leave:
                    note = resource.leave_id.holiday_status_id.name
                elif resource.approve_personal_permission:
                    note = resource.personal_permission_id.permission_type_id.name
                elif not resource.public_holiday and not resource.normal_leave:
                    if resource.sign_in and not resource.sign_out:
                        note = 'نسيان بصمة'
                    elif not resource.sign_in and resource.sign_out:
                        note = 'نسيان بصمة'

                data.append({
                    'date': resource.date,
                    'day': WEEK_DAYS_AR[resource.date.weekday()],
                    'sig_in': resource.sign_in,
                    'sig_out': resource.sign_out,
                    'lateness': resource.lateness,
                    'early_exit': resource.early_exit,
                    'extra_hours': resource.additional_hours,
                    'office_hours': resource.office_hours,
                    'note': note,
                    'department': resource.employee_id.department_id.name,
                    'employee_number': resource.employee_number,
                    'calendar_id': resource.calendar_id.name,
                    'employee_id': resource.employee_id,
                    'employee_name': resource.employee_id.name,
                })

            data = sorted(data, key=lambda d: d['date'])
            for emp in employees:
                list_cat = attendance_transaction_ids.filtered(lambda r: r.employee_id.name == emp)
                total_lateness = sum(list_cat.mapped('lateness'))
                total_early_exit = sum(list_cat.mapped('early_exit'))
                total_late_early = str(datetime.timedelta(minutes=total_early_exit + total_lateness))
                total_extra_hours = sum(list_cat.mapped('additional_hours'))
                total_extra_hours = str(datetime.timedelta(minutes=total_extra_hours))

                list_missing_punch = attendance_transaction_ids.filtered(
                    lambda r: r.employee_id.name == emp and
                              not r.public_holiday and
                              not r.normal_leave and
                              ((r.sign_in and not r.sign_out) or (not r.sign_in and r.sign_out))
                )
                total_missing_punch = len(list_missing_punch)

                list_absent = attendance_transaction_ids.filtered(
                    lambda r: r.employee_id.name == emp and r.is_absent == True)
                total_absent = len(list_absent)
                list_not_log_in = attendance_transaction_ids.filtered(
                    lambda r: r.employee_id.name == emp and r.sign_in == 0.0)
                total_not_sig_in = len(list_not_log_in)
                list_not_log_out = attendance_transaction_ids.filtered(
                    lambda r: r.employee_id.name == emp and r.sign_out == 0.0)
                list_leave = attendance_transaction_ids.filtered(
                    lambda r: r.employee_id.name == emp and (r.normal_leave or r.approve_personal_permission))
                total_not_sig_out = len(list_not_log_out)
                total_leave = len(list_leave)
                total_dic[emp] = {'total_lateness': total_lateness, 'total_early_exit': total_early_exit,
                                  "total_extra_hours": total_extra_hours, "total_late_early": total_late_early,
                                  "total_leave": total_leave, 'total_absent': total_absent,
                                  'total_not_sig_in': total_not_sig_in,
                                  'total_not_sig_out': total_not_sig_out,
                                  'total_missing_punch':total_missing_punch}
            grouped = collections.defaultdict(list)
            for item in data:
                grouped[item['employee_name']].append(item)
            for key, value in grouped.items():
                final_dic[key] = list(value)
                key_list.append(key)
            mykey = list(dict.fromkeys(key_list))
            return final_dic, mykey, total_dic, emp_data_dict

        elif type == 'absent':
            for resource in attendance_transaction_ids.filtered(lambda r: r.is_absent == True):
                data.append({
                    'date': resource.date,
                    'employee_name': resource.employee_id.name,
                    'employee_id_department_id_name': resource.employee_id.department_id.name,
                    'day': datetime.datetime.strptime(str(resource.date), '%Y-%m-%d').date().strftime('%A'),
                })
                grouped = collections.defaultdict(list)
                for item in data:
                    grouped[item['employee_id_department_id_name']].append(item)
                for key, value in grouped.items():
                    final_dic[key] = list(value)
                    key_list.append(key)
                mykey = list(dict.fromkeys(key_list))
            return final_dic, mykey, '', emp_data_dict
        elif type == 'employee':
            for emp in employees:
                list_cat = attendance_transaction_ids.filtered(lambda r: r.employee_id.name == emp)
                total_lateness = sum(list_cat.mapped('lateness'))
                total_lateness = str(datetime.timedelta(minutes=total_lateness))
                total_early_exit = sum(list_cat.mapped('early_exit'))
                total_early_exit = str(datetime.timedelta(minutes=total_early_exit))
                total_dic[emp] = {'total_lateness': total_lateness, 'total_early_exit': total_early_exit}
                key_list.append(emp)
            mykey = list(dict.fromkeys(key_list))
            return '', mykey, total_dic, emp_data_dict


    @api.model
    def _get_report_values(self, docids, data=None):
        final_dic, mykey, total, emp_data = self.get_value(data)
        start_date = data['form']['from_date']
        end_date = data['form']['to_date']
        type_ = data['form']['type']
        totals_only = data['form'].get('print_totals_only', False)

        summary_rows = []
        summary_totals = []
        if totals_only:
            domain = [('date', '>=', start_date), ('date', '<=', end_date)]
            emp_ids = data['form']['employee_ids']
            cal_id = data['form']['resource_calender_id']
            if emp_ids:
                domain.append(('employee_id', 'in', list(set(emp_ids))))
            elif cal_id:
                rc = self.env['resource.calendar'].browse(cal_id)
                domain.append(('employee_id', 'in', rc.employee_ids.ids))

            att = self.env['hr.attendance.transaction'].search(domain)
            for emp in att.mapped('employee_id'):
                # lines = att.filtered(lambda l, e=emp: l.employee_id == e)

                emp_att_lines = att.filtered(lambda l: l.employee_id == emp)
                for seq in sorted(set(emp_att_lines.mapped('sequence'))):  # For each shift (1, 2)
                    lines = emp_att_lines.filtered(lambda l: l.sequence == seq)

                    all_days = {l.date for l in lines}
                    absent = {l.date for l in lines if l.is_absent}
                    vacation = {l.date for l in lines if l.normal_leave}
                    holidays = {l.date for l in lines if l.public_holiday}
                    missing_punch = {l.date for l in lines if
                                     not l.public_holiday and
                                     not l.normal_leave and
                                     ((l.sign_in and not l.sign_out) or (not l.sign_in and l.sign_out))}

                    iq = getattr(emp, 'iqama_number', False) or getattr(emp, 'saudi_number', '')
                    calendar_name = lines[0].calendar_id.name if lines and lines[0].calendar_id else ''
                    summary_rows.append({
                        'employee_number': emp.emp_no or '',
                        'name': emp.name,
                        'seq': f"{seq} - {calendar_name}" if seq else '',
                        'iqama': iq.display_name or '',
                        'department': emp.department_id.name,
                        'job': emp.sudo().job_id.name,
                        'days_present': len(all_days - absent - vacation - holidays),
                        'leave_days': len(vacation),
                        'holiday_days': len(holidays),
                        'absent_days': len(absent),
                        'missing_punch_days': len(missing_punch),
                        'office_hours': hhmm(sum(lines.mapped('office_hours'))),
                        'extra_hours': hhmm(sum(lines.mapped('additional_hours'))),
                        'permission_hours': hhmm(sum(lines.mapped('total_permission_hours'))),
                        'mission_hours': hhmm(sum(lines.mapped('total_mission_hours'))),
                        'lateness_approved': hhmm(sum(lines.filtered(lambda l: l.approve_lateness).mapped('lateness'))),
                        'early_exit_approved': hhmm(sum(lines.filtered(lambda l: l.approve_exit_out).mapped('early_exit'))),

                        'office_hours_int': (sum(lines.mapped('office_hours'))),
                        'extra_hours_int': (sum(lines.mapped('additional_hours'))),
                        'permission_hours_int': (sum(lines.mapped('total_permission_hours'))),
                        'mission_hours_int': (sum(lines.mapped('total_mission_hours'))),
                        'lateness_approved_int': (sum(lines.filtered(lambda l: l.approve_lateness).mapped('lateness'))),
                        'early_exit_approved_int': (sum(lines.filtered(lambda l: l.approve_exit_out).mapped('early_exit'))),

                    })

            summary_totals.append({
                'days_present': sum(row['days_present'] for row in summary_rows),
                'leave_days': sum(row['leave_days'] for row in summary_rows),
                'holiday_days': sum(row['holiday_days'] for row in summary_rows),
                'absent_days': sum(row['absent_days'] for row in summary_rows),
                'missing_punch_days': sum(row['missing_punch_days'] for row in summary_rows),
                'office_hours': hhmm(sum(row['office_hours_int'] for row in summary_rows)),
                'extra_hours': hhmm(sum(row['extra_hours_int'] for row in summary_rows)),
                'permission_hours': hhmm(sum(row['permission_hours_int'] for row in summary_rows)),
                'mission_hours': hhmm(sum(row['mission_hours_int'] for row in summary_rows)),
                'lateness_approved':hhmm( sum(row['lateness_approved_int'] for row in summary_rows)),
                'early_exit_approved': hhmm(sum(row['early_exit_approved_int'] for row in summary_rows)),
            })


        return {
            'doc_ids': data['ids'],
            'doc_model': data['model'],
            'date_start': start_date,
            'date_end': end_date,
            'type': type_,
            'data': final_dic,
            'mykey': mykey,
            'emp_data': emp_data,
            'total': total,
            'summary': summary_rows,
            'summary_totals': summary_totals,
            'totals_only': totals_only,
            'print_date': datetime.datetime.now().strftime("%H:%M %m/%d/%Y"),
            'print_user': self.env.user.name,
        }


class AttendancesReportXls(models.AbstractModel):
    _name = 'report.attendances.general_attendance_xls'
    _inherit = 'report.report_xlsx.abstract'

    def generate_xlsx_report(self, workbook, data, datas):
        self = self.with_context(lang=self.env.user.lang)
        x = self.env['report.attendances.general_attendances_report_temp']
        final_dic, mykey, total, emp_data = ReportAttendancePublic.get_value(x, data)
        start_date = data['form']['from_date']
        end_date = data['form']['to_date']
        type = data['form']['type']
        totals_only = data['form'].get('print_totals_only', False)
        sheet = workbook.add_worksheet(U'Holiday Report')
        calendar_id = data['form']['resource_calender_id']
        sheet.right_to_left()
        sheet.set_column(1, 10, 15)
        employee_ids = data['form']['employee_ids']
        format2 = workbook.add_format(
            {'font_size': 10, 'bottom': True, 'right': True, 'left': True, 'top': True, 'align': 'center',
             'bold': True})
        format2.set_align('center')
        format2.set_align('vcenter')
        fmt = workbook.add_format({'font_size': 10, 'border': 1, 'align': 'center', 'valign': 'vcenter', 'bold': True})

        # if totals_only:
        #     sheet.merge_range('F2:P2', _('تقرير الحضور والانصراف للموظفين'), fmt)
        #     sheet.write('G3', _('من تاريخ'), fmt)
        #     sheet.write('J3', _('إلى تاريخ'), fmt)
        #     sheet.write(2, 7, str(start_date), fmt)
        #     sheet.write(2, 10, str(end_date), fmt)
        #
        #     headers = [
        #         'الرقم الوظيفي', 'اسم الموظف', 'رقم الهوية', 'اﻹدارة', 'المسمي الوظيفي',
        #         'ايام الحضور', 'الاجازات', 'الاجازات الرسمية', 'الغياب', 'ساعات العمل الفعلية',
        #         'ساعات العمل الاضافية', 'الاستئذان', 'مهام عمل/انتداب/تدريب', 'التأخيرات', 'الخروج المبكر',
        #     ]
        #     for col, h in enumerate(headers, start=1):
        #         sheet.write(5, col, h, fmt)
        #
        #     domain = [('date', '>=', start_date), ('date', '<=', end_date)]
        #     emp_ids = data['form']['employee_ids']
        #     cal_id = data['form']['resource_calender_id']
        #     if emp_ids:
        #         domain.append(('employee_id', 'in', list(set(emp_ids))))
        #     elif cal_id:
        #         rc = self.env['resource.calendar'].browse(cal_id)
        #         domain.append(('employee_id', 'in', rc.employee_ids.ids))
        #     att = self.env['hr.attendance.transaction'].search(domain)
        #
        #     row = 6
        #     total_days = 0
        #     total_leave = 0
        #     total_holidays = 0
        #     total_absent = 0
        #     for emp in att.mapped('employee_id'):
        #         lines = att.filtered(lambda l, e=emp: l.employee_id == e)
        #
        #         all_days = {l.date for l in lines}
        #         absent = {l.date for l in lines if l.is_absent}
        #         vacation = {l.date for l in lines if l.normal_leave}
        #         holidays = {l.date for l in lines if l.public_holiday}
        #         total_days +=  len(all_days - absent - vacation - holidays)
        #         total_leave += len(vacation)
        #         total_holidays += len(holidays)
        #         total_absent += len(absent)
        #
        #         iq = getattr(emp, 'iqama_number', False) or getattr(emp, 'saudi_number', '')
        #
        #         sheet.write_row(row, 1, [
        #             emp.emp_no or '', emp.name, iq.display_name,
        #             emp.department_id.name, emp.sudo().job_id.name,
        #             len(all_days - absent - vacation - holidays),
        #             len(vacation), len(holidays), len(absent),
        #             hhmm(sum(lines.mapped('office_hours'))),
        #             hhmm(sum(lines.mapped('additional_hours'))),
        #             hhmm(sum(lines.mapped('total_permission_hours'))),
        #             hhmm(sum(lines.mapped('total_mission_hours'))),
        #             hhmm(sum(lines.filtered(lambda l: l.approve_lateness).mapped('lateness'))),
        #             hhmm(sum(lines.filtered(lambda l: l.approve_exit_out).mapped('early_exit')))
        #         ], fmt)
        #         row += 1
        #
        #     sheet.write_row(row, 1, [
        #         _('الاجمالي'), '', '', '', '',
        #         total_days,
        #         total_leave,
        #         total_holidays,
        #         total_absent,
        #         hhmm(sum(att.mapped('office_hours'))),
        #         hhmm(sum(att.mapped('additional_hours'))),
        #         hhmm(sum(att.mapped('total_permission_hours'))),
        #         hhmm(sum(att.mapped('total_mission_hours'))),
        #         hhmm(sum(att.filtered(lambda l: l.approve_lateness).mapped('lateness'))),
        #         hhmm(sum(att.filtered(lambda l: l.approve_exit_out).mapped('early_exit')))
        #     ], fmt)
        #     return

        if totals_only:

            sheet.merge_range('F2:P2', _('تقرير الحضور والانصراف للموظفين'), fmt)
            sheet.write('G3', _('من تاريخ'), fmt)
            sheet.write('J3', _('إلى تاريخ'), fmt)
            sheet.write(2, 7, str(start_date), fmt)
            sheet.write(2, 10, str(end_date), fmt)

            headers = [
                'الرقم الوظيفي', 'اسم الموظف', 'الدوام', 'رقم الهوية', 'اﻹدارة', 'المسمي الوظيفي',
                'ايام الحضور', 'الاجازات', 'الاجازات الرسمية', 'الغياب', 'نسيان البصمة',
                'ساعات العمل الفعلية', 'ساعات العمل الاضافية', 'الاستئذان', 'مهام عمل/انتداب/تدريب',
                'التأخيرات', 'الخروج المبكر',
            ]

            for col, h in enumerate(headers, start=1):
                sheet.write(5, col, h, fmt)

            domain = [('date', '>=', start_date), ('date', '<=', end_date)]
            emp_ids = data['form']['employee_ids']
            cal_id = data['form']['resource_calender_id']
            if emp_ids:
                domain.append(('employee_id', 'in', list(set(emp_ids))))
            elif cal_id:
                rc = self.env['resource.calendar'].browse(cal_id)
                domain.append(('employee_id', 'in', rc.employee_ids.ids))
            att = self.env['hr.attendance.transaction'].search(domain)

            row = 6
            total_days = 0
            total_leave = 0
            total_holidays = 0
            total_absent = 0
            total_missing_punch = 0
            for emp in att.mapped('employee_id'):
                emp_att_lines = att.filtered(lambda l: l.employee_id == emp)
                for seq in sorted(set(emp_att_lines.mapped('sequence'))):  # For each shift (1, 2)
                    lines = emp_att_lines.filtered(lambda l: l.sequence == seq)

                    all_days = {l.date for l in lines}
                    absent = {l.date for l in lines if l.is_absent}
                    vacation = {l.date for l in lines if l.normal_leave}
                    holidays = {l.date for l in lines if l.public_holiday}
                    missing_punch = {l.date for l in lines if
                                     not l.public_holiday and
                                     not l.normal_leave and
                                     ((l.sign_in and not l.sign_out) or (not l.sign_in and l.sign_out))}

                    total_days += len(all_days - absent - vacation - holidays)
                    total_leave += len(vacation)
                    total_holidays += len(holidays)
                    total_absent += len(absent)
                    total_missing_punch += len(missing_punch)
                    iq = getattr(emp, 'iqama_number', False) or getattr(emp, 'saudi_number', '')
                    calendar_name = lines[0].calendar_id.name if lines and lines[0].calendar_id else ''

                    sheet.write_row(row, 1, [
                        emp.emp_no or '',
                        emp.name,
                        f"{seq} - {calendar_name}" if seq else '',
                        iq.display_name,
                        emp.department_id.name,

                        emp.sudo().job_id.name,
                        len(all_days - absent - vacation - holidays),
                        len(vacation),
                        len(holidays),
                        len(absent),
                        len(missing_punch),
                        hhmm(sum(lines.mapped('office_hours'))),
                        hhmm(sum(lines.mapped('additional_hours'))),
                        hhmm(sum(lines.mapped('total_permission_hours'))),
                        hhmm(sum(lines.mapped('total_mission_hours'))),
                        hhmm(sum(lines.filtered(lambda l: l.approve_lateness).mapped('lateness'))),
                        hhmm(sum(lines.filtered(lambda l: l.approve_exit_out).mapped('early_exit')))
                    ], fmt)
                    row += 1

            # Totals row
            sheet.write_row(row, 1, [
                _('الاجمالي'), '', '', '', '','',
                total_days,
                total_leave,
                total_holidays,
                total_absent,
                total_missing_punch,
                hhmm(sum(att.mapped('office_hours'))),
                hhmm(sum(att.mapped('additional_hours'))),
                hhmm(sum(att.mapped('total_permission_hours'))),
                hhmm(sum(att.mapped('total_mission_hours'))),
                hhmm(sum(att.filtered(lambda l: l.approve_lateness).mapped('lateness'))),
                hhmm(sum(att.filtered(lambda l: l.approve_exit_out).mapped('early_exit')))
            ], fmt)

            return

        if type == 'late':
            sheet.merge_range('D3:I3', _("Attendance Reports"), format2)
            sheet.write('E4:E4', _("From date"), format2)
            sheet.write('G4:G4', _("To date"), format2)
            sheet.write(3, 5, str(start_date)[0:10], format2)
            sheet.write(3, 7, str(end_date)[0:10], format2)
            row = 9
            for key in mykey:
                n = 1
                h_col = 4
                size = len(final_dic[key])
                tot_size = len(total[key])
                sheet.write(row - 3, h_col, _('Employee Number'), format2)
                sheet.write(row - 3, h_col + 3, _('job '), format2)
                sheet.write(row - 2, h_col, _('Name'), format2)
                sheet.write(row - 2, h_col + 3, _('Department'), format2)

                sheet.write(row, n, _('date'), format2)
                sheet.write(row, n + 1, _('day'), format2)
                sheet.write(row, n + 2, _('Sign in'), format2)
                sheet.write(row, n + 3, _('Sign out'), format2)
                sheet.write(row, n + 4, _('lateness'), format2)
                sheet.write(row, n + 5, _('Early Exit'), format2)
                sheet.write(row, n + 6, _('Extra hours'), format2)
                sheet.write(row, n + 7, _('Office Hours'), format2)
                sheet.write(row, n + 8, _('Notes'), format2)
                sheet.write(row, n + 9, _('Shift'), format2)
                data_row = row + 1
                total_lateness = total_early_exit = total_extra_hours = total_office_hours = 0.0

                for line in final_dic[key]:
                    sheet.merge_range(row - 3, h_col + 1, row - 3, h_col + 2, emp_data[key][0]['emp_no'], format2)
                    sheet.write(row - 3, h_col + 4, emp_data[key][0]['job'], format2)
                    sheet.merge_range(row - 2, h_col + 1, row - 2, h_col + 2, emp_data[key][0]['emp_namw'], format2)
                    sheet.write(row - 2, h_col + 4, emp_data[key][0]['department'], format2)
                    sheet.write(data_row, n, str(line['date']), format2)
                    sheet.write(data_row, n + 1, str(line['day']), format2)

                    sheet.write(data_row, n + 2, '{0:02.0f}:{1:02.0f}'.format(*divmod(float(line['sig_in']) * 60, 60)),
                                format2)
                    sheet.write(data_row, n + 3, '{0:02.0f}:{1:02.0f}'.format(*divmod(float(line['sig_out']) * 60, 60)),
                                format2)
                    sheet.write(data_row, n + 4,
                                '{0:02.0f}:{1:02.0f}'.format(*divmod(float(line['lateness']) * 60, 60)), format2)
                    sheet.write(data_row, n + 5,
                                '{0:02.0f}:{1:02.0f}'.format(*divmod(float(line['early_exit']) * 60, 60)), format2)
                    sheet.write(data_row, n + 6,
                                '{0:02.0f}:{1:02.0f}'.format(*divmod(float(line['extra_hours']) * 60, 60)), format2)
                    sheet.write(data_row, n + 7,
                                '{0:02.0f}:{1:02.0f}'.format(*divmod(float(line['office_hours']) * 60, 60)), format2)

                    sheet.write(data_row, n + 8, line['note'], format2)
                    sheet.write(data_row, n + 9, line['calendar_id'], format2)
                    total_lateness += float(line['lateness'])
                    total_early_exit += float(line['early_exit'])
                    total_extra_hours += float(line['extra_hours'])
                    total_office_hours += float(line['office_hours'])
                    data_row += 1

                sheet.write(data_row + 1, n + 3, _('الاجمالي'), format2)
                sheet.write(data_row + 1, n + 4, '{0:02.0f}:{1:02.0f}'.format(*divmod(total_lateness * 60, 60)),
                            format2)
                sheet.write(data_row + 1, n + 5, '{0:02.0f}:{1:02.0f}'.format(*divmod(total_early_exit * 60, 60)),
                            format2)
                sheet.write(data_row + 1, n + 6, '{0:02.0f}:{1:02.0f}'.format(*divmod(total_extra_hours * 60, 60)),
                            format2)
                sheet.write(data_row + 1, n + 7, '{0:02.0f}:{1:02.0f}'.format(*divmod(total_office_hours * 60, 60)),
                            format2)

                sheet.write(data_row + 3, n + 4, _('Total lateness'), format2)
                # sheet.set_column(data_row,data_row, 15)
                sheet.write(data_row + 3, n + 5, str(total[key]['total_late_early'].split('.')[0]), format2)
                sheet.write(data_row + 3, n + 6, _('Total Absent'), format2)
                sheet.write(data_row + 3, n + 7, str(total[key]['total_absent']), format2)
                size -= 2
                sheet.write(data_row + 4, n + 4, _('Total Extra'), format2)
                sheet.write(data_row + 4, n + 5, str(total[key]['total_extra_hours'].split('.')[0]), format2)
                sheet.write(data_row + 4, n + 6, _('Total Leave'), format2)
                sheet.write(data_row + 4, n + 7, total[key]['total_leave'], format2)
                n += 1
                data_row += 5
                row += size + 3 + tot_size
                row += 1

                print("kkkkkkggggggggggg")
        elif type == 'absent':
            sheet.merge_range('C3:G3', _("Absent Report"), format2)
            sheet.merge_range('C4:G4', _("All Employee - Details"), format2)
            sheet.merge_range('B5:C5', _("From date"), format2)
            sheet.merge_range('F5:G5', _("To date"), format2)
            sheet.write(4, 3, str(start_date)[0:10], format2)
            sheet.write(4, 7, str(end_date)[0:10], format2)
            row = 8
            for key in mykey:
                n = 1
                size = len(final_dic[key])
                sheet.write(row - 2, n, _('Department'), format2)
                sheet.write(row, n, _('Employee Name'), format2)
                sheet.write(row, n + 1, _('Day'), format2)
                sheet.write(row, n + 2, _('date'), format2)
                sheet.write(row, n + 3, _('Notes'), format2)
                data_row = row + 1
                for line in final_dic[key]:
                    sheet.write(row - 2, n + 1, line['employee_id_department_id_name'], format2)
                    sheet.write(data_row, n, line['employee_name'], format2)
                    sheet.write(data_row, n + 1, line['day'], format2)
                    sheet.write(data_row, n + 2, line['date'], format2)
                    sheet.write(data_row, n + 3, (' '), format2)
                    data_row += 1
                n += 1
                row += size + 3
                row += 1

        elif type == 'employee':
            sheet.merge_range('C3:G3', _("Employee Attendance Report"), format2)
            sheet.merge_range('B4:C4', _("From date"), format2)
            sheet.merge_range('F4:G4', _("To date"), format2)
            sheet.write(3, 3, str(start_date)[0:10], format2)
            sheet.write(3, 7, str(end_date)[0:10], format2)
            row = 8
            for key in mykey:
                n = 1
                size = len(total[key])
                sheet.write(row, n, _('Employee Name'), format2)
                sheet.write(row, n + 1, _('Total of Lateness '), format2)
                sheet.write(row, n + 2, _('Total of Early Exit'), format2)
                data_row = row + 1
                sheet.write(data_row, n, key, format2)
                sheet.write(data_row, n + 1, total[key]['total_lateness'], format2)
                sheet.write(data_row, n + 2, total[key]['total_early_exit'], format2)
                data_row += 1
                n += 1
                row += size + 1
                row += 1

