# -*- coding: utf-8 -*-

from datetime import datetime, date
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from dateutil.relativedelta import relativedelta


class OvertimeReport(models.TransientModel):

    _name = 'overtime.report'
    _description = 'Overtime Report'

    employee_ids = fields.Many2many('hr.employee')
    department_ids = fields.Many2many('hr.department')
    overtime_place = fields.Selection(
        [('inside', 'Inside'), ('outside', 'Outside')], default='inside')
    date_from = fields.Date()
    date_to = fields.Date()

    @api.onchange('date_from')
    def check_date_from(self):
        if self.date_from :
            self.date_to = fields.Date.from_string(self.date_from)+relativedelta(months=+1, day=1, days=-1)

    @api.onchange('department_ids')
    def _onchange_department_ids(self):
        if self.department_ids:
            employee_ids = self.department_ids.mapped('employee_ids').ids
            return {'domain': {'employee_ids': [('id', 'in', employee_ids), ('state', '=', 'open')]}}
        else:
            return {
                'domain': {'employee_ids': [('id', '!=', False), ('state', '=', 'open')]},
                'value': {'employee_ids': [(6, 0, [])]}
            }


    def action_print(self):
        if self.department_ids and not self.employee_ids:
            employee_ids = self.env['hr.employee'].search([('department_id', 'in', self.department_ids.ids)]).ids
        elif self.employee_ids:
            employee_ids = self.employee_ids.ids
        else:
            employee_ids = self.env['hr.employee'].search([]).ids
        data = {
            'employee_ids': employee_ids,
            'date_from': self.date_from,
            'date_to': self.date_to,
            'overtime_place': self.overtime_place
        }
        return self.env.ref('hr_base_reports.action_overtime_report').report_action([], data=data)


    def print_excel_report(self):
        if self.department_ids and not self.employee_ids:
            employee_ids = self.env['hr.employee'].search([('department_id', 'in', self.department_ids.ids)]).ids
        elif self.employee_ids:
            employee_ids = self.employee_ids.ids
        else:
            employee_ids = self.env['hr.employee'].search([]).ids
        data = {
            'ids': self.ids,
            'model': self._name,
            'form': {
                'employee_ids': employee_ids,
                'date_from': self.date_from,
                'date_to': self.date_to,
                'overtime_place': self.overtime_place
            },
        }

        return self.env.ref('hr_base_reports.overtime_action_report_xls').report_action(self, data=data)


class OvertimeReportView(models.AbstractModel):

    _name = 'report.hr_base_reports.overtime_report'

    @api.model
    def _get_report_values(self, docids, data=None):
        report_values = []
        employee_ids = data['employee_ids']
        date_from = data['date_from']
        date_to = data['date_to']
        overtime_place = data['overtime_place']
        overtime_domain = [('date_from', '>=', date_from), ('date_from', '<=', date_to),
                           ('date_to', '<=', date_to), ('date_to', '>=', date_from),
                           ('state', 'not in', ['draft', 'refused']),
                           ('overtime_plase', '=', overtime_place)]
        for employee in employee_ids:
            employee_lines = []
            over_time_workdays_hours = 0
            over_time_vacation_hours = 0
            price_hour = 0
            daily_amount = 0
            vacation_amount = 0

            for record in self.env['employee.overtime.request'].search(overtime_domain):
                for line in record.line_ids_over_time.filtered(lambda l: l.employee_id.id == employee):
                    employee_lines.append(line)
            if employee_lines:
                for l in employee_lines:
                    daily_hourly_rate = l[0].daily_hourly_rate
                    holiday_hourly_rate = l[0].holiday_hourly_rate
                    over_time_workdays_hours += l.over_time_workdays_hours
                    over_time_vacation_hours += l.over_time_vacation_hours

                    daily_amount += l.over_time_workdays_hours*l.daily_hourly_rate
                    vacation_amount += l.over_time_vacation_hours*l.holiday_hourly_rate
                    price_hour += l.price_hour
                report_values.append({
                        'employee_id': self.env['hr.employee'].browse(employee),
                        'daily_hourly_rate': daily_hourly_rate,
                        'holiday_hourly_rate': holiday_hourly_rate,
                        'over_time_workdays_hours': over_time_workdays_hours,
                        'over_time_vacation_hours': over_time_vacation_hours,

                        'daily_amount': daily_amount,
                        'vacation_amount': vacation_amount,
                        'price_hour': price_hour,
                    })
        if len(report_values) == 0:
            raise ValidationError(_("There is no Data"))

        return {
            'docs': report_values,
            'doc': self,
            'overtime_place': _('Inside') if overtime_place == 'inside' else _('Outside'),
            'date_from': date_from,
            'date_to': date_to,
            'print_date': datetime.now().date()
        }


class OvertimeReportXls(models.AbstractModel):
    _name = 'report.hr_base_reports.overtime_action_report_xls'
    _inherit = 'report.report_xlsx.abstract'

    def generate_xlsx_report(self, workbook, data, datas):
        x = self.env['report.hr_base_reports.overtime_report']
        result = OvertimeReportView._get_report_values(x, False, data['form'])
        start_date = data['form']['date_from']
        end_date = data['form']['date_to']
        sheet = workbook.add_worksheet(U'Overtime Report')
        sheet.right_to_left()
        format2 = workbook.add_format(
            {'font_size': 10, 'bottom': True, 'right': True, 'left': True, 'top': True, 'align': 'center',
             'bold': True})
        format2.set_align('center')
        format2.set_align('vcenter')
        sheet.merge_range('D3:G3', _("Overtime Report"), format2)
        sheet.merge_range('B4:C4', _("From date"), format2)
        sheet.merge_range('F4:G4', _("To date"), format2)
        sheet.write(3, 3, str(start_date)[0:10], format2)
        sheet.write(3, 7, str(end_date)[0:10], format2)
        row = 6
        sheet.merge_range(row, 3, row, 6, result['overtime_place'], format2)
        row += 1
        sheet.write(row, 0, _('Sequence'), format2)
        sheet.set_column('A:A', 10)
        sheet.write(row, 1, _('Iqama'), format2)
        sheet.set_column('B:B', 20)
        sheet.write(row, 2, _('Name'), format2)
        sheet.set_column('C:C', 20)
        sheet.write(row, 3, _('Job'), format2)
        sheet.set_column('D:D', 20)
        sheet.write(row, 4, _("Salary"), format2)
        sheet.set_column('E:E', 20)
        sheet.merge_range(row, 5, row, 6,  _("Hour Rate"), format2)
        sheet.set_column('F:F', 20)
        sheet.set_column('G:G', 20)
        sheet.set_column('H:H', 15)
        sheet.merge_range(row, 7, row, 11, _("Effective Hours"), format2)
        row += 1
        sheet.merge_range(row, 0, row, 4, '', format2)
        sheet.write(row, 5, _("Regular"), format2)
        sheet.write(row, 6, _("Holiday"), format2)
        sheet.write(row, 7, _("Regular"), format2)
        sheet.write(row, 8, _("Holiday"), format2)
        sheet.write(row, 9, _("Total Hours"), format2)
        sheet.merge_range(row, 9, row, 10, _("Hour Rate"), format2)
        sheet.write(row, 11, _("Total"), format2)
        sequence = 1
        total = 0
        total_daily_hours = 0
        total_holiday_hours = 0
        for line in result['docs']:
            row += 1
            sheet.write(row, 0, sequence, format2)
            if line['employee_id'].country_id.code == 'SA':
                sheet.write(row, 1, line['employee_id'].saudi_number.saudi_id, format2)
            else:
                sheet.write(row, 1, line['employee_id'].iqama_number.iqama_id, format2)
            sheet.write(row, 2, line['employee_id'].name, format2)
            sheet.write(row, 3, line['employee_id'].job_id.name, format2)
            sheet.write(row, 4, "{0:.2f}".format(line['employee_id'].contract_id.total_allowance), format2)
            sheet.write(row, 5, "{0:.2f}".format(line['daily_hourly_rate']), format2)
            sheet.write(row, 6,  "{0:.2f}".format(line['holiday_hourly_rate']), format2)
            sheet.write(row, 7, line['over_time_workdays_hours'], format2)
            sheet.write(row, 8, line['over_time_vacation_hours'], format2)
            #sheet.write(row, 9, line['over_time_workdays_hours'] * line['daily_hourly_rate'], format2)
            #sheet.write(row, 10, line['over_time_vacation_hours'] * line['holiday_hourly_rate'], format2)
            #sheet.write(row, 11, line['over_time_workdays_hours'] * line['daily_hourly_rate'] +
            #            line['over_time_vacation_hours'] * line['holiday_hourly_rate'], format2)
            #total_daily_hours += line['over_time_workdays_hours'] * line['daily_hourly_rate']
            #total_holiday_hours += line['over_time_vacation_hours'] * line['holiday_hourly_rate']
            #total += line['over_time_workdays_hours'] * line['daily_hourly_rate'] + line['over_time_vacation_hours'] * line['holiday_hourly_rate']

            sheet.write(row, 9, line['daily_amount'], format2)
            sheet.write(row, 10, line['vacation_amount'], format2)
            sheet.write(row, 11, line['price_hour'], format2)
            sequence += 1

            total_daily_hours += line['daily_amount']
            total_holiday_hours += line['vacation_amount']
            total  += line['price_hour']

        row += 1
        sheet.merge_range(row, 0, row, 8, _("Total"), format2)
        sheet.write(row, 9, total_daily_hours, format2)
        sheet.write(row, 10, total_holiday_hours, format2)
        sheet.write(row, 11, total, format2)

