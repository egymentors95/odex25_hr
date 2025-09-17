# -*- coding: utf-8 -*-

from odoo import api, models, _


class EmployeeGeneralReport(models.AbstractModel):
    _name = 'report.hr_base_reports.employee_general_report'
    _description = "Employee General Report"

    def get_result(self, data=None):
        form = data['form']
        employees = False
        li = []
        domain = []
        if form['employee_ids']:
            employees = self.env['hr.employee'].sudo().browse(form['employee_ids'])
            employees = employees.sorted(key=lambda r: r.emp_no)
        else:
            if form['department_ids'] and not form['employee_ids']:
                domain = [('department_id', 'in', form['department_ids']), ('state', '=', 'open')]
            domain += [('state', '=', 'open')]
            employees = self.env['hr.employee'].sudo().search(domain)
            employees = employees.sorted(key=lambda r: r.emp_no)
        return employees

    @api.model
    def _get_report_values(self, docids, data=None):
        record = self.get_result(data)

        return {

            'docs': record,
        }


class EmployeeGeneralReportXlsx(models.AbstractModel):
    _name = "report.hr_base_reports.employee_general_report_xlsx"
    _description = 'XLSX Employee General Report'
    _inherit = 'report.report_xlsx.abstract'

    @api.model
    def generate_xlsx_report(self, workbook, data, objs):
        docs = self.env[
            'report.hr_base_reports.employee_general_report'].get_result(data)
        sheet = workbook.add_worksheet('Employee General Report')
        if self.env.user.lang != 'en_US':
            sheet.right_to_left()
        format0 = workbook.add_format(
            {'bottom': True, 'bg_color': '#b8bcbf', 'right': True, 'left': True, 'top': True, 'align': 'center', })
        format1 = workbook.add_format({'bottom': True, 'right': True, 'left': True, 'top': True, 'align': 'center', })
        format2 = workbook.add_format(
            {'font_size': 14, 'bottom': True, 'right': True, 'left': True, 'top': True, 'align': 'center',
             'bold': True, 'bg_color': '#0f80d6', 'font_color': 'white'})
        date_format = workbook.add_format({'num_format': 'dd-mm-yyyy', 'align': 'center'})

        format2.set_align('center')
        sheet.merge_range('A9:Q9', (_("Employee General Report")) + " ", format2)
        sheet.set_column('B:D', 15)
        sheet.set_column('E:L', 10)
        row = 9
        clm = 0
        for res in [
            (_('#')), (_('Employee ID')), (_('Employee Name')), (_('Location')), (_('Department')), (_('Job Title')),
            (_('Join Date')), (_('Bank')), (_('IBN')), (_('Line Manager')), (_('Birth Date')),
            (_('Identification Number')),
            (_('Employee Salary')), (_('House Allowance')), (_('Transportation Allowance')), (_('Other Benefits')),
            (_('Leave Balance'))]:
            sheet.write(row, clm, res, format0)
            clm += 1
        row = 10
        seq = 0
        for rec in docs:
            other_value = rec.get_transport_allowance(rec.contract_id)
            seq += 1
            clm = 0
            sheet.write(row, clm, seq, format1)
            sheet.write(row, clm + 1, rec.emp_no, format1)
            sheet.write(row, clm + 2, rec.name, format1)
            working_location = rec.working_location.name or ''
            sheet.write(row, clm + 3, working_location, format1)
            sheet.write(row, clm + 4, rec.department_id.name, format1)
            sheet.write(row, clm + 5, rec.job_id.name, format1)
            sheet.write(row, clm + 6, rec.first_hiring_date, date_format)
            sheet.write(row, clm + 7, rec.bank_account_id.acc_number, format1)
            sheet.write(row, clm + 8, rec.bank_code, format1)
            sheet.write(row, clm + 9, rec.parent_id.name, format1)
            sheet.write(row, clm + 10, rec.birthday, date_format)
            sheet.write(row, clm + 11,
                        rec.saudi_number.saudi_id if rec.check_nationality == True else rec.iqama_number.iqama_id,
                        format1)
            sheet.write(row, clm + 12, rec.contract_id.salary, format1)
            sheet.write(row, clm + 13, rec.contract_id.house_allowance_temp, format1)
            sheet.write(row, clm + 14, round(other_value[1]), format1)
            sheet.write(row, clm + 15, round(other_value[0]), format1)
            sheet.write(row, clm + 16, round(other_value[2],2), format1)
            row += 1

