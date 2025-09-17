# -*- coding: utf-8 -*-

from odoo import api, models, _


class EmployeeLeaveCostReport(models.AbstractModel):
    _name = 'report.hr_holidays_public.public_leave_cost_report'
    _description = 'Public Leave Cost Report'

    def get_result(self, data=None):
        form = data['form']
        employees = False
        departments = False
        li = []
        domain = []
        if form['employee_ids']:
            employees = self.env['hr.employee'].sudo().browse(form['employee_ids'])
        else:
            if form['department_ids'] and not form['employee_ids']:
                domain = [('department_id', 'in', form['department_ids'])]
                domain += [('state', '=', 'open')]
            employees = self.env['hr.employee'].sudo().search(domain)
        departments = employees.mapped('department_id')
        departments = departments.sorted(key=lambda r: r.id)

        for dep in departments:
            dep_leave = 0
            dep_cost = 0
            dep_data = {}
            dep_data['data'] = []
            for emp in dep.employee_ids.sorted(key=lambda r: r.id):
                day_salary = round(emp.contract_id.salary / 30)
                total_cost = emp.remaining_leaves * day_salary
                dep_leave += emp.remaining_leaves
                dep_cost += total_cost
                if emp in employees:
                    rec = {}
                    rec['employee'] = emp.name
                    rec['department_id'] = dep.name
                    rec['emp_no'] = emp.emp_no
                    rec['day_salary'] = day_salary
                    rec['leave'] = emp.remaining_leaves
                    rec['leave_cost'] = total_cost
                    dep_data['data'].append(rec)
            dep_data['leave'] = dep_leave
            dep_data['leave_cost'] = dep_cost
            li.append(dep_data)
        return li

    @api.model
    def _get_report_values(self, docids, data=None):
        record = self.get_result(data)
        return {
            'docs': record,
        }


class EmployeeLeaveCostReportXlsx(models.AbstractModel):
    _name = "report.hr_holidays_public.public_leave_cost_report_xls"
    _description = "XLSX Public Leave Cost Report"
    _inherit = 'report.report_xlsx.abstract'

    @api.model
    def generate_xlsx_report(self, workbook, data, objs):
        docs = self.env[
            'report.hr_holidays_public.public_leave_cost_report'].get_result(data)
        sheet = workbook.add_worksheet('Leaves Cost Report')
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
        sheet.merge_range('A9:I9', (_("Leave Cost Report")) + " ", format2)
        sheet.set_column('B:D', 15)
        sheet.set_column('E:L', 10)
        row = 9
        clm = 0
        for res in [(_('#')), (_('Department')), (_('Employee NO')), (_('Employee Name')),
                    (_('Department Leave Balance')), (_('Leave Balance')),
                    (_('Employee Cost Per Day')), (_('Employer Leave Cost')), (_('Department Leave Cost'))]:
            sheet.write(row, clm, res, format0)
            clm += 1
        row = 10
        seq = 0
        for doc in docs:
            for rec in doc['data']:
                seq += 1
                clm = 0
                sheet.write(row, clm, seq, format1)
                sheet.write(row, clm + 1, rec['department_id'], format1)
                sheet.write(row, clm + 2, rec['emp_no'], format1)
                sheet.write(row, clm + 3, rec['employee'], format1)
                sheet.write(row, clm + 4, round(doc['leave']), format1)
                sheet.write(row, clm + 5, round(rec['leave']), format1)
                sheet.write(row, clm + 6, round(rec['day_salary']), format1)
                sheet.write(row, clm + 7, round(rec['leave_cost']), format1)
                sheet.write(row, clm + 8, round(doc['leave_cost']), format1)
                row += 1


class EmployeeLeaveBalanceReport(models.AbstractModel):
    _name = 'report.hr_holidays_public.public_leave_balance_report'
    _description = 'Public Leave Balance Report'

    def get_result(self, data=None):
        form = data['form']
        employees = False
        departments = False
        li = []
        domain = []
        if form['employee_ids']:
            employees = self.env['hr.employee'].sudo().browse(form['employee_ids'])
        else:
            if form['department_ids'] and not form['employee_ids']:
                domain = [('department_id', 'in', form['department_ids'])]
            employees = self.env['hr.employee'].sudo().search(domain)
        value = [('employee_id', 'in', employees.ids), ('type', '=', 'add'),
                 ('check_allocation_view', '=', 'balance')]
        if form['leave_type_ids']:
            value += [('holiday_status_id', 'in', form['leave_type_ids'])]

        holidays = self.env['hr.holidays'].sudo().search(value)
        holidays = holidays.sorted(key=lambda r: r.holiday_status_id.id)
        labels = [
            (_('#')), (_('Employee NO')), (_('Employee Name')), (_('Join Date')), (_('Type Of Leave')),
            (_('Department')),
            (_('Deducted Leave Balance')), (_('Leave Balance')), (_('Overall Leave Balance'))]
        return [labels, holidays]

    @api.model
    def _get_report_values(self, docids, data=None):
        record = self.get_result(data)
        return {
            'docs': record,
        }


class EmployeeLeaveBalanceReportXlsx(models.AbstractModel):
    _name = "report.hr_holidays_public.public_leave_balance_report_xls"
    _description = "XLSX public Leave Balance Report"
    _inherit = 'report.report_xlsx.abstract'

    @api.model
    def generate_xlsx_report(self, workbook, data, objs):
        docs = self.env[
            'report.hr_holidays_public.public_leave_balance_report'].get_result(data)
        sheet = workbook.add_worksheet('Leaves balance Report')
        if self.env.user.lang != 'en_US':
            sheet.right_to_left()
        format0 = workbook.add_format(
            {'bottom': True, 'bg_color': '#263f79', 'right': True, 'left': True, 'top': True, 'align': 'center'})
        format1 = workbook.add_format({'bottom': True, 'right': True, 'left': True, 'top': True, 'align': 'center'})
        format2 = workbook.add_format(
            {'font_size': 14, 'bottom': True, 'right': True, 'left': True, 'top': True, 'align': 'center',
             'bold': True, 'bg_color': '#ffffff', 'font_color': 'black'})
        format2.set_align('center')
        sheet.merge_range('A9:L9', (_("Leave Balance Report")) + " ", format2)
        sheet.set_column('B:D', 15)
        sheet.set_column('E:I', 10)
        row = 9
        clm = 0
        for res in docs[0]:
            sheet.write(row, clm, res, format0)
            clm += 1
        row = 10
        seq = 0
        for doc in docs[1]:
            for rec in doc:
                seq += 1
                clm = 0
                sheet.write(row, clm, seq, format1)
                sheet.write(row, clm + 1, rec.employee_id.emp_no, format1)
                sheet.write(row, clm + 2, rec.employee_id.name, format1)
                sheet.write(row, clm + 3, rec.employee_id.joining_date, format1)
                sheet.write(row, clm + 4, rec.holiday_status_id.name, format1)
                sheet.write(row, clm + 5, rec.employee_id.department_id.name, format1)
                sheet.write(row, clm + 6, round(rec.leaves_taken, 2), format1)
                sheet.write(row, clm + 7, round(rec.remaining_leaves, 2), format1)
                sheet.write(row, clm + 8, round(rec.remaining_leaves + rec.leaves_taken, 2), format1)
                row += 1
