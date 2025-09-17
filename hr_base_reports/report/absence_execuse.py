# -*- coding: utf-8 -*-


from odoo import api, fields, models, tools, _


# Excuse
class EmployeeExecuseReport(models.AbstractModel):
    _name = 'report.hr_base_reports.employee_executions_report'
    _description = 'Employee Executions Report'

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
        li = []
        date_to = form['date_to']
        date_from = form['date_from']
        clause_1 = ['&', ('date_to', '<=', date_to), ('date_to', '>=', date_from)]
        clause_2 = ['&', ('date_from', '<=', date_to), ('date_from', '>=', date_from)]
        clause_3 = ['&', ('date_from', '<=', date_from), ('date_to', '>=', date_to)]
        value = [('state', 'not in', ['refused', 'draft']), ('employee_id', 'in', employees.ids), '|',
                 '|'] + clause_1 + clause_2 + clause_3
        record = self.env['hr.personal.permission'].sudo().search(value)
        for e in employees.sorted(key=lambda r: r.department_id.id):
            permission = record.filtered(lambda r: r.employee_id == e)
            for p in permission:
                date_permission = permission.filtered(lambda r: fields.Datetime.from_string(
                    p.date_from).date() == fields.Datetime.from_string(r.date_from).date())
                overall = sum(date_permission.mapped('duration')) if date_permission else p.duration
                rec = {}
                early_exit = {'early_exit': "خروج مبكر", 'late entry': "دخول متاخر", 'during work': "اثناء الدوام"}
                rec['employee'] = e.name
                rec['id'] = e.emp_no
                rec['department_id'] = e.department_id.name
                rec['job_id'] = e.job_id.name
                rec['join'] = e.first_hiring_date
                rec['date'] = p.date_from
                if p.type_exit:
                    rec['type'] = early_exit[p.type_exit] if self.env.user.lang != 'en_US' else dict(
                        p._fields['type_exit'].selection).get(p.type_exit)
                else:
                    rec['type'] = False
                rec['duration'] = p.duration
                rec['overall'] = overall
                li.append(rec)
        labels = [
            (_('#')), (_('Employee ID')), (_('Employee Name')), (_('Department')), (_('Join Date')), (_('Job Title')),
            (_('Type Of Excuse')), (_('Date')), (_('Number Of Excuse')), (_('Overall Excuse'))]
        return [labels, li]

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


class EmployeeExecuseReportXlsx(models.AbstractModel):
    _name = "report.hr_base_reports.employee_executions_report_xlsx"
    _description = 'XLSX Employee Executions Report'
    _inherit = 'report.report_xlsx.abstract'

    @api.model
    def generate_xlsx_report(self, workbook, data, objs):
        docs = self.env[
            'report.hr_base_reports.employee_executions_report'].get_result(data)
        sheet = workbook.add_worksheet('Employee  Excuse Transaction')
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
                          (_("Employee Excuse Transaction")) + " " + data['form']['date_from'] + '  -  ' + data['form'][
                              'date_to'], format2)
        sheet.set_column('B:D', 15)
        sheet.set_column('E:J', 10)
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
            sheet.write(row, clm + 1, rec['id'], format1)
            sheet.write(row, clm + 2, rec['employee'], format1)
            sheet.write(row, clm + 3, rec['department_id'], format1)
            sheet.write(row, clm + 4, rec['join'], format1)
            sheet.write(row, clm + 5, rec['job_id'], format1)
            sheet.write(row, clm + 6, rec['type'], format1)
            sheet.write(row, clm + 7, rec['date'], format1)
            sheet.write(row, clm + 8, round(rec['duration']), format1)
            sheet.write(row, clm + 9, round(rec['overall']), format1)
            row += 1

# Absence
class EmployeeAbsenceReport(models.AbstractModel):
    _name = 'report.hr_base_reports.employee_absence_report'
    _description = 'Employee Absence Report'

    def get_result(self, data=None):
        form = data['form']
        employees = False
        domain = []
        if form['employee_ids']:
            employees = self.env['hr.employee'].sudo().browse(form['employee_ids'])
        else:
            if form['department_ids'] and not form['employee_ids']:
                domain = [('department_id', 'in', form['department_ids'])]
            employees = self.env['hr.employee'].sudo().search(domain)
        li = []
        attendance = self.env['hr.attendance.transaction'].sudo().search(
            [('date', '>=', form['date_from']), ('date', '<=', form['date_to']),
             ('employee_id', 'in', employees.ids), ('is_absent', '=', True),('approve_lateness', '=', False),
             ('public_holiday', '=', False), ('approve_personal_permission', '=', False), ('is_official', '=', False),('normal_leave', '=', False)])
        for e in employees:
            # overall = sum(attendance.filtered(lambda r: r.employee_id == e).mapped('lateness')) + sum(
            #     attendance.filtered(lambda r: r.employee_id == e).mapped('early_exit')) or 0
            work_hour = e.resource_calendar_id.working_hours
            day_price = e.contract_id.total_allowance / 30
            overall_day = len(attendance.filtered(lambda r: r.employee_id == e))
            rec = {}
            rec['employee'] = e.name
            rec['id'] = e.emp_no
            rec['department_id'] = e.department_id.name
            rec['job_id'] = e.job_id.name
            rec['days'] = overall_day
            rec['day_cost'] = day_price
            rec['hour_cost'] = day_price / work_hour if work_hour > 0 else 0
            rec['cost'] = day_price * overall_day
            li.append(rec)
        labels = [
            (_('#')), (_('Employee ID')), (_('Employee Name')), (_('Department')),
            (_('Job Title')),
            (_('Total Absence Days')), (_('Total Cost')), (_('Total Deduction'))]
        return [labels, li]

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


class EmployeeAbcenseReportXlsx(models.AbstractModel):
    _name = "report.hr_base_reports.employee_absence_report_xlsx"
    _description = "XLSX Employee Absence Report"
    _inherit = 'report.report_xlsx.abstract'

    @api.model
    def generate_xlsx_report(self, workbook, data, objs):
        docs = self.env[
            'report.hr_base_reports.employee_absence_report'].get_result(data)
        sheet = workbook.add_worksheet('Employee  Absence Transaction')
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
        sheet.merge_range('A9:H9',
                          (_("Employee Absence Transaction")) + " " + data['form']['date_from'] + '  -  ' +
                          data['form'][
                              'date_to'], format2)
        sheet.set_column('B:D', 15)
        sheet.set_column('E:H', 10)
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
            sheet.write(row, clm + 1, rec['id'], format1)
            sheet.write(row, clm + 2, rec['employee'], format1)
            sheet.write(row, clm + 3, rec['department_id'], format1)
            sheet.write(row, clm + 4, rec['job_id'], format1)
            sheet.write(row, clm + 5, round(rec['days'], 2), format1)
            sheet.write(row, clm + 6, round(rec['day_cost'], 2), format1)
            sheet.write(row, clm + 7, round(rec['cost'], 2), format1)
            row += 1

