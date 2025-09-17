# -*- coding: utf-8 -*-

from datetime import datetime
from odoo import api, models, _
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT


class EmployeeAttendanceReport(models.AbstractModel):
    _name = 'report.hr_base_reports.employee_attendance_report'
    _description = 'Employee Attendance Report'

    def get_result(self, data=None):
        form = data['form']
        employees = False
        domain = []
        if form['employee_ids']:
            employees = self.env['hr.employee'].sudo().browse(form['employee_ids'])
        else:
            if form['department_ids'] and not form['employee_ids']:
                domain = [('department_id', 'in', form['department_ids']), ('state', '=', 'open')]
            domain += [('state', '=', 'open')]
            employees = self.env['hr.employee'].sudo().search(domain)
        end_date = datetime.strptime(str(form['date_to']), DEFAULT_SERVER_DATE_FORMAT)
        start_date = datetime.strptime(str(form['date_from']), DEFAULT_SERVER_DATE_FORMAT)
        value = [('date', '>=', start_date), ('date', '<=', end_date)]
        records = self.env['hr.attendance.transaction'].sudo().search(value)
        record = records.filtered(lambda r: r.employee_id in employees).sorted(
            lambda r: r.date) if employees else records.sorted(lambda r: r.date)
        return record, records

    # lateness_reasons = reason_pool.search([('latest_date', '>=', self.date_from),
    #                                        ('latest_date', '<=', self.date_to),
    #                                        ('employee_id', '=', employee.id),
    #                                        ('state', '=', 'hr_manager')])
    @api.model
    def _get_report_values(self, docids, data=None):
        record = self.get_result(data)
        date_to, date_from = ' / ', ' / '
        if data['form']['date_from'] and data['form']['date_to']:
            date_from = data['form']['date_from']
            date_to = data['form']['date_to']
        return {
            'date_from': date_from,
            'date_to': date_to,
            'docs': record,
        }


class EmployeeAttendanceReportXlsx(models.AbstractModel):
    _name = "report.hr_base_reports.employee_attendance_report_xlsx"
    _description = 'XLSX Employee Attendance Report'
    _inherit = 'report.report_xlsx.abstract'

    @api.model
    def generate_xlsx_report(self, workbook, data, objs):
        docs = self.env[
            'report.hr_base_reports.employee_attendance_report'].get_result(data)
        sheet = workbook.add_worksheet('Employee  Attendance Transaction')
        if self.env.user.lang != 'en_US':
            sheet.right_to_left()
        format0 = workbook.add_format(
            {'bottom': True, 'bg_color': '#b8bcbf', 'right': True, 'left': True, 'top': True, 'align': 'center', })
        format1 = workbook.add_format({'bottom': True, 'right': True, 'left': True, 'top': True, 'align': 'center', })
        format2 = workbook.add_format(
            {'font_size': 14, 'bottom': True, 'right': True, 'left': True, 'top': True, 'align': 'center',
             'bold': True, 'bg_color': '#0f80d6', 'font_color': 'white'})

        format2.set_align('center')
        sheet.merge_range('A9:Q9', (_("Employee Attendance Transaction")) + " " + data['form']['date_from'] + '  -  ' +
                          data['form']['date_to'], format2)
        sheet.set_column('B:D', 15)
        sheet.set_column('E:Q', 10)
        row = 9
        clm = 0
        if self.env.user.lang == 'ar_001':
            for res in [
                (_('م')), (_('التاريخ')), (_('رقم الهوية')), (_('اسم الموظف')), (_('اسم القسم')), (_('الوظيفة')),
                (_('زمن الدخول')), (_('زمن الخروج')), (_('التأخيرات')), (_('خروج مبكر')),
                (_('إجمالي ساعات الإذن'))
                , (_('ساعات الحضور')), (_('ساعات إضافية')), (_('اسم الأجازة')),
                (_('عطل رسمية')), (_('مهام العمل')), (_('غياب'))]:
                sheet.write(row, clm, res, format0)
                clm += 1
        if self.env.user.lang == 'en_US':
            for res in [
                (_('#')), (_('Date')), (_('Employee ID')), (_('Employee Name')), (_('Department')), (_('Job Title')),
                (_('Sign In Time')), (_('Sign Out Time')), (_('Lateness Hours')),(_('Early Exit')),(_('Total Permission Hours'))
                ,(_('Office Hours')), (_('Extra Hour')), (_('Leave Name')),
                (_('Public Holiday')),(_('Is Official')),(_('Is Absent'))]:
                sheet.write(row, clm, res, format0)
                clm += 1
        row = 10
        seq = 0
        for rec in docs[0]:
            # attendance_value = rec.get_attendance_value(rec.employee_id, docs[1])
            seq += 1
            clm = 0
            # start = rec.employee_id.get_time_permission(rec.personal_permission_id)
            # extra = rec.official_hours - rec.office_hours
            # late = rec.break_duration + rec.lateness + rec.approve_exit_out
            sheet.write(row, clm, seq, format1)
            sheet.write(row, clm + 1, str(rec.date), format1)
            if rec.employee_id.saudi_number:
                sheet.write(row, clm + 2, rec.employee_id.saudi_number.saudi_id, format1)
            if rec.employee_id.iqama_number:
                sheet.write(row, clm + 2, rec.employee_id.iqama_number.iqama_id, format1)
            sheet.write(row, clm + 3, rec.employee_id.with_context({'lang': str(self.env.user.lang)}).name, format1)
            sheet.write(row, clm + 4, rec.employee_id.department_id.name, format1)
            sheet.write(row, clm + 5, rec.employee_id.job_id.name, format1)
            sheet.write(row, clm + 6, '{0:02.0f}:{1:02.0f}'.format(*divmod(float(rec.sign_in) * 60, 60)), format1)
            sheet.write(row, clm + 7, '{0:02.0f}:{1:02.0f}'.format(*divmod(float(rec.sign_out) * 60, 60)), format1)
            sheet.write(row, clm + 8, '{0:02.0f}:{1:02.0f}'.format(*divmod(float(rec.lateness) * 60, 60)), format1)
            sheet.write(row, clm + 9, '{0:02.0f}:{1:02.0f}'.format(*divmod(float(rec.early_exit) * 60, 60)), format1)
            sheet.write(row, clm + 10, '{0:02.0f}:{1:02.0f}'.format(*divmod(float(rec.total_permission_hours) * 60, 60)), format1)
            sheet.write(row, clm + 11, '{0:02.0f}:{1:02.0f}'.format(*divmod(float(rec.office_hours) * 60, 60)), format1)
            sheet.write(row, clm + 12, '{0:02.0f}:{1:02.0f}'.format(*divmod(float(rec.additional_hours) * 60, 60)),format1)
            sheet.write(row, clm + 13, rec.holiday_name.name if rec.holiday_name else " ", format1)
            sheet.write(row, clm + 14, rec.public_holiday, format1)
            sheet.write(row, clm + 15,rec.is_official, format1)
            sheet.write(row, clm + 16,rec.is_absent, format1)
            row += 1

