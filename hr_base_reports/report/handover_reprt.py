# -*- coding: utf-8 -*-

from odoo import api, models, _


class EmployeeHandoverReport(models.AbstractModel):
    _name = 'report.hr_base_reports.employee_handover_report'
    _description = 'Employee Handover Report'

    def get_result(self, data=None):
        form = data['form']
        employees = False
        li = []
        domain = []
        if form['employee_ids']:
            employees = self.env['hr.employee'].sudo().browse(form['employee_ids'])
        else:
            if form['department_ids'] and not form['employee_ids']:
                domain = [('department_id', 'in', form['department_ids'])]
            # domain += [('state','=','open')]
            employees = self.env['hr.employee'].sudo().search(domain)
        value = [('last_work_date', '>=', form['date_from']), ('create_date', '<=', form['date_to']),
                 ('state', '!=', 'refused')]
        if employees:
            value += [('employee_id', 'in', employees.ids)]
        records = self.env['hr.termination'].sudo().search(value)
        records = records.sorted(key=lambda r: r.department_id.id)
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


class EmployeeHandoverReportXlsx(models.AbstractModel):
    _name = "report.hr_base_reports.employee_handover_report_xlsx"
    _description = 'XLSX Employee Handover Report'
    _inherit = 'report.report_xlsx.abstract'

    @api.model
    def generate_xlsx_report(self, workbook, data, objs):
        docs = self.env[
            'report.hr_base_reports.employee_handover_report'].get_result(data)
        sheet = workbook.add_worksheet('Handover Report')
        if self.env.user.lang != 'en_US':
            sheet.right_to_left()
        format0 = workbook.add_format({'bottom': True, 'bg_color': '#b8bcbf', 'right': True, 'left': True, 'top': True, 'align': 'center', })
        format1 = workbook.add_format({'bottom': True, 'right': True, 'left': True, 'top': True, 'align': 'center', })
        format2 = workbook.add_format(
            {'font_size': 14, 'bottom': True, 'right': True, 'left': True, 'top': True, 'align': 'center',
             'bold': True, 'bg_color': '#0f80d6', 'font_color': 'white'})

        format2.set_align('center')
        sheet.merge_range('A9:K9',(_("Employee Handover Report")) + " " + data['form']['date_from'] + '  -  ' + data['form']['date_to'], format2)
        sheet.set_column('B:D', 15)
        sheet.set_column('E:L', 10)
        row = 9
        clm = 0
        for res in [
            (_('#')), (_('Employee ID')), (_('Employee Name')), (_('Job Title')),
            (_('Department')), (_('Join Date')), (_('Reason of Resignation')), (_('Date of Resignation')),
            (_('Last Date')),
            (_('Location')), (_('Line Manager'))]:
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
            sheet.write(row, clm + 3, rec.job_id.name, format1)
            sheet.write(row, clm + 4, rec.employee_id.department_id.name, format1)
            sheet.write(row, clm + 5, rec.first_hire_date, format1)
            sheet.write(row, clm + 6, rec.reason, format1)
            sheet.write(row, clm + 7, rec.create_date, format1)
            sheet.write(row, clm + 8, rec.last_work_date, format1)
            sheet.write(row, clm + 9, rec.employee_id.working_location, format1)
            sheet.write(row, clm + 10, rec.employee_id.parent_id.name, format1)
            row += 1

