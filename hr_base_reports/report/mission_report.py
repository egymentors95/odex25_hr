# -*- coding: utf-8 -*-

from odoo import api, models, _
from datetime import datetime
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT


class EmployeeMissionReport(models.AbstractModel):
    _name = 'report.hr_base_reports.employee_mission_report'
    _description = 'Employee Mission Report'

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
        employees = self.env['hr.employee'].sudo().search(domain)
        date_to = datetime.strptime(form['date_to'], DEFAULT_SERVER_DATE_FORMAT)
        date_from = datetime.strptime(form['date_from'], DEFAULT_SERVER_DATE_FORMAT)
        clause_1 = ['&', ('date_to', '<=', date_to), ('date_to', '>=', date_from)]
        clause_2 = ['&', ('date_from', '<=', date_to), ('date_from', '>=', date_from)]
        clause_3 = ['&', ('date_from', '<=', date_from), ('date_to', '>=', date_to)]
        day_case = []
        if form['mission_type']:
            day_case += [('mission_type', '=', form['mission_type'][0])]
        day_case += [('employee_ids.employee_id', 'in', employees.ids), ('state', 'not in', ['draft', 'refused']),
                     ('process_type', '=', 'mission'), '|',
                     '|'] + clause_1 + clause_2 + clause_3
        day = self.env['hr.official.mission'].sudo().search(day_case)
        day_mission = day.sorted(key=lambda r: r.department_id.id)
        department = day_mission
        department_mission = department.mapped('employee_ids')
        return [day_mission, department_mission]

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


class EmployeeMissionReportXlsx(models.AbstractModel):
    _name = "report.hr_base_reports.employee_mission_report_xlsx"
    _description = 'XLSX Employee Mission Report'
    _inherit = 'report.report_xlsx.abstract'

    @api.model
    def generate_xlsx_report(self, workbook, data, objs):
        docs = self.env[
            'report.hr_base_reports.employee_mission_report'].get_result(data)
        sheet = workbook.add_worksheet('Employee Mission Report')
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
        sheet.merge_range('A2:O2',
                          (_("Employee Mission Report")) + " " + data['form']['date_from'] + '  -  ' + data['form'][
                              'date_to'], format2)
        sheet.set_column('B:D', 15)
        sheet.set_column('E:L', 10)
        row = 2
        clm = 0
        for res in [
            (_('#')), (_('Employee ID')), (_('Employee Name')), (_('Department')), (_('Mission Type')),
            (_('Reference Number')), (_('Start Trip')),
            (_('End Of Trip')), (_('Country')), (_('City')), (_('Per Diems')), (_('Ticket Cost')),
            (_('Total Cost')), (_('Department Total Cost')), (_('Days Number'))]:
            sheet.write(row, clm, res, format0)
            clm += 1
        row = 3
        seq = 0
        total = 0
        for doc in docs[0]:
            for rec in doc.employee_ids:
                mission_data = doc.get_mission_data(doc, rec.employee_id, docs[1])
                seq += 1
                clm = 0
                total += rec.amount
                sheet.write(row, clm, seq, format1)
                sheet.write(row, clm + 1, rec.employee_id.emp_no, format1)
                sheet.write(row, clm + 2, rec.employee_id.name, format1)
                sheet.write(row, clm + 3, rec.employee_id.department_id.name, format1)
                sheet.write(row, clm + 4, str(rec.official_mission_id.mission_type.name), format1)
                sheet.write(row, clm + 5, rec.official_mission_id.reference, format1)
                sheet.write(row, clm + 6, rec.hour_from if rec.official_mission_id.mission_type.duration_type == 'hours'
                else rec.date_from, format1)
                sheet.write(row, clm + 7, rec.hour_to if rec.official_mission_id.mission_type.duration_type == 'hours'
                else rec.date_to, format1)
                sheet.write(row, clm + 8, rec.official_mission_id.country_id.name, format1)
                sheet.write(row, clm + 9, str(rec.official_mission_id.destination.name), format1)
                sheet.write(row, clm + 10, round(rec.day_price), format1)
                sheet.write(row, clm + 11, round(mission_data[0]), format1)
                sheet.write(row, clm + 12, round(rec.amount), format1)
                sheet.write(row, clm + 13, round(mission_data[1]), format1)
                sheet.write(row, clm + 14, rec.official_mission_id.date_duration, format1)
                row += 1
            sheet.write(row, clm, (_('Total')), format0)
            sheet.write(row, clm + 12, total, format1)


# Training

class EmployeeTrainingReport(models.AbstractModel):
    _name = 'report.hr_base_reports.employee_training_report'
    _description = 'Employee Training Report'

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
        date_to = form['date_to']
        date_from = form['date_from']
        clause_1 = ['&', ('date_to', '<=', date_to), ('date_to', '>=', date_from)]
        clause_2 = ['&', ('date_from', '<=', date_to), ('date_from', '>=', date_from)]
        clause_3 = ['&', ('date_from', '<=', date_from), ('date_to', '>=', date_to)]
        value = []
        if form['mission_type']:
            value += [('mission_type', '=', form['mission_type'][0])]
        day_case = value + [('employee_ids.employee_id', 'in', employees.ids),
                            ('state', 'not in', ['draft', 'refused']), ('process_type', '=', 'training'), '|',
                            '|'] + clause_1 + clause_2 + clause_3
        day = self.env['hr.official.mission'].sudo().search(day_case)
        # day_mission = day.sorted(key=lambda r: r.department_id.id)
        record = day.mapped('employee_ids').sorted(key=lambda r: r.employee_id.department_id.id)
        records = record.filtered(lambda r: r.employee_id in employees)

        labels = [
            (_('#')), (_('Employee ID')), (_('Employee Name')), (_('Location')), (_('Department')), (_('Job Title')),
            (_('Join Date')), (_('Line Manager')), (_('Title Of Course')), (_('Course Organization')),
            (_('Course Location')),
            (_('Cost Of Course')), (_('Cost Of Ticket')), (_('Cost Of Day')), (_('Total Cost')), (_('Date Of Course')),
            (_('End Training')), (_('Period Of Course')),(_('Total Hours')), (_('Status'))]
        return [labels, records]

    @api.model
    def _get_report_values(self, docids, data=None):
        record = self.get_result(data)
        x = []
        y = 0.0
        for r in record[1]:
            ticket = sum(
                self.env['hr.ticket.request'].sudo().search([('mission_request_id', '=', r.official_mission_id.id),
                                                             ('employee_id', '=', r.employee_id.id)]).mapped(
                    'cost_of_tickets')) or 0
            y = ticket
            x.append(y)
        date_to, date_from = ' / ', ' / '
        if data['form']['date_from'] and data['form']['date_to']:
            date_from = data['form']['date_from']
            date_to = data['form']['date_to']
        return {
            'date_from': date_from,
            'date_to': date_to,
            'docs': record,
            'x': x,
        }


class EmployeeMissionTrainingReportXlsx(models.AbstractModel):
    _name = "report.hr_base_reports.employee_training_report_xlsx"
    _description = 'XLSX Employee Training Report'
    _inherit = 'report.report_xlsx.abstract'

    @api.model
    def generate_xlsx_report(self, workbook, data, objs):
        docs = self.env[
            'report.hr_base_reports.employee_training_report'].get_result(data)
        sheet = workbook.add_worksheet('Employee Training Report')
        if self.env.user.lang != 'en_US':
            sheet.right_to_left()
        format0 = workbook.add_format(
            {'bottom': True, 'bg_color': '#263f79', 'right': True, 'left': True, 'top': True, 'align': 'center',
             'font_color': 'white'})
        format1 = workbook.add_format({'bottom': True, 'right': True, 'left': True, 'top': True, 'align': 'center', })
        format2 = workbook.add_format(
            {'font_size': 14, 'bottom': True, 'right': True, 'left': True, 'top': True, 'align': 'center',
             'bold': True, 'bg_color': '#ffffff', 'font_color': 'black'})
        date_format = workbook.add_format({'num_format': 'dd-mm-yyyy', 'align': 'center'})


        format2.set_align('center')
        sheet.merge_range('A9:S9',
                          (_("Employee Training Report")) + " " + data['form']['date_from'] + '  -  ' + data['form'][
                              'date_to'], format2)
        sheet.set_column('B:D', 15)
        sheet.set_column('E:O', 10)
        row = 9
        clm = 0
        for res in docs[0]:
            sheet.write(row, clm, res, format0)
            clm += 1
        row = 10
        seq = 0
        for rec in docs[1]:
            ticket = sum(
                self.env['hr.ticket.request'].sudo().search([('mission_request_id', '=', rec.official_mission_id.id),
                                                             ('employee_id', '=', rec.employee_id.id)]).mapped(
                    'cost_of_tickets')) or 0
            seq += 1
            clm = 0
            stages = {
                'draft': 'مبدئي',
                'send': 'انتظار المدير المباشر',
                'direct_manager': 'انتظار مدير الادارة',
                'depart_manager': 'انتظار الموارد البشرية',
                'hr_aaproval': 'انتظار التنفيذي',
                'approve': 'تم التصديق',
                'refused': 'رفض'
            }
            sheet.write(row, clm, seq, format1)
            sheet.write(row, clm + 1, rec.employee_id.emp_no, format1)
            sheet.write(row, clm + 2, rec.employee_id.name, format1)
            sheet.write(row, clm + 3, rec.employee_id.working_location.name, format1)
            sheet.write(row, clm + 4, rec.employee_id.department_id.name, format1)
            sheet.write(row, clm + 5, rec.employee_id.job_id.name, format1)
            sheet.write(row, clm + 6, rec.employee_id.first_hiring_date, date_format)
            sheet.write(row, clm + 7, rec.employee_id.parent_id.name, format1)
            sheet.write(row, clm + 8, rec.official_mission_id.course_name.name, format1)
            sheet.write(row, clm + 9, rec.official_mission_id.partner_id.name, format1)
            sheet.write(row, clm + 10, rec.official_mission_id.destination.name, format1)
            sheet.write(row, clm + 11, round(rec.train_cost_emp, 2), format1)
            sheet.write(row, clm + 12, round(ticket, 2), format1)
            sheet.write(row, clm + 13, round(rec.day_price, 2), format1)
            sheet.write(row, clm + 14, (rec.day_price + rec.train_cost_emp), format1)
            sheet.write(row, clm + 15, rec.date_from, date_format)
            sheet.write(row, clm + 16, rec.date_to, date_format)

            # sheet.write(row, clm + 17, str(rec.hours))
            sheet.write(row, clm + 17, str(rec.days))
            # sheet.write(row, clm + 18, str(rec.days))
            sheet.write(row, clm + 18, str(rec.total_hours))
            if self.env.user.lang != 'en_US':
                sheet.write(row, clm + 19, stages[rec.official_mission_id.state], format1)
            else:
                sheet.write(row, clm + 19,
                            dict(rec.official_mission_id._fields['state'].selection).get(rec.official_mission_id.state),
                            format1)
            row += 1
