# -*- coding: utf-8 -*-

from datetime import datetime, date
from dateutil import relativedelta
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class HrTerminationReport(models.TransientModel):
    _name = 'hr.termination.report'
    _description = 'HR Termination Report'

    employee_ids = fields.Many2many('hr.employee')
    department_ids = fields.Many2many('hr.department')
    cause_type_id = fields.Many2one('hr.termination.type')
    date_from = fields.Date()
    date_to = fields.Date()

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
            'cause_type_id': self.cause_type_id.id,
            'date_from': self.date_from,
            'date_to': self.date_to,
        }

        return self.env.ref('hr_termination.action_hr_termination_report').report_action([], data=data)

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
                'cause_type_id': self.cause_type_id.id,
                'date_from': self.date_from,
                'date_to': self.date_to,
            },
        }

        return self.env.ref('hr_termination.hr_termination_action_report_xls').report_action(self, data=data)


class HrTerminationReportView(models.AbstractModel):
    _name = 'report.hr_termination.hr_termination_report'

    @api.model
    def _get_report_values(self, docids, data=None):
        report_values = []
        employee_ids = data['employee_ids']
        date_from = data['date_from']
        date_to = data['date_to']
        cause_type_id = data['cause_type_id']
        termination_domain = [('employee_id', 'in', employee_ids),
                              ('last_work_date', '>=', date_from), ('last_work_date', '<=', date_to),
                              ('cause_type', '=', cause_type_id),
                              ('state', 'not in', ['draft', 'refused'])]

        for record in self.env['hr.termination'].search(termination_domain):
            year = datetime.strptime(str(record.last_work_date), "%Y-%m-%d").year
            start_date = datetime.strptime(str(record.first_hire_date), "%Y-%m-%d")
            end_date = datetime.strptime(str(record.last_work_date), "%Y-%m-%d")
            r = relativedelta.relativedelta(end_date, start_date)
            duration = ''
            if r.years:
                duration = str(r.years) + _(' year(s) ')
            if r.months:
                duration = duration + str(r.months) + _(' month(s) ')
            if r.days:
                duration = duration + str(r.days) + _(' day(s) ')
            report_values.append({'record': record, 'year': year, 'duration': duration})

        if len(report_values) == 0:
            raise ValidationError(_("There is no Data"))

        return {
                'docs': report_values,
                'date_from': date_from,
                'date_to': date_to,
                'cause_type': self.env['hr.termination.type'].browse(cause_type_id),
                'doc': self,
            }


class HRTerminationReportXls(models.AbstractModel):
    _name = 'report.hr_termination.hr_termination_action_report_xls'
    _inherit = 'report.report_xlsx.abstract'

    def generate_xlsx_report(self, workbook, data, datas):
        x = self.env['report.hr_termination.hr_termination_report']
        result = HrTerminationReportView._get_report_values(x, False, data['form'])
        start_date = data['form']['date_from']
        end_date = data['form']['date_to']
        sheet = workbook.add_worksheet(U'Termination Report')
        sheet.right_to_left()
        format2 = workbook.add_format(
            {'font_size': 10, 'bottom': True, 'right': True, 'left': True, 'top': True, 'align': 'center',
             'bold': True})
        format2.set_align('center')
        format2.set_align('vcenter')
        sheet.merge_range('D3:G3', _("HR Termination Report"), format2)
        sheet.merge_range('B4:C4', _("From date"), format2)
        sheet.merge_range('F4:G4', _("To date"), format2)
        sheet.write(3, 3, str(start_date)[0:10], format2)
        sheet.write(3, 7, str(end_date)[0:10], format2)
        row = 6
        sheet.merge_range(row, 3, row, 6, result['cause_type'].name, format2)
        row += 1
        sheet.write(row, 0, _('Sequence'), format2)
        sheet.set_column('A:A', 20)
        sheet.write(row, 1, _('Year'), format2)
        sheet.set_column('B:B', 20)
        sheet.write(row, 2, _('Employee Number'), format2)
        sheet.set_column('C:C', 20)
        sheet.write(row, 3, _('Iqama'), format2)
        sheet.set_column('D:D', 20)
        sheet.write(row, 4, _('Name'), format2)
        sheet.set_column('E:E', 20)
        sheet.write(row, 5, _('Branch'), format2)
        sheet.set_column('F:F', 20)
        sheet.write(row, 6, _('Job'), format2)
        sheet.set_column('G:G', 20)
        sheet.write(row, 7, _("First Hiring Date"), format2)
        sheet.set_column('H:H', 20)
        sheet.write(row, 8, _("First Termination Date"), format2)
        sheet.set_column('I:I', 20)
        sheet.write(row, 9, _("Last Work Date"), format2)
        sheet.set_column('J:J', 20)
        sheet.write(row, 10, _("Duration"), format2)
        sheet.set_column('K:K', 20)
        sheet.write(row, 11, _("Total"), format2)
        sheet.set_column('L:L', 20)
        sheet.write(row, 12, _("Payment Method"), format2)
        sheet.set_column('M:M', 20)
        sequence = 1
        for line in result['docs']:
            row += 1
            sheet.write(row, 0, sequence, format2)
            sheet.write(row, 1, line['year'], format2)
            sheet.write(row, 2, line['record'].employee_id.emp_no, format2)
            if line['record'].employee_id.country_id.code == 'SA':
                sheet.write(row, 3, line['record'].employee_id.saudi_number.saudi_id, format2)
            else:
                sheet.write(row, 3, line['record'].employee_id.iqama_number.iqama_id, format2)
            sheet.write(row, 4, line['record'].employee_id.name, format2)
            sheet.write(row, 5, line['record'].department_id.name, format2)
            sheet.write(row, 6, line['record'].employee_id.job_id.name, format2)
            sheet.write(row, 7, line['record'].employee_id.first_hiring_date, format2)
            sheet.write(row, 8, line['record'].salary_date_from, format2)
            sheet.write(row, 9, line['record'].last_work_date, format2)
            sheet.write(row, 10, line['duration'], format2)
            sheet.write(row, 11, line['record'].net, format2)
            if line['record'].employee_id.payment_method == 'bank':
                sheet.write(row, 12, line['record'].employee_id.bank_code, format2)
            else:
                sheet.write(row, 12, line['record'].employee_id.payment_method, format2)
            sequence += 1
