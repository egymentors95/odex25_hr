# -*- coding: utf-8 -*-

from datetime import datetime, date
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class HRPenaltyReport(models.TransientModel):
    _name = 'hr.penalty.report'
    _description = 'HR Penalty Report'

    date_from = fields.Date()
    date_to = fields.Date()
    employee_ids = fields.Many2many('hr.employee')
    penalty_ids = fields.Many2many('hr.penalty.ss')
    punishment_ids = fields.Many2many('hr.punishment')

    @api.onchange('penalty_ids')
    def _onchange_penalty_ids(self):
        if self.penalty_ids:
            list_items = []
            for penalty_id in self.penalty_ids:
                list_items.extend(penalty_id.first_time.ids)
                list_items.extend(penalty_id.second_time.ids)
                list_items.extend(penalty_id.third_time.ids)
                list_items.extend(penalty_id.fourth_time.ids)
                list_items.extend(penalty_id.fifth_time.ids)
            return {'domain': {'punishment_ids': [('id', 'in', list(set(list_items)))]}}
        else:
            return {
                'value': {'punishment_ids': [(6, 0, [])]}
            }

    def action_print(self):
        employee_ids = self.employee_ids and self.employee_ids.ids or self.env['hr.employee'].search([]).ids
        data = {
            'employee_ids': employee_ids,
            'date_from': self.date_from,
            'date_to': self.date_to,
            'penalty_ids': self.penalty_ids.ids,
            'punishment_ids': self.punishment_ids.ids,
        }

        return self.env.ref('hr_disciplinary_tracking.action_hr_penalty_report').report_action([], data=data)

    def print_excel_report(self):
        employee_ids = self.employee_ids and self.employee_ids.ids or self.env['hr.employee'].search([]).ids
        data = {
            'ids': self.ids,
            'model': self._name,
            'form': {
                'employee_ids': employee_ids,
                'penalty_ids': self.penalty_ids.ids,
                'punishment_ids': self.punishment_ids.ids,
                'date_from': self.date_from,
                'date_to': self.date_to,
            },
        }

        return self.env.ref('hr_disciplinary_tracking.hr_penalty_action_report_xls').report_action(self, data=data)


class HRPenaltyReportView(models.AbstractModel):
    _name = 'report.hr_disciplinary_tracking.hr_penalty_report'
    _description = 'HR Penalty Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        report_values = []
        employee_ids = data['employee_ids']
        date_from = data['date_from']
        date_to = data['date_to']
        penalty_ids = data['penalty_ids']
        punishment_ids = data['punishment_ids']

        for penalty_id in penalty_ids:
            search_domain = [('date', '>=', date_from), ('date', '<=', date_to),
                             ('penalty_id', '=', penalty_id), ('punishment_id', 'in', punishment_ids),
                             ('employee_id', 'in', employee_ids), ('state', 'not in', ['draft', 'cancel'])]
            lines = self.env['hr.penalty.register'].search(search_domain)
            if lines:
                report_values.append({'penalty': self.env['hr.penalty.ss'].browse(penalty_id),
                                      'lines': lines})
        if len(report_values) == 0:
            raise ValidationError(_("There is no Data"))

        return {
            'print_date': datetime.now().date(),
            'user_name': self.env.user.name,
            'docs': report_values,
            'doc': self,
            'date_from': date_from,
            'date_to': date_to,
        }


class HRPenaltyReportXls(models.AbstractModel):
    _name = 'report.hr_disciplinary_tracking.hr_penalty_action_report_xls'
    _inherit = 'report.report_xlsx.abstract'

    def generate_xlsx_report(self, workbook, data, datas):
        x = self.env['report.hr_disciplinary_tracking.hr_penalty_report']
        result = HRPenaltyReportView._get_report_values(x, False, data['form'])
        start_date = data['form']['date_from']
        end_date = data['form']['date_to']
        sheet = workbook.add_worksheet(U'Penalty Report')
        sheet.right_to_left()
        format2 = workbook.add_format(
            {'font_size': 10, 'bottom': True, 'right': True, 'left': True, 'top': True, 'align': 'center',
             'bold': True})
        format2.set_align('center')
        format2.set_align('vcenter')
        sheet.merge_range('D3:G3', _("Penalty Report"), format2)
        sheet.merge_range('B4:C4', _("From date"), format2)
        sheet.merge_range('F4:G4', _("To date"), format2)
        sheet.write(3, 3, str(start_date)[0:10], format2)
        sheet.write(3, 7, str(end_date)[0:10], format2)
        row = 6
        for doc in result['docs']:
            sequence = 1
            sheet.merge_range(row, 3, row, 6, doc['penalty'].name, format2)
            row += 1
            sheet.write(row, 0, _('Sequence'), format2)
            sheet.set_column('A:A', 20)
            sheet.write(row, 1, _('Iqama'), format2)
            sheet.set_column('B:B', 20)
            sheet.write(row, 2, _('Name'), format2)
            sheet.set_column('C:C', 20)
            sheet.write(row, 3, _('Nationality'), format2)
            sheet.set_column('D:D', 20)
            sheet.write(row, 4, _('Job'), format2)
            sheet.set_column('E:E', 20)
            sheet.write(row, 5, _("Department"), format2)
            sheet.set_column('F:F', 20)
            sheet.write(row, 6, _("First Hiring Date"), format2)
            sheet.set_column('G:G', 20)
            sheet.write(row, 7, _("Punishment Date"), format2)
            sheet.set_column('H:H', 20)
            sheet.write(row, 8, _("Reason"), format2)
            sheet.set_column('I:I', 20)
            sheet.write(row, 9, _("Deduction"), format2)
            sheet.set_column('J:J', 20)
            for line in doc['lines']:
                row += 1
                sheet.write(row, 0, sequence, format2)
                if line.employee_id.country_id.code == 'SA':
                    sheet.write(row, 1, line.employee_id.saudi_number.saudi_id, format2)
                else:
                    sheet.write(row, 1, line.employee_id.iqama_number.iqama_id, format2)
                sheet.write(row, 2, line.employee_id.name, format2)
                sheet.write(row, 3, line.employee_id.country_id.name, format2)
                sheet.write(row, 4, line.employee_id.job_id.name, format2)
                sheet.write(row, 5, line.employee_id.department_id.name, format2)
                sheet.write(row, 6, line.employee_id.first_hiring_date, format2)
                sheet.write(row, 7, line.date, format2)
                for p in line.punishment_id:
                    sheet.write(row, 8, p.name, format2)
                sheet.write(row, 9, line.deduction_amount, format2)
                sequence += 1
            row += 2
