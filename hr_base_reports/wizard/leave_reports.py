# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
from odoo import models, fields, api, _
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT as DATETIME_FORMAT


class HrLeaveReportsWizard(models.TransientModel):
    _name = "hr.leave.reports.wizard"

    _description = "Leaves Wizard"

    date_from = fields.Datetime()
    date_to = fields.Datetime()
    leave_type_id = fields.Many2one('hr.holidays.status')
    job_id = fields.Many2one('hr.job')

    def get_report(self):
        """Call when button 'Get Report' clicked.
        """
        data = {
            'ids': self.ids,
            'model': self._name,
            'form': {
                'date_start': self.date_from,
                'date_end': self.date_to,
                'leave_type_id': self.leave_type_id.id,
                'job_id': self.job_id.id,
            },
        }

        return self.env.ref('hr_base_reports.action_leaves_report').report_action(self, data=data)

    def get_reportxlsxs(self):
        data = {
            'ids': self.ids,
            'model': self._name,
            'form': {
                'date_start': self.date_from,
                'date_end': self.date_to,
                'leave_type_id': self.leave_type_id.id,
                'job_id': self.job_id.id,
            },
        }
        return self.env.ref('hr_base_reports.action_leaves_report_xlsx').report_action(self, data=data)


class ReportHrLeaveReportsWizard(models.AbstractModel):
    """Abstract Model for report template.
    for `_name` model, please use `report.` as prefix then add `module_name.report_name`.
    """

    _name = 'report.hr_base_reports.report_leaves_of_employee_template'
    _description = 'Leaves of Employee Template Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        date_start = datetime.strptime(data['form']['date_start'], DATETIME_FORMAT)
        date_end = datetime.strptime(data['form']['date_end'], DATETIME_FORMAT) + timedelta(days=1)
        leave_type_id = data['form']['leave_type_id']
        job_id = data['form']['job_id']

        docs = []

        if leave_type_id:
            leaves = self.env['hr.holidays'].search([
                ('date_from', '>=', date_start.strftime(DATETIME_FORMAT)),
                ('date_to', '<', date_end.strftime(DATETIME_FORMAT)), ('type', '=', 'remove'),
                ('state', '!=', 'refuse'),
                ('holiday_status_id', '=', leave_type_id)])
        else:
            leaves = self.env['hr.holidays'].search([
                ('date_from', '>=', date_start.strftime(DATETIME_FORMAT)),
                ('date_to', '<', date_end.strftime(DATETIME_FORMAT)), ('type', '=', 'remove'),
                ('state', '!=', 'refuse')])

        for item in leaves:
            if item.holiday_status_id.id == leave_type_id or item.employee_id.job_id.id == job_id:
                docs.append({
                    'employee': item.employee_id.name,
                    'department': item.department_id.name,
                    'job': item.employee_id.job_id.name,
                    'number_of_days': item.number_of_days_temp,
                    'holiday_status_id': item.holiday_status_id.id,
                    'date_from': item.date_from,
                    'date_to': item.date_to,
                    'holiday': item.holiday_status_id.name,

                })
            else:
                docs.append({
                    'employee': item.employee_id.name,
                    'department': item.department_id.name,
                    'job': item.employee_id.job_id.name,
                    'number_of_days': item.number_of_days_temp,
                    'holiday_status_id': item.holiday_status_id.id,
                    'date_from': item.date_from,
                    'date_to': item.date_to,
                    'holiday': item.holiday_status_id.name,

                })

        return {
            'doc_ids': data['ids'],
            'doc_model': data['model'],
            'date_start': date_start.strftime(DATE_FORMAT),
            'date_end': (date_end - timedelta(days=1)).strftime(DATE_FORMAT),
            'docs': docs,
        }


class HrTerminationJobParseXlsx(models.AbstractModel):
    _name = "report.hr_base_reports.action_leaves_report_xlsx"
    _description = "XLSX Action Leaves Report"
    _inherit = 'report.report_xlsx.abstract'

    @api.model
    def generate_xlsx_report(self, workbook, data, objs):
        date_start = datetime.strptime(data['form']['date_start'], DATETIME_FORMAT)
        date_end = datetime.strptime(data['form']['date_end'], DATETIME_FORMAT) + timedelta(days=1)
        leave_type_id = data['form']['leave_type_id']
        job_id = data['form']['job_id']

        docs = []

        if leave_type_id:
            leaves = self.env['hr.holidays'].search([
                ('date_from', '>=', date_start.strftime(DATETIME_FORMAT)),
                ('date_to', '<', date_end.strftime(DATETIME_FORMAT)), ('type', '=', 'remove'),
                ('state', '!=', 'refuse'),
                ('holiday_status_id', '=', leave_type_id)])
        else:
            leaves = self.env['hr.holidays'].search([
                ('date_from', '>=', date_start.strftime(DATETIME_FORMAT)),
                ('date_to', '<', date_end.strftime(DATETIME_FORMAT)), ('type', '=', 'remove'),
                ('state', '!=', 'refuse')])

        for item in leaves:
            if item.holiday_status_id.id == leave_type_id or item.employee_id.job_id.id == job_id:
                docs.append({
                    'employee': item.employee_id.name,
                    'department': item.department_id.name,
                    'job': item.employee_id.job_id.name,
                    'number_of_days': item.number_of_days_temp,
                    'holiday_status_id': item.holiday_status_id.id,
                    'date_from': item.date_from,
                    'date_to': item.date_to,
                    'holiday': item.holiday_status_id.name,

                })
            else:
                docs.append({
                    'employee': item.employee_id.name,
                    'department': item.department_id.name,
                    'job': item.employee_id.job_id.name,
                    'number_of_days': item.number_of_days_temp,
                    'holiday_status_id': item.holiday_status_id.id,
                    'date_from': item.date_from,
                    'date_to': item.date_to,
                    'holiday': item.holiday_status_id.name,

                })

        sheet = workbook.add_worksheet('Holidays Of Employees')
        format1 = workbook.add_format(
            {'font_size': 10, 'bottom': True, 'right': True, 'left': True, 'top': True, 'align': 'center',
             'bold': True})
        format2 = workbook.add_format(
            {'font_size': 10, 'bottom': True, 'right': True, 'left': True, 'top': True, 'align': 'center',
             'bold': True})
        format2.set_align('center')
        format2.set_align('vcenter')
        format1.set_font_color('black')
        format1.set_fg_color('#e6e6e6')
        format2.set_font_color('#464dbb')
        format2.set_fg_color('#e6e6ff')

        sheet.write('A3:A3', _('Employee'), format2)
        sheet.write('B3:B3',_('Department') , format2)
        sheet.write('C3:C3', _('Holiday Type'), format2)
        sheet.write('D3:D3', _('Start Date'), format2)
        sheet.write('E3:E3', _('End Date'), format2)
        sheet.write('F3:F3', _('Number of days'), format2)

        sheet.set_column('A:A', 20)
        sheet.set_column('B:B', 20)
        sheet.set_column('C:C', 20)
        sheet.set_column('D:D', 20)
        sheet.set_column('E:E', 20)
        sheet.set_column('F:F', 20)

        row = 3
        col = 0
        for line in docs:
            row += 1
            sheet.write(row, col, line['employee'], format1)
            sheet.write(row, col + 1, line['department'], format1)
            sheet.write(row, col + 2, line['holiday'], format1)
            sheet.write(row, col + 3, line['date_from'], format1)
            sheet.write(row, col + 4, line['date_to'], format1)
            sheet.write(row, col + 5, line['number_of_days'], format1)
