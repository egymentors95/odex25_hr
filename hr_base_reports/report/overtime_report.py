# -*- coding: utf-8 -*-

from odoo import api, models, _
from datetime import datetime
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT

from dateutil.relativedelta import relativedelta
import calendar


class EmployeeOvertimeReport(models.AbstractModel):
    _name = 'report.hr_base_reports.employee_overtime_report'
    _description = 'Employee Overtime Report'

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
        delta = (end_date.year - start_date.year) * 12 + (end_date.month - start_date.month) + 1
        li = []
        emps = []
        days = []
        records = []
        for i in range(delta):
            if i < delta:
                if i > 0:
                    start_date = start_date.replace(day=1)
                day = start_date + relativedelta(months=i)
                end = calendar.monthrange(day.year, day.month)[1]
                to = day.replace(day=end)
                if i == delta - 1:
                    to = end_date
                days.append(day)
                clause_1 = ['&', ('employee_over_time_id.date_to', '<=', to),('employee_over_time_id.date_to', '>=', day)]
                clause_2 = ['&', ('employee_over_time_id.date_from', '<=', to),('employee_over_time_id.date_from', '>=', day)]
                clause_3 = ['&', ('employee_over_time_id.date_from', '<=', day),('employee_over_time_id.date_to', '>=', to)]
                value = [('employee_over_time_id.state', '!=', 'refused'), '|', '|'] + clause_1 + clause_2 + clause_3
                if employees:
                    value += [('employee_id', 'in', employees.ids)]
                lines = self.env['line.ids.over.time'].sudo().search(value)
                emps += (lines.mapped('employee_id'))
                li.append({'day': day, 'data': lines})
        if emps:
            for e in sorted(emps, key=lambda r: r.department_id):
                rec = {'employee': e.name, 'department_id': e.department_id.name, 'job_id': e.job_id.name,
                       'salary': e.contract_id.salary, 'data': []}
                total = 0
                for l in li:
                    recs = l['data'].filtered(lambda r: r.employee_id == e)
                    # hours = sum(recs.mapped('over_time_workdays_hours')+recs.mapped('over_time_vacation_hours')) if recs else 0.0
                    hours = sum(recs.mapped('price_hour')) if recs else 0.0
                    total += hours
                    rec['data'].append(hours)
                rec['total'] = total
                records.append(rec)
        datas = {'days': days, 'data': records}
        return datas

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
class EmployeeOvertimeReportXlsx(models.AbstractModel):
    _name = "report.hr_base_reports.employee_overtime_report_xlsx"
    _description = 'XLSX Employee Overtime Report'
    _inherit = 'report.report_xlsx.abstract'

    @api.model
    def generate_xlsx_report(self, workbook, data, objs):
        docs = self.env[
            'report.hr_base_reports.employee_overtime_report'].get_result(data)
        sheet = workbook.add_worksheet((_('Employee Overtime Report')))
        if self.env.user.lang != 'en_US':
            sheet.right_to_left()
        format0 = workbook.add_format(
            {'bottom': True, 'bg_color': '#b8bcbf', 'right': True, 'left': True, 'top': True, 'align': 'center', })
        format1 = workbook.add_format({'bottom': True, 'right': True, 'left': True, 'top': True, 'align': 'center', })
        format2 = workbook.add_format(
            {'font_size': 14, 'bottom': True, 'right': True, 'left': True, 'top': True, 'align': 'center',
             'bold': True, 'bg_color': '#0f80d6', 'font_color': 'white'})

        sheet.merge_range('A9:I9',
                          (_("Employee Overtime Report")) + " " + data['form']['date_from'] + '  -  ' + data['form'][
                              'date_to'], format2)
        sheet.set_column('B:D', 20)
        sheet.set_column('E:I', 10)
        row = 9
        clm = 0
        label = [
            (_('#')), (_('Department')), (_('Employee Name')), (_('Job Title')), (_('Employee Basic Wage'))]

        for day in docs['days']:
            date = (_('OT')) + " " + day.strftime('%d/%m/%Y')
            label.append(date)
        label.append((_('Total')))
        for res in label:
            sheet.write(row, clm, res, format0)
            clm += 1
        row = 10
        seq = 0
        for rec in docs['data']:
            seq += 1
            clm = 0
            sheet.write(row, clm, seq, format1)
            sheet.write(row, clm + 1, rec['department_id'], format1)
            sheet.write(row, clm + 2, rec['employee'], format1)
            sheet.write(row, clm + 3, rec['job_id'], format1)
            sheet.write(row, clm + 4, round(rec['salary'], 2), format1)
            cl = 5
            for o in rec['data']:
                sheet.write(row, cl, o, format1)
                cl += 1
            sheet.write(row, cl, round(rec['total'], 2), format1)
            row += 1

