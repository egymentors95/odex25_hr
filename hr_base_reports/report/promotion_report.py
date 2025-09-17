# -*- coding: utf-8 -*-

import io
import base64

from odoo import api, fields, models, tools, _
from odoo.exceptions import ValidationError, UserError


class EmployeePromotionReport(models.AbstractModel):
    _name = 'report.hr_base_reports.employee_promotion_report'
    _description = "Employee Promotion Report"

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
        value = [('state', 'not in', ['draft', 'refuse']), ('employee_id', 'in', employees.ids)]
        if form['date_from'] and form['date_to']:
            value += [('date', '>=', form['date_from']), ('date', '<=', form['date_to'])]
        records = self.env['employee.promotions'].sudo().search(value)
        labels = [
            (_('#')), (_('Employee ID')), (_('Employee Name')), (_('Nationality')), (_('Department')), (_('Location')),
            (_('Join Date')), (_('Previous Job Title')), (_('Previous Line Manager')), (_('Previous Grade'))
            , (_('Current Job Title')), (_('current Line Manager')), (_('Current Grade')), (_('Previous Salary')),
            (_('Current Salary')), (_('The Year Of Promotion'))]
        records.sorted(key=lambda r: r.employee_id.department_id.id)
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


class EmployeePromotionReportXlsx(models.AbstractModel):
    _name = "report.hr_base_reports.employee_promotion_report_xlsx"
    _description = "XLSX Employee Promotion Report"
    _inherit = 'report.report_xlsx.abstract'

    @api.model
    def generate_xlsx_report(self, workbook, data, objs):
        docs = self.env[
            'report.hr_base_reports.employee_promotion_report'].get_result(data)
        sheet = workbook.add_worksheet('Promotion Report')
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
        sheet.merge_range('A9:P9',
                          (_("Promotion Report")) + " " + data['form']['date_from'] + '  -  ' + data['form']['date_to'],
                          format2)
        sheet.set_column('B:D', 15)
        sheet.set_column('E:P', 10)
        row = 9
        clm = 0
        for res in docs[0]:
            sheet.write(row, clm, res, format0)
            clm += 1
        row = 10
        seq = 0
        for rec in docs[1]:
            seq += 1
            clm = 0
            sheet.write(row, clm, seq, format1)
            sheet.write(row, clm + 1, rec.employee_id.emp_no, format1)
            sheet.write(row, clm + 2, rec.employee_id.name, format1)
            sheet.write(row, clm + 3, rec.employee_id.country_id.name, format1)

            sheet.write(row, clm + 4, rec.employee_id.department_id.name, format1)
            sheet.write(row, clm + 5, rec.employee_id.working_location, format1)
            sheet.write(row, clm + 6, rec.employee_id.first_hiring_date, format1)

            sheet.write(row, clm + 7, rec.current_job_id.name, format1)
            sheet.write(row, clm + 8, rec.employee_id.parent_id.name, format1)
            sheet.write(row, clm + 9, rec.old_degree_2.name, format1)

            sheet.write(row, clm + 10, rec.promotion_job_id.name, format1)
            sheet.write(row, clm + 11, rec.employee_id.parent_id.name, format1)
            sheet.write(row, clm + 12, rec.new_degree.name, format1)

            sheet.write(row, clm + 13, rec.old_degree_2.base_salary, format1)
            sheet.write(row, clm + 14, rec.new_degree.base_salary, format1)

            sheet.write(row, clm + 15, rec.date, format1)
            # sheet.write(row, clm+16,dict(rec._fields['state'].selection).get(rec.state), format1)

            row += 1

