# -*- coding: utf-8 -*-

from odoo import api, models, _


class EmployeeSaudiReport(models.AbstractModel):
    _name = 'report.hr_base_reports.employee_saudi_report'
    _description = "Employee Saudi Report"

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
        employees = employees.sorted(key=lambda r: r.department_id.id)
        return employees

    @api.model
    def _get_report_values(self, docids, data=None):
        record = self.get_result(data)
        i = 0
        j = 0
        k = 0
        for e in record:
            if e.check_nationality == True:
                i += 1
            else:
                j += 1
            k = i + j
        date_to, date_from = ' / ', ' / '
        if data['form']['date_from'] and data['form']['date_to']:
            date_from = data['form']['date_from']
            date_to = data['form']['date_to']
        return {
            'date_from': date_from,
            'date_to': date_to,
            'docs': record,
            'i': i,
            'j': j,
            'k': k,
        }


class EmployeeSaudiReportXlsx(models.AbstractModel):
    _name = "report.hr_base_reports.employee_saudi_report_xlsx"
    _description = "XLSX Employee Saudi Report"
    _inherit = 'report.report_xlsx.abstract'

    @api.model
    def generate_xlsx_report(self, workbook, data, objs):
        docs = self.env[
            'report.hr_base_reports.employee_saudi_report'].get_result(data)
        sheet = workbook.add_worksheet('Saudi Report')
        if self.env.user.lang != 'en_US':
            sheet.right_to_left()
        format0 = workbook.add_format(
            {'bottom': True, 'bg_color': '#263f79', 'right': True, 'left': True, 'top': True, 'align': 'center',
             'font_color': 'white'})
        format11 = workbook.add_format(
            {'bottom': True, 'bg_color': '#b8bcbf', 'right': True, 'left': True, 'top': True, 'align': 'center', })
        format1 = workbook.add_format({'bottom': True, 'right': True, 'left': True, 'top': True, 'align': 'center', })
        format2 = workbook.add_format(
            {'font_size': 14, 'bottom': True, 'right': True, 'left': True, 'top': True, 'align': 'center',
             'bold': True, 'bg_color': '#ffffff', 'font_color': 'black'})
        format3 = workbook.add_format({'bottom': True, 'right': True, 'left': True, 'top': True, 'align': 'center', })

        format2.set_align('center')
        sheet.merge_range('A9:F9', (_("Saudi Report")) + " ", format2)
        sheet.set_column('B:D', 15)
        sheet.set_column('E:F', 10)
        row = 9
        clm = 0
        for res in [
            (_('#')), (_('Employee ID')), (_('Employee Name')), (_('Nationality')), (_('Department')),
            (_('Join Date'))]:
            sheet.write(row, clm, res, format0)
            clm += 1
        row = 10
        seq = 0
        for rec in docs:
            seq += 1
            clm = 0
            sheet.write(row, clm, seq, format1)
            sheet.write(row, clm + 1, rec.emp_no, format1)
            sheet.write(row, clm + 2, rec.name, format1)
            sheet.write(row, clm + 3, rec.country_id.name, format1)
            sheet.write(row, clm + 4, rec.department_id.name, format1)
            sheet.write(row, clm + 5, rec.first_hiring_date, format1)
            row += 1
        x = row
        y = clm + 3
        for a in [(_('Saudi')), (_('Non Saudi')), (_('Total'))]:
            sheet.write(x + 1, y, a, format11)
            y += 1
        i = 0
        j = 0
        for a in docs:
            if a.check_nationality == True:
                i += 1
            else:
                j += 1
            k = i + j
            sheet.write(x + 2, y - 3, i, format3)
            sheet.write(x + 2, y - 2, j, format3)
            sheet.write(x + 2, y - 1, k, format3)