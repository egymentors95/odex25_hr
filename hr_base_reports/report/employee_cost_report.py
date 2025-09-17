# -*- coding: utf-8 -*-

from odoo import api, models, _


class EmployeeCostReport(models.AbstractModel):
    _name = 'report.hr_base_reports.employee_cost_report'
    _description = 'Employee Cost Report'

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
        department = self.env['hr.department'].search([])
        y = []
        for dep in department:
            i = 0
            z = 0
            for e in employees:
                salary_value = e.get_employee_data_report(e.contract_id, data['form']['date_from'],
                                                          data['form']['date_to'])
                x = round(salary_value[2], 2)
                if e.department_id.id == dep.id:
                    i += 1
                    z += x
            y.append(z)
        labels = [
            (_('#')), (_('Department')), (_('Employee ID')), (_('Employee Name')), (_('Employee Basic Wage')),
            (_('House Allowance')), (_('Transportation Allowance')), (_('Other Benefits')), (_('Employee GOSI')),
            (_('Employer GOSI')), (_('Daily Wage')),
            (_('Total')), (_('Annual Cost')), (_('Department Total Cost'))]
        return [labels, employees, y]

    @api.model
    def _get_report_values(self, docids, data=None):
        record = self.get_result(data)
        department = self.env['hr.department'].search([])

        date_to, date_from = ' / ', ' / '
        if data['form']['date_from'] and data['form']['date_to']:
            date_from = data['form']['date_from']
            date_to = data['form']['date_to']
        return {
            'date_from': date_from,
            'date_to': date_to,
            'docs': record,
            'department': department,
        }


class EmployeeCostReportXlsx(models.AbstractModel):
    _name = "report.hr_base_reports.employee_cost_report_xlsx"
    _description = 'XLSX Employee Cost Report'
    _inherit = 'report.report_xlsx.abstract'

    @api.model
    def generate_xlsx_report(self, workbook, data, objs):
        docs = self.env[
            'report.hr_base_reports.employee_cost_report'].get_result(data)
        sheet = workbook.add_worksheet('Department Cost Report')
        if self.env.user.lang != 'en_US':
            sheet.right_to_left()
        format0 = workbook.add_format(
            {'bottom': True, 'bg_color': '#b8bcbf', 'right': True, 'left': True, 'top': True, 'align': 'center', })
        format1 = workbook.add_format({'bottom': True, 'right': True, 'left': True, 'top': True, 'align': 'center', })
        format2 = workbook.add_format(
            {'font_size': 14, 'bottom': True, 'right': True, 'left': True, 'top': True, 'align': 'center',
             'bold': True, 'bg_color': '#0f80d6', 'font_color': 'white'})

        format2.set_align('center')
        sheet.merge_range('A9:N9',
                          (_("Department Cost Report")) + " " + data['form']['date_from'] + '  -  ' + data['form'][
                              'date_to'], format2)
        sheet.set_column('B:D', 15)
        sheet.set_column('E:M', 10)
        row = 9
        clm = 0
        for res in docs[0]:
            sheet.write(row, clm, res, format0)
            clm += 1
        row = 10
        seq = 0

        for rec in docs[1]:
            department = self.env['hr.department'].search([])
            salary_value = rec.get_employee_data_report(rec.contract_id, data['form']['date_from'],
                                                        data['form']['date_to'])
            seq += 1
            clm = 0
            sheet.write(row, clm, seq, format1)
            sheet.write(row, clm + 1, rec.department_id.name, format1)
            sheet.write(row, clm + 2, rec.emp_no, format1)
            sheet.write(row, clm + 3, rec.name, format1)
            sheet.write(row, clm + 4, rec.contract_id.salary, format1)
            sheet.write(row, clm + 5, rec.contract_id.house_allowance_temp, format1)
            sheet.write(row, clm + 6, rec.contract_id.transport_allowance, format1)
            sheet.write(row, clm + 7, round(salary_value[1], 2), format1)
            sheet.write(row, clm + 8, rec.contract_id.gosi_deduction, format1)
            sheet.write(row, clm + 9, rec.contract_id.gosi_employer_deduction, format1)
            sheet.write(row, clm + 10, round(salary_value[0], 2), format1)
            sheet.write(row, clm + 11, rec.contract_id.total_allowance, format1)
            sheet.write(row, clm + 12, round(salary_value[2], 2), format1)
            i = 0
            for d in department:
                if rec.department_id.id == d.id:
                    sheet.write(row, clm + 13, docs[2][i], format1)
                i += 1
            row += 1