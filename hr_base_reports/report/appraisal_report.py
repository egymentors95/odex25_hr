# -*- coding: utf-8 -*-

from odoo import api, models, _


class EmployeeAppraisalReport(models.AbstractModel):
    _name = 'report.hr_base_reports.employee_appraisal_report'
    _description = "Employee Appraisal Report"

    def get_result(self, data=None):
        form = data['form']
        employees = False
        domain = []
        if form['employee_ids']:
            employees = form['employee_ids']
        else:
            if form['department_ids'] and not form['employee_ids']:
                domain = [('department_id', 'in', form['department_ids']), ('state', '=', 'open')]
            employees = self.env['hr.employee'].sudo().search(domain).ids
        value = [('employee_id', 'in', employees)]
        if form['date_from'] and form['date_to']:
            value += [('appraisal_date', '>=', form['date_from']), ('appraisal_date', '<=', form['date_to'])]
        records = self.env['hr.employee.appraisal'].sudo().search(value)
        records = records.sorted(key=lambda r: (r.employee_id.department_id.id, r.appraisal_plan_id.id))
        return records

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


class EmployeeAppraisalReportXlsx(models.AbstractModel):
    _name = "report.hr_base_reports.employee_appraisal_report_xlsx"
    _description = "XLSX Employee Appraisal Report"
    _inherit = 'report.report_xlsx.abstract'

    @api.model
    def generate_xlsx_report(self, workbook, data, objs):
        docs = self.env[
            'report.hr_base_reports.employee_appraisal_report'].get_result(data)
        sheet = workbook.add_worksheet((_('Employee Appraisal Report')))
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
        sheet.merge_range('A9:J9',
                          (_("Employee Appraisal Report")) + " " + data['form']['date_from'] + '  -  ' + data['form'][
                              'date_to'], format2)
        sheet.set_column('B:D', 20)
        sheet.set_column('E:L', 10)
        row = 9
        clm = 0
        label = [
            (_('#')), (_('Employee ID')), (_('Employee Name')), (_('Location')), (_('Department')), (_('Job Title')),
            (_('Join Date')), (_('Line Manager')), (_('Appraisal Plan')), (_('Performance Grade'))]
        for res in label:
            sheet.write(row, clm, res, format0)
            clm += 1
        row = 10
        seq = 0
        for rec in docs:
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
            sheet.write(row, clm + 8, rec.appraisal_plan_id.name, format1)
            sheet.write(row, clm + 9, round(rec.level_achieved_percentage, 2), format1)
            row += 1

