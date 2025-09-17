# -*- coding: utf-8 -*-

from odoo import api, models, _


class EmployeeIqamaReport(models.AbstractModel):
    _name = 'report.hr_base_reports.employee_iqama_report'
    _description = "Employee Iqama Report"

    def get_result(self, data=None):
        form = data['form']
        employees = False
        li = []
        domain = []
        if form['employee_ids']:
            employees = self.env['hr.employee'].sudo().browse(form['employee_ids'])
        else:
            if form['department_ids'] and not form['employee_ids']:
                domain = [('department_id', 'in', form['department_ids']), ('state', '=', 'open')]
            domain += [('state', '=', 'open')]
            employees = self.env['hr.employee'].sudo().search(domain)
        value = [('line_id.state', 'not in', ['draft', 'refused'])]
        if employees:
            value += [('employee_id', 'in', employees.ids)]
        if form['date_from'] and form['date_to']:
            value += [('line_id.date', '>=', form['date_from']), ('line_id.date', '<=', form['date_to'])]
        records = self.env['employee.iqama.renewal.line'].sudo().search(value)
        records = records.sorted(key=lambda r: r.employee_id.department_id.id)
        rec = records
        labels = [
            (_('#')), (_('Employee ID')), (_('Employee Name')), (_('Location')), (_('Department')), (_('Job Title')),
            (_('Join Date')), (_('Line Manager')), (_('Date Of Payment')), (_('The Amount')), (_('Nationality')),
            (_('Identity Expiry Date'))]
        return [labels, records]

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
class EmployeeIqamaReportXlsx(models.AbstractModel):
    _name = "report.hr_base_reports.employee_iqama_report_xlsx"
    _description = "XLSX Employee Iqama Report"
    _inherit = 'report.report_xlsx.abstract'

    @api.model
    def generate_xlsx_report(self, workbook, data, objs):
        docs = self.env[
            'report.hr_base_reports.employee_iqama_report'].get_result(data)
        sheet = workbook.add_worksheet('Identity Report')
        if self.env.user.lang != 'en_US':
            sheet.right_to_left()
        format0 = workbook.add_format(
            {'bottom': True, 'bg_color': '#263f79', 'right': True, 'left': True, 'top': True, 'align': 'center',
             'font_color': 'white'})
        format1 = workbook.add_format({'bottom': True, 'right': True, 'left': True, 'top': True, 'align': 'center', })
        format2 = workbook.add_format(
            {'font_size': 14, 'bottom': True, 'right': True, 'left': True, 'top': True, 'align': 'center',
             'bold': True, 'bg_color': '#ffffff', 'font_color': 'black'})

        format2.set_align('center')
        sheet.merge_range('A9:L9', (_("Identity Report")) + " ", format2)
        sheet.set_column('B:D', 15)
        sheet.set_column('E:L', 10)
        row = 9
        clm = 0
        for res in docs[0]:
            sheet.write(row, clm, res, format0)
            clm += 1
        row = 10
        seq = 0
        for rec in docs[1]:
            stages = {'draft': "مسودة", 'submit': " مسؤول علاقات الموظفين", 'hr_depart': "الموارد البشرية",
                      'effective_department': "الرئيس التنفيذي",
                      'chief_accountant': "تم الترحيل",
                      'refused': "رفض"}
            seq += 1
            clm = 0
            sheet.write(row, clm, seq, format1)
            sheet.write(row, clm + 1, rec.employee_id.emp_no, format1)
            sheet.write(row, clm + 2, rec.employee_id.name, format1)
            sheet.write(row, clm + 3, rec.employee_id.working_location, format1)
            sheet.write(row, clm + 4, rec.employee_id.department_id.name, format1)
            sheet.write(row, clm + 5, rec.employee_id.job_id.name, format1)
            sheet.write(row, clm + 6, rec.employee_id.first_hiring_date, format1)
            sheet.write(row, clm + 7, rec.employee_id.parent_id.name, format1)
            sheet.write(row, clm + 8, rec.line_id.date, format1)
            sheet.write(row, clm + 9, rec.total, format1)
            sheet.write(row, clm + 10, rec.employee_id.country_id.name, format1)
            sheet.write(row, clm + 11, rec.employee_id.iqama_expiy_date, format1)

        row += 1
