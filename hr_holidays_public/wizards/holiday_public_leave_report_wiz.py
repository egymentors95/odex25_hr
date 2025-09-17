# -*- coding: utf-8 -*-

import collections
from odoo import api, fields, models, _


class PublicLeaveReport(models.TransientModel):
    _name = "public.leave.report"
    _description = "Public Leave Report"

    # Fields remain the same as before
    from_date = fields.Date(string='From Date')
    to_date = fields.Date(string='To Date')
    employee_ids = fields.Many2many(comodel_name='hr.employee', string='Employees')
    department_ids = fields.Many2many(comodel_name='hr.department', string='Department')
    lave_type_ids = fields.Many2many(comodel_name='hr.holidays.status', string='Leave Type')
    type = fields.Selection(selection=[('all', 'All'), ('specified', 'By Employee')],
                            default='specified', string='Type')
    report_type = fields.Selection([('leave_cost', 'Leave Cost'), ('leave', 'Leave'), ('leave_balance', 'Leave Balance')])

    @api.onchange('department_ids')
    def get_department_employee(self):
        if self.department_ids:
            emps = self.department_ids.mapped('employee_ids').ids
            return {'domain': {'employee_ids': [('id', 'in', emps), ('state', '=', 'open')]}}
        else:
            return {'domain': {'employee_ids': [('id', '!=', False), ('state', '=', 'open')]}}

    def _prepare_report_data(self):
        """ Helper method to apply filters based on report_type. """

        # If employee_ids is empty, get all employees
        employees = self.employee_ids
        if not employees:
            if self.department_ids:
                # If department_ids is specified, filter employees by these departments
                employees = self.env['hr.employee'].search([
                    ('department_id', 'in', self.department_ids.ids),
                    ('state', '=', 'open')
                ])
            else:
                # No department filter, retrieve all employees
                employees = self.env['hr.employee'].search([('state', '=', 'open')])

        data = {
            'employee_ids': employees.ids,
            'department_ids': self.department_ids.ids,
        }

        if self.report_type == 'leave':
            data.update({
                'from_date': str(self.from_date),
                'to_date': str(self.to_date),
                'type': self.type,
                'leave_type_ids': self.lave_type_ids.ids,
            })
        elif self.report_type == 'leave_balance':
            data.update({
                'leave_type_ids': self.lave_type_ids.ids,
            })

        return data

    def print_report(self):
        data = {
            'ids': self.ids,
            'model': self._name,
            'form': self._prepare_report_data(),
        }

        if self.report_type == 'leave_cost':
            return self.env.ref('hr_holidays_public.public_leave_cost_action_report').report_action(self, data=data)
        elif self.report_type == 'leave_balance':
            return self.env.ref('hr_holidays_public.public_leave_balance_action_report').report_action(self, data=data)
        else:
            return self.env.ref('hr_holidays_public.public_leave_action_report').report_action(self, data=data)

    def print_excel_report(self):
        data = {
            'ids': self.ids,
            'model': self._name,
            'form': self._prepare_report_data(),
        }

        if self.report_type == 'leave_cost':
            return self.env.ref('hr_holidays_public.public_leave_cost_action_report_xls').report_action(self, data=data)
        elif self.report_type == 'leave_balance':
            return self.env.ref('hr_holidays_public.public_leave_balance_action_report_xls').report_action(self, data=data)
        else:
            return self.env.ref('hr_holidays_public.public_leave_xls').report_action(self, data=data, config=False)


class ReportHolidayPublic(models.AbstractModel):
    _name = 'report.hr_holidays_public.public_report_temp'
    _description = 'Public Report'

    def get_value(self, data):
        type = data['form']['type']
        employee_ids = data['form']['employee_ids']
        leave_type_ids = data['form']['leave_type_ids']
        from_date = data['form']['from_date']
        to_date = data['form']['to_date']
        data = []
        total = {'total': {}, 'sum': 0.0}
        holidays_ids = self.env['hr.holidays'].search([('employee_id', 'in', employee_ids),
                                                       ('holiday_status_id', 'in', leave_type_ids),
                                                       ('date_from', '>=', from_date),
                                                       ('date_from', '<=', to_date), ('state', '=', 'validate1'),
                                                       ('type', '=', 'remove')])
        total_of_all_leave = 0.0
        for holiday in holidays_ids:
            if holiday.employee_id.country_id.code == 'SA':
                iqama_number = holiday.employee_id.saudi_number.saudi_id
            else:
                iqama_number = holiday.employee_id.iqama_number.iqama_id
            data.append({
                'employee_id': holiday.employee_id.name,
                'iqama_number': iqama_number,
                'nationality': holiday.employee_id.country_id.name,
                'job': holiday.employee_id.job_id.name,
                'department': holiday.employee_id.department_id.name if not holiday.employee_id.department_id.parent_id else holiday.employee_id.department_id.parent_id.name,
                'start_day_work': holiday.employee_id.first_hiring_date,
                'end_day_work': holiday.employee_id.leaving_date,
                'leave_count': holiday.employee_id.leaves_count,
                'remaining_leave': holiday.employee_id.leaves_count - holiday.number_of_days_temp,
                'leave_type_name': holiday.holiday_status_id.name,
                'leave_start_date': holiday.date_from,
                'leave_end_date': holiday.date_to,
                'number_of_days': holiday.number_of_days_temp,
                'holiday_status': holiday.holiday_status_id
            })
            total_of_all_leave += holiday.number_of_days_temp
            if type == 'all':
                name = holiday.holiday_status_id.name
                if name not in total['total']:
                    total['total'][name] = holiday.number_of_days_temp
                else:
                    total['total'][name] += holiday.number_of_days_temp
        total['sum'] = total_of_all_leave
        mykey = []
        if type == 'specified':
            final_dic = {}
            key_list = []
            total_list = []
            final_total = {}
            total_leave_dic = {}
            employees = holidays_ids.mapped('employee_id.name')
            leave_types = holidays_ids.mapped('holiday_status_id')
            for emp in employees:
                for leave in leave_types:
                    list_cat = holidays_ids.filtered(lambda r: r.employee_id.name == emp and r.holiday_status_id == leave)
                    total = sum(list_cat.mapped('number_of_days_temp'))
                    total_list.append({'employee_id': emp, 'leave_name': leave.name, 'total': total})
                list_tot = holidays_ids.filtered(lambda r: r.employee_id.name == emp)
                total_emp_leave = sum(list_tot.mapped('number_of_days_temp'))
                total_leave_dic[emp] = total_emp_leave
            grouped = collections.defaultdict(list)
            tot_grouped = collections.defaultdict(list)
            for item in data:
                grouped[item['employee_id']].append(item)
            for key, value in grouped.items():
                final_dic[key] = list(value)
                key_list.append(key)
            for item in total_list:
                tot_grouped[item['employee_id']].append(item)
            for key, value in tot_grouped.items():
                final_total[key] = list(value)
            mykey = list(dict.fromkeys(key_list))
            return final_dic, mykey, final_total, total_leave_dic
        else:
            return data, mykey, total, ''

    #
    @api.model
    def _get_report_values(self, docids, data=None):
        final_dic, mykey, total, total_leave = self.get_value(data)
        start_date = data['form']['from_date']
        end_date = data['form']['to_date']
        type = data['form']['type']
        return {
            'doc_ids': data['ids'],
            'doc_model': data['model'],
            'date_start': start_date,
            'date_end': end_date,
            'type': type,
            'data': final_dic,
            'key': mykey,
            'total': total,
            'total_leave': total_leave,
        }


class HolidayReportXls(models.AbstractModel):
    _name = 'report.hr_holidays_public.public_leave_xls'
    _description = 'XLSX Public leave Report '

    _inherit = 'report.report_xlsx.abstract'

    def generate_xlsx_report(self, workbook, data, datas):
        x = self.env['report.hr_holidays_public.public_report_temp']
        final_dic, mykey, total, total_leave = ReportHolidayPublic.get_value(x, data)
        start_date = data['form']['from_date']
        end_date = data['form']['to_date']
        type = data['form']['type']
        sheet = workbook.add_worksheet(U'Holiday Report')
        sheet.right_to_left()
        format2 = workbook.add_format(
            {'font_size': 10, 'bottom': True, 'right': True, 'left': True, 'top': True, 'align': 'center',
             'bold': True})
        format2.set_align('center')
        format2.set_align('vcenter')
        if type == 'all':
            sheet.merge_range('D3:G3', _("Leave Report"), format2)
            sheet.write(6, 2, _('Name'), format2)
            sheet.set_column('C:C', 20)
            sheet.write(6, 3, _('Iqama'), format2)
            sheet.set_column('D:D', 20)
            sheet.write(6, 4, _('Nationality'), format2)
            sheet.set_column('E:E', 20)
            sheet.write(6, 5, _('Job'), format2)
            sheet.set_column('F:F', 20)
            sheet.write(6, 6, _("Department"), format2)
            sheet.set_column('G:G', 20)
            sheet.write(6, 7, _("Working begin Start Date"), format2)
            sheet.set_column('H:H', 20)
            sheet.write(6, 8, _("Holiday Type"), format2)
            sheet.set_column('I:I', 20)
            sheet.write(6, 9, _("Holiday Start"), format2)
            sheet.set_column('J:J', 20)
            sheet.write(6, 10, _("Holiday End"), format2)
            sheet.set_column('K:K', 20)
            sheet.write(6, 11, _("Number of Days"), format2)
            sheet.set_column('L:L', 10)
            # sheet.write(6, 12, _("Leave count"), format2)
            # sheet.set_column('M:M', 10)
            sheet.write(6, 12, _("New Leave Balance"), format2)
            sheet.set_column('M:M', 20)
            row = 6
            for line in final_dic:
                row += 1
                sheet.write(row, 2, line['employee_id'], format2)
                sheet.write(row, 3, line['iqama_number'], format2)
                sheet.write(row, 4, line['nationality'], format2)
                sheet.write(row, 5, line['job'], format2)
                sheet.write(row, 6, line['department'], format2)
                sheet.write(row, 7, line['start_day_work'].strftime('%d/%m/%Y'), format2)
                sheet.write(row, 8, line['leave_type_name'], format2)
                sheet.write(row, 9, line['leave_start_date'].strftime('%d/%m/%Y'), format2)
                sheet.write(row, 10, line['leave_end_date'].strftime('%d/%m/%Y'), format2)
                sheet.write(row, 11, line['number_of_days'], format2)
                # sheet.write(row, 12, line['leave_count'], format2)
                sheet.write(row, 12, line['remaining_leave'], format2)
            #
            tot_row = row + 3
            x = tot_row
            z = 'C' + str(x)
            y = 'E' + str(x)
            sheet.merge_range('%s:%s' % (z, y), _("Leave Total"), format2)
            new = tot_row + 1
            n = 2
            for tot in total['total']:
                sheet.set_column('C:C', 20)
                sheet.write(x, n, _(tot), format2)
                sheet.write(new, n, total['total'][tot], format2)
                n += 1
            sheet.write(new + 1, 2, _('Total'), format2)
            sheet.write(new + 2, 2, total['sum'], format2)
            sheet.merge_range('B4:C4', _("From date"), format2)
            sheet.merge_range('F4:G4', _("To date"), format2)
            sheet.write(3, 3, str(start_date)[0:10], format2)
            sheet.write(3, 7, str(end_date)[0:10], format2)
        else:
            row = 6
            for key in mykey:
                n = 1
                size = len(final_dic[key])
                tot_size = len(total[key])
                sheet.merge_range('D3:G3', _("Leave Report"), format2)
                sheet.merge_range('B4:C4', _("From date"), format2)
                sheet.merge_range('F4:G4', _("To date"), format2)
                sheet.write(3, 3, str(start_date)[0:10], format2)
                sheet.write(3, 7, str(end_date)[0:10], format2)
                sheet.write(row - 2, n, _('Name'), format2)
                sheet.set_column('B:B', 16)
                sheet.set_column('C:C', 16)
                sheet.set_column('D:D', 16)
                sheet.write(row - 2, n + 2, _('Iqama'), format2)
                sheet.write(row - 2, n + 4, _('Nationality'), format2)
                sheet.set_column('E:E', 10)
                sheet.set_column('F:F', 10)
                sheet.set_column('G:G', 10)
                sheet.set_column('H:H', 10)
                sheet.set_column('I:I', 10)
                sheet.set_column('J:J', 10)
                sheet.set_column('K:K', 16)
                sheet.set_column('L:L', 16)
                sheet.set_column('M:M', 16)
                sheet.set_column('N:N', 16)
                sheet.set_column('O:O', 16)
                sheet.set_column('P:P', 16)
                sheet.set_column('Q:Q', 16)
                sheet.write(row - 2, n + 6, _('Job'), format2)
                sheet.write(row - 2, n + 8, _('Department'), format2)
                sheet.write(row - 2, n + 10, _('Working begin Start Date'), format2)
                # sheet.write(row-2, n + 12, _('End work day'), format2)
                sheet.write(row - 2, n + 12, _('New Leave Balance'), format2)
                sheet.write(row, n, _('Holiday Type'), format2)
                sheet.write(row, n + 1, _('Holiday Start'), format2)
                sheet.write(row, n + 2, _('Holiday End'), format2)
                sheet.write(row, n + 3, _('Number of Days'), format2)
                data_row = row + 1
                for line in final_dic[key]:
                    sheet.write(row - 2, n + 1, line['employee_id'], format2)
                    sheet.write(row - 2, n + 3, line['iqama_number'], format2)
                    sheet.write(row - 2, n + 5, line['nationality'], format2)
                    sheet.write(row - 2, n + 7, line['job'], format2)
                    sheet.write(row - 2, n + 9, line['department'], format2)
                    sheet.write(row - 2, n + 11, line['start_day_work'], format2)
                    # sheet.write(row - 2, n + 13, line['end_day_work'], format2)
                    sheet.write(row - 2, n + 13, line['remaining_leave'], format2)
                    sheet.write(data_row, n, line['leave_type_name'], format2)
                    sheet.write(data_row, n + 1, line['leave_start_date'].strftime('%d/%m/%Y'), format2)
                    sheet.write(data_row, n + 2, line['leave_end_date'].strftime('%d/%m/%Y'), format2)
                    sheet.write(data_row, n + 3, line['number_of_days'], format2)
                    data_row += 1
                # for tot in total[key]:
                #     sheet.write(data_row+size, n, tot['leave_name'], format2)
                #     sheet.write(data_row+size, n+1, tot['total'], format2)
                #     size += 1
                sheet.write(data_row, n, _('Total'), format2)
                sheet.write(data_row, n + 1, total_leave[key], format2)
                n += 1
                row += size + 3 + tot_size
