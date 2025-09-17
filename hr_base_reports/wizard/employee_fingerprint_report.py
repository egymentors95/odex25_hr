# -*- coding: utf-8 -*-

from datetime import datetime, timedelta
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class FingerprintReport(models.TransientModel):
    _name = 'fingerprint.report'
    _description = 'Fingerprint Report'

    employee_ids = fields.Many2many('hr.employee')
    date_from = fields.Date()
    date_to = fields.Date()
    report_type = fields.Selection([('by_employee', 'By Employee'), ('all', 'All Employees')], default='all')

    def action_print(self):
        employee_ids = self.employee_ids and self.employee_ids.ids or self.env['hr.employee'].search([]).ids
        data = {
            'employee_ids': employee_ids,
            'date_from': self.date_from,
            'date_to': self.date_to,
            'report_type': self.report_type,
        }

        return self.env.ref('hr_base_reports.action_fingerprint_report').report_action([], data=data)

    def print_excel_report(self):
        employee_ids = self.employee_ids and self.employee_ids.ids or self.env['hr.employee'].search([]).ids
        data = {
            'ids': self.ids,
            'model': self._name,
            'form': {
                'employee_ids': employee_ids,
                'date_from': self.date_from,
                'date_to': self.date_to,
                'report_type': self.report_type,
            },
        }

        return self.env.ref('hr_base_reports.fingerprint_action_report_xls').report_action(self, data=data)


class FingerprintReportView(models.AbstractModel):
    _name = 'report.hr_base_reports.fingerprint_report'
    _description = 'Fingerprint Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        report_values = []
        employee_ids = data['employee_ids']
        date_from = data['date_from']
        date_to = data['date_to']
        report_type = data['report_type']

        def divide_chunks(l, n):
            # looping till length l
            for i in range(0, len(l), n):
                yield l[i:i + n]

        def daterange(start_date, end_date):
            for n in range(
                    int((fields.Datetime.from_string(date_to) - fields.Datetime.from_string(date_from)).days) + 1):
                yield start_date + timedelta(n)

        for employee_id in employee_ids:

            tran_date = []
            for single_date in daterange(fields.Datetime.from_string(date_from).date(),
                                         fields.Datetime.from_string(date_to).date()):
                transactions = []
                transaction_ids = self.env['hr.attendance.transaction'].search([
                    ('employee_id', '=', employee_id), ('date', '=', single_date)])
                for transaction in transaction_ids:
                    sign_in_hour, sign_in_minute = divmod(transaction.sign_in, 1)
                    sign_in_minute *= 60
                    sign_out_hour, sign_out_minute = divmod(transaction.sign_out, 1)
                    sign_out_minute *= 60
                    transactions.append({'date': transaction.date,
                                         'sign_in': transaction.sign_in,
                                         'sign_out': transaction.sign_out,
                                         'sign_in_hour': sign_in_hour,
                                         'sign_in_minute': sign_in_minute,
                                         'sign_out_hour': sign_out_hour,
                                         'sign_out_minute': sign_out_minute,
                                         'working_hours': transaction.office_hours,
                                         'lateness': transaction.lateness,
                                         'early_exit': transaction.early_exit,
                                         'is_absent': transaction.is_absent
                                         })
                tran_date.append({'date': single_date,
                                  'transaction_ids': transactions})
            if report_type == 'by_employee':
                tran_date = list(divide_chunks(tran_date, 5))

            report_values.append({'employee_id': self.env['hr.employee'].browse(employee_id),
                                  'transactions': tran_date})
        if len(report_values) == 0:
            raise ValidationError(_("There is no Data"))

        return {
            'print_date': datetime.now().date(),
            'user_name': self.env.user.name,
            'report_type': report_type,
            'date_from': date_from,
            'date_to': date_to,
            'employee_ids': employee_ids,
            'docs': report_values,
            'doc': self,
        }


class FingerprintReportXls(models.AbstractModel):
    _name = 'report.hr_base_reports.fingerprint_action_report_xls'
    _description = 'XLSX Fingerprint Report'
    _inherit = 'report.report_xlsx.abstract'

    def generate_xlsx_report(self, workbook, data, datas):
        x = self.env['report.hr_base_reports.fingerprint_report']
        result = FingerprintReportView._get_report_values(x, False, data['form'])
        start_date = data['form']['date_from']
        end_date = data['form']['date_to']
        sheet = workbook.add_worksheet(U'Fingerprint Report')
        sheet.right_to_left()
        format2 = workbook.add_format(
            {'font_size': 10, 'bottom': True, 'right': True, 'left': True, 'top': True, 'align': 'center',
             'bold': True})
        if result['report_type'] == 'all':
            row = 3
            for doc in result['docs']:
                format2.set_align('center')
                format2.set_align('vcenter')
                sheet.merge_range(row, 2, row, 6, _("Fingerprint Report For ") + doc['employee_id'].name, format2)
                row += 1
                sheet.merge_range(row, 1, row, 3, _("From date"), format2)
                sheet.merge_range(row, 5, row, 6, _("To date"), format2)
                sheet.write(row, 3, str(start_date)[0:10], format2)
                sheet.write(row, 7, str(end_date)[0:10], format2)
                row += 1
                sheet.write(row, 0, _('Day'), format2)
                sheet.set_column('A:A', 10)
                sheet.write(row, 1, _('Date'), format2)
                sheet.set_column('B:B', 20)
                sheet.merge_range(row, 2, row, 4, _('Sign In'), format2)
                sheet.set_column('C:C', 20)
                sheet.merge_range(row, 5, row, 7, _('Sign Out'), format2)
                sheet.set_column('D:D', 20)
                sheet.write(row, 8, _("Total Working Hours"), format2)
                sheet.set_column('E:E', 15)
                sheet.write(row, 9, _("Total Lateness"), format2)
                sheet.set_column('F:F', 15)
                sheet.set_column('G:G', 20)
                sheet.set_column('H:H', 15)
                sheet.set_column('I:I', 20)
                sheet.set_column('J:J', 20)
                sheet.set_column('K:K', 20)
                row += 1
                sheet.merge_range(row, 0, row, 1, '', format2)
                sheet.write(row, 2, _("Type"), format2)
                sheet.merge_range(row, 3, row, 4, _("Time"), format2)
                sheet.write(row, 5, _("Type"), format2)
                sheet.merge_range(row, 6, row, 7, _("Time"), format2)
                sheet.merge_range(row, 8, row, 9, '', format2)
                row += 1
                sheet.merge_range(row, 0, row, 1, '', format2)
                sheet.write(row, 3, '', format2)
                sheet.write(row, 3, _("Minute"), format2)
                sheet.write(row, 4, _("Hour"), format2)
                sheet.write(row, 5, '', format2)
                sheet.write(row, 6, _("Minute"), format2)
                sheet.write(row, 7, _("Hour"), format2)
                sheet.merge_range(row, 8, row, 9, '', format2)
                sequence = 1
                total_working_hours = 0
                total_lateness = 0
                row += 1
                for line in doc['transactions']:
                    if line['transaction_ids']:
                        for tr in line['transaction_ids']:
                            sheet.write(row, 0, sequence, format2)
                            sheet.write(row, 1, tr['date'], format2)
                            sheet.write(row, 2, tr['sign_in_hour'], format2)
                            sheet.write(row, 3, tr['sign_in_minute'], format2)
                            sheet.write(row, 4, '', format2)
                            sheet.write(row, 5, tr['sign_out_hour'], format2)
                            sheet.write(row, 6, tr['sign_out_minute'], format2)
                            sheet.write(row, 7, '', format2)
                            sheet.write(row, 8, tr['working_hours'], format2)
                            sheet.write(row, 9, tr['lateness'], format2)
                            sequence += 1
                            row += 1
                            total_working_hours += tr['working_hours']
                            total_lateness += tr['lateness']

                    else:
                        sheet.write(row, 0, sequence, format2)
                        sheet.write(row, 1, str(line['date']), format2)
                        sequence += 1
                        row += 1

                row += 1
                sheet.merge_range(row, 0, row, 7, _("Total"), format2)
                sheet.write(row, 8, total_working_hours, format2)
                sheet.write(row, 9, total_lateness, format2)
                row += 2
        else:
            row = 3
            for doc in result['docs']:
                total_absence = 0
                total_lateness = 0
                total_early_exit = 0
                row += 1
                format2.set_align('center')
                format2.set_align('vcenter')
                sheet.set_column('A:A', 15)
                sheet.set_column('B:B', 15)
                sheet.set_column('C:C', 15)
                sheet.set_column('D:D', 15)
                sheet.set_column('E:E', 15)
                sheet.set_column('F:F', 15)
                sheet.set_column('G:G', 15)
                sheet.set_column('H:H', 15)
                sheet.set_column('I:I', 20)
                sheet.set_column('J:J', 20)
                sheet.set_column('K:K', 20)
                sheet.merge_range(row, 2, row, 6, _("Fingerprint Report"), format2)
                row += 1
                sheet.merge_range(row, 1, row, 2, _("Employee"), format2)
                sheet.write(row, 3, doc['employee_id'].name, format2)
                sheet.merge_range(row, 5, row, 6, _("Number"), format2)
                if doc['employee_id'].country_id.code == 'SA':
                    sheet.write(row, 7, doc['employee_id'].saudi_number.saudi_id, format2)
                else:
                    sheet.write(row, 7, doc['employee_id'].iqama_number.iqama_id, format2)
                row += 1
                sheet.merge_range(row, 1, row, 2, _("From date"), format2)
                sheet.merge_range(row, 5, row, 6, _("To date"), format2)
                sheet.write(row, 3, str(start_date)[0:10], format2)
                sheet.write(row, 7, str(end_date)[0:10], format2)
                row += 1
                for i in range(0, len(doc['transactions'])):
                    row += 1
                    index = 1
                    for j in doc['transactions'][i]:
                        if j['transaction_ids']:
                            for tr in j['transaction_ids']:
                                sheet.write(row, index, tr['date'], format2)
                                sheet.write(row + 1, index, str(tr['sign_in']) + '\n' + str(tr['sign_out']), format2)
                                sheet.set_row(row + 1, 25)
                                total_lateness += tr['lateness']
                                total_early_exit += tr['early_exit']
                                if tr['is_absent']:
                                    total_absence += 1
                        else:
                            sheet.write(row, index, str(j['date']), format2)
                            sheet.write(row + 1, index, '', format2)
                        index += 1
                    row += 1
                row += 2
                sheet.write(row, 1, _('Date'), format2)
                sheet.write(row, 2, _('Total Lateness'), format2)
                sheet.write(row, 3, _('Total Early Exit'), format2)
                sheet.write(row, 4, _('Total Absence'), format2)
                row += 1
                sheet.write(row, 1, str(result['print_date']), format2)
                sheet.write(row, 2, total_lateness, format2)
                sheet.write(row, 3, total_early_exit, format2)
                sheet.write(row, 4, total_absence, format2)
                row += 1