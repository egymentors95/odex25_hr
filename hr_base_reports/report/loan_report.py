# -*- coding: utf-8 -*-

from odoo import api, models, _


class EmployeeloanReport(models.AbstractModel):
    _name = 'report.hr_base_reports.employee_loan_report'
    _description = "Employee Loan Report"

    def get_result(self, data=None):
        form = data['form']
        employees = False
        li = []
        domain = []
        if form['employee_ids']:
            employees = self.env['hr.employee'].sudo().browse(form['employee_ids'])
        else:
            if form['department_ids'] and not form['employee_ids']:
                domain = [('department_id', 'in', form['department_ids']), ('state', '!=', 'out_of_service')]
            domain += [('state', '!=', 'out_of_service')]
            employees = self.env['hr.employee'].sudo().search(domain)
        value = []
        if employees:
            value += [('employee_id', 'in', employees.ids)]
        if form['request_type_id']:
            value += [('request_type', '=', form['request_type_id'][0])]
        if form['old']:
            value += [('state', 'not in', ['draft', 'cancel'])]
        if not form['old']:
            value += [('state', '=', 'pay')]
        if form['date_from'] and form['date_to']:
            value += [('date', '>=', form['date_from']), ('date', '<=', form['date_to'])]
        records = self.env['hr.loan.salary.advance'].sudo().search(value)
        records = records.sorted(key=lambda r: r.employee_id.department_id.id)
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


class EmployeeLoanReportXlsx(models.AbstractModel):
    _name = "report.hr_base_reports.employee_loan_report_xlsx"
    _description = "XLSX Employee Loan Report"
    _inherit = 'report.report_xlsx.abstract'

    @api.model
    def generate_xlsx_report(self, workbook, data, objs):
        docs = self.env[
            'report.hr_base_reports.employee_loan_report'].get_result(data)
        sheet = workbook.add_worksheet('Employee Loan Report')
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
        sheet.merge_range('A9:L9',
                          (_("Employee Loan Report")) + " " + data['form']['date_from'] + '  -  ' + data['form'][
                              'date_to'], format2)
        sheet.set_column('B:D', 15)
        sheet.set_column('E:M', 10)
        row = 9
        clm = 0

        for res in [
            (_('#')), (_('Employee ID')), (_('Employee Name')), (_('Department')), (_('Loan Type')),
            (_('Date Of Loan')), (_('Total Balance')), (_('Period Of installment')),
            (_('Installment Amount')), (_('Paid Amount')), (_('Loan Due Date')), (_('Outstanding'))]:
            sheet.write(row, clm, res, format0)
            clm += 1
        row = 10
        seq = 0
        for rec in docs:
            lens = len(rec.deduction_lines)
            num = lens - 1 if lens > 0 else 0
            seq += 1
            clm = 0
            sheet.write(row, clm, seq, format1)
            sheet.write(row, clm + 1, rec.employee_id.emp_no, format1)
            sheet.write(row, clm + 2, rec.employee_id.name, format1)
            sheet.write(row, clm + 3, rec.department_id.name, format1)
            sheet.write(row, clm + 4, rec.request_type.name, format1)
            sheet.write(row, clm + 5, rec.date, format1)
            sheet.write(row, clm + 6, round(rec.gm_propos_amount,2), format1)
            sheet.write(row, clm + 7, rec.months, format1)
            # sheet.write(row, clm+8,rec.deduction_lines[0].installment_date, format1)
            # sheet.write(row, clm+8, rec.deduction_lines[num].installment_date, format1)
            sheet.write(row, clm + 8, round(rec.installment_amount, 2), format1)
            sheet.write(row, clm + 9, round(rec.total_paid_inst, 2), format1)
            sheet.write(row, clm + 10, rec.deduction_lines[num].installment_date, format1)
            sheet.write(row, clm + 11, round(rec.remaining_loan_amount, 2), format1)
            row += 1