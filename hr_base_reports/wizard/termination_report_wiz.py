# -*- coding: utf-8 -*-

import datetime
from odoo import api, fields, models, _
from odoo import exceptions
from datetime import date, timedelta, datetime as dt
from dateutil import relativedelta
from dateutil import relativedelta as rd

class TreminationReport(models.TransientModel):
    _name = "employees.cost.report"
    _description = "Employees Cost Report"

    employee_ids = fields.Many2many(comodel_name='hr.employee', string='Employees', domain="[('state','=','open')]")
    cause_type = fields.Many2one(comodel_name='hr.termination.type')
    salary_date_from = fields.Date()
    salary_date_to = fields.Date()
    end_date = fields.Date(string='End Of Service')
    allowance_ids = fields.Many2many('hr.salary.rule', domain=[('rules_type', 'in', ['house', 'salary', 'transport'])])
    type = fields.Selection(selection=[('salary', 'Salary'), ('ticket', 'Ticket'), ('leave', 'Leave'),
                                       ('termination', 'Termination'), ('all', 'All')], required=True,
                            default='all', string='Type')

    def print_report(self):
        for emp in self.employee_ids:
            if not emp.first_hiring_date:
                raise exceptions.Warning(_('Please set the First Hiring Date %s')
                                         % emp.name)
        data = {
            'ids': self.ids,
            'model': self._name,
            'form': {
                'allowance_ids': self.allowance_ids.ids,
                'cause_type': self.cause_type.id,
                'employee_ids': self.employee_ids.ids,
                'date_from': self.salary_date_from,
                'date_to': self.salary_date_to,
                'end_date': self.end_date,
            },
        }
        return self.env.ref('hr_base_reports.termination_benefits_action_report').report_action(self, data=data)

    def print_excel_report(self):
        for emp in self.employee_ids:
            if not emp.first_hiring_date:
                raise exceptions.Warning(_('Please set the First Hiring Date %s')
                                         % (emp.name))
        data = {
            'ids': self.ids,
            'model': self._name,
            'form': {
                'allowance_ids': self.allowance_ids.ids,
                'cause_type': self.cause_type.id,
                'employee_ids': self.employee_ids.ids,
                'date_from': self.salary_date_from,
                'date_to': self.salary_date_to,
                'end_date': self.end_date,
            },
        }
        return self.env.ref('hr_base_reports.termination_benefits_xls').report_action(self, data=data, config=False)


class ReportTerminationPublic(models.AbstractModel):
    _name = 'report.hr_base_reports.termination_report_temp'

    def get_cause_amount(self, first_hire_date, cause_type_name, end_date, emp):
        # Get salary rule  form cause type
        if first_hire_date:
            cause_type_amount = 0.0
            five_year_benefit = 0
            termination_per_month = 0.0
            amount = 0
            termination_model = self.env['hr.termination']
            if cause_type_name:
                start_date = datetime.datetime.strptime( str(first_hire_date), "%Y-%m-%d")
                end_date = datetime.datetime.strptime(str(end_date), "%Y-%m-%d") + timedelta(days=1)
                total_rules, amount_of_year, amount_of_month, amount_of_day, cause_type_amount = 0.0, 0.0, 0.0, 0.0, 0.0
                five_year_benefit, amount = 0, 0

                if end_date >= start_date:
                    value = relativedelta.relativedelta(end_date, start_date)
                    years = value.years
                    days = value.days
                    months = value.months
                    all_duration = months + (days / 30) + (years * 12)


                    if cause_type_name.allowance_ids and cause_type_name.termination_duration_ids:

                        # Get total for  all salary rules form cause type
                        for rule in cause_type_name.allowance_ids:
                            rule_flag = False
                            if rule_flag is False:
                                total_rules += termination_model.compute_rule(rule, emp.contract_id)

                        reward_amount = 0
                        residual = all_duration
                        line_amount = 0
                        duration_to = 0
                        # search line cause_type and get amount for each line factor
                        for line in cause_type_name.termination_duration_ids:
                            line_amount = line.amount
                            if line.date_to <= all_duration:
                                if line.amount > 0:
                                    duration_to = line.date_to - duration_to
                                    reward_amount += total_rules * (duration_to / 12) * line.factor
                                    residual = all_duration - line.date_to

                            else:
                                if line.date_to > all_duration:
                                    reward_amount += total_rules * residual / 12 * line.factor
                                    break
                                    residual = 0

                        reward_amount = reward_amount * line_amount
                        cause_type_amount = reward_amount
                        termination_per_month = (cause_type_amount/all_duration)
                        five_year = 0
                        if all_duration > 60:

                            for rec in cause_type_name.termination_duration_ids:
                                line_amount = rec.amount
                                if rec.date_to <= 60:
                                    if rec.amount > 0:
                                        duration_to = rec.date_to - duration_to
                                        five_year += total_rules * (duration_to / 12) * rec.factor
                            five_year = five_year * line_amount
                            five_year_benefit = five_year
                            amount = cause_type_amount - five_year_benefit

                        else:
                            amount = 0
                            five_year_benefit = cause_type_amount
            return cause_type_amount, five_year_benefit, amount ,termination_per_month
        else:
            return 0.0

    def get_duration_service(self, first_hire_date, end_date):
        if first_hire_date:
            start_date = datetime.datetime.strptime(str(first_hire_date), "%Y-%m-%d")
            end_date = datetime.datetime.strptime(str(end_date), "%Y-%m-%d")
            if end_date > start_date:
                r = rd.relativedelta(end_date, start_date)
                years = r.years
                months = r.months
                days = r.days
                return years, months, days
            else:
                raise exceptions.Warning(_('Leaving Date  must be greater than First Hiring Date'))

    def compute_iqama_cost(self, emp):
        iqama_line = self.env['employee.iqama.renewal.line'].search([('employee_id', '=', emp.id)])
        for iqama in iqama_line:
            r = rd.relativedelta(iqama.iqama_new_expiry,iqama.iqama_expir_date)
            if r:
                months = r.months
                if months:
                    iqama_month_cost = iqama.total / months
                    return iqama_month_cost
                else:
                    return 0.0
            else:
                return 0

    def get_value(self, data):
        # type = data['form']['type']
        employee_ids = data['form']['employee_ids']
        cause_type_id = data['form']['cause_type']
        cause_type_name = self.env['hr.termination.type'].search([('id', '=', cause_type_id)])
        allowance_ids = data['form']['allowance_ids']
        date_from = data['form']['date_from']
        date_to = data['form']['date_to']
        end_date = data['form']['end_date']
        termination_model = self.env['hr.termination']
        data = {'total_rule': {}, 'total_sum': {}}
        key_list = []
        employee_ids = self.env['hr.employee'].search([('id', 'in', employee_ids)])
        rules_ids = self.env['hr.salary.rule'].search([('id', 'in', allowance_ids)])
        if not employee_ids:
            raise exceptions.Warning(_('Sorry, Not Select Employees'))
        for emp in employee_ids:
            total = 0.0
            ticket_num = 0
            ticket_price = 0.0
            cause_amount = 0.0
            five_cause_amount = 0
            termination_per_month= 0
            amount = 0
            number_year = '0:0:0'
            if emp.first_hiring_date:
                year, month, day = self.get_duration_service(emp.first_hiring_date, end_date)
                cause_amount, five_cause_amount,amount,termination_per_month = self.get_cause_amount(
                    emp.first_hiring_date, cause_type_name,
                    end_date, emp)
                ticket = self.env['hr.ticket.request'].search([('employee_id', '=', emp.id), ('state', '=', 'done'),('mission_check','=',False)])
                if ticket:
                    for tic in ticket:
                        ticket_price_year =+ tic.cost_of_tickets
                        ticket_price = (ticket_price_year/12)

            number_year = ' سنه %s : شهر%s : يوم%s' % (year, month, day)
            salary = 0.0
            identity_id = False
            identity = False
            if emp.country_id.name == "Saudi Arabia":
                identity = emp.saudi_number.saudi_id
                identity_id = emp.saudi_number
                saudi = True
            else:
                saudi = False
                identity = emp.iqama_number.iqama_id
                identity_id = emp.iqama_number
            data[emp.name] = {
                'date': emp.first_hiring_date,
                'termination_reson': cause_type_name.name,
                'remind_leave_day': emp.remaining_leaves,
                'experiences_year': number_year,
                'ticket': ticket_num,
                'ticket_price': ticket_price,
                'leave_price': '',
                'termination_price': termination_per_month,
                'five_year_price': five_cause_amount,
                'amount': amount,
                'total': '',
                'total_salary': 0.0,
                'rule': '',
                'employee_name': emp.name,
                'employee_code': emp.emp_no,
                'identity': identity,
                'department': emp.department_id.name,
                'department_parent': emp.department_id.parent_id.name,
                'branch': emp.branch_id.name,
                'job': emp.job_id.name,
                'iqama_job': emp.emp_iqama_job,
                'nationality': emp.country_id.name,
                'ticket_type': emp.contract_id.ticket_class_id.name,
                'company_registry': emp.company_id.name,
                'social_ins': emp.contract_id.gosi_employer_deduction,
                'iqama_cost': self.compute_iqama_cost(emp),

            }
            if 'remaining_leaves' not in data['total_sum']:
                data['total_sum']['remaining_leaves'] = emp.remaining_leaves
            else:
                data['total_sum']['remaining_leaves'] += emp.remaining_leaves
            if 'ticket_num' not in data['total_sum']:
                data['total_sum']['ticket_num'] = ticket_num
            else:
                data['total_sum']['ticket_num'] += ticket_num
            if 'ticket_price' not in data['total_sum']:
                data['total_sum']['ticket_price'] = ticket_price
            else:
                data['total_sum']['ticket_price'] += ticket_price
            rules = {}
            lave_price = 0.0
            for rule in rules_ids:
                rule_amount = termination_model.compute_rule(rule, emp.contract_id)
                rules[rule.name] = rule_amount
                name = rule.name
                if name not in data['total_rule']:
                    data['total_rule'][name] = rule_amount
                else:
                    data['total_rule'][name] += rule_amount
                salary += rule_amount
                if 'total_salary' not in data['total_rule']:
                    data['total_rule']['total_salary'] = salary
                else:
                    data['total_rule']['total_salary'] += salary
                data[emp.name]['rule'] = rules
                data[emp.name]['total_salary'] = salary
            if salary > 0:
                amount_per_day = salary / 30
                lave_price = emp.remaining_leaves * amount_per_day
            if 'lave_price' not in data['total_sum']:
                data['total_sum']['lave_price'] = lave_price
            else:
                data['total_sum']['lave_price'] += lave_price
            data[emp.name]['leave_price'] = lave_price
            if 'five_year_price' not in data['total_sum']:
                data['total_sum']['termination_price'] = cause_amount
                data['total_sum']['five_year_price'] = five_cause_amount
                data['total_sum']['amount'] = amount
            else:
                data['total_sum']['termination_price'] += cause_amount
                data['total_sum']['five_year_price'] += five_cause_amount
                data['total_sum']['amount'] += amount
            key_list.append(emp.name)
            total = data[emp.name]['total_salary'] + data[emp.name]['termination_price'] + data[emp.name][ 'leave_price'] + data[emp.name]['ticket_price']
            data[emp.name]['total'] = total
            if 'total' not in data['total_sum']:
                data['total_sum']['total'] = total
            else:
                data['total_sum']['total'] += total

        mykey = list(dict.fromkeys(key_list))
        return data, mykey


    @api.model
    def _get_report_values(self, docids, data=None):
        data_dic, mykey = self.get_value(data)
        allowance_ids = data['form']['allowance_ids']
        len_of_salary = len(allowance_ids)
        date_to = data['form']['date_to']
        return {
            'doc_ids': data['ids'],
            'doc_model': data['model'],
            'type': type,
            'data': data_dic,
            'mykey': mykey,
            'len_of_salary': len_of_salary,
            'date_to': date_to,
        }


class TerminationReportXls(models.AbstractModel):
    _name = 'report.hr_base_reports.termination_benefits_xls'
    _inherit = 'report.report_xlsx.abstract'

    def generate_xlsx_report(self, workbook, data, datas):
        cost = self.env['report.hr_base_reports.termination_report_temp']
        final_dic, mykey = ReportTerminationPublic.get_value(cost, data)

        allowance_ids = data['form']['allowance_ids']
        len_of_salary = len(allowance_ids)
        sheet = workbook.add_worksheet(U'Holiday Report')
        sheet.right_to_left()
        format1 = workbook.add_format(
            {'font_size': 10, 'bottom': True, 'right': True, 'left': True, 'top': True, 'align': 'center',
             'bold': True})
        format2 = workbook.add_format(
            {'font_size': 10, 'bottom': True, 'right': True, 'left': True, 'top': True, 'align': 'center',
             'bold': True})

        format2.set_align('center')
        format2.set_align('vcenter')
        format2.set_color('white')
        format2.set_bg_color('blue')
        sheet.set_column(2, 11, 20)
        sheet.merge_range('E3:H3', (_("تقرير تكلفة الموظف ")) , format2)
        sheet.write(3, 1, ('كود الموظف'), format2)
        sheet.write(3, 2, ('رقم الهوية'), format2)
        sheet.write(3, 3, ('الموظف'), format2)
        sheet.write(3, 4, ('القطاع'), format2)
        sheet.write(3, 5, ('اﻹدارة'), format2)
        sheet.write(3, 6, ('الفرع'), format2)
        sheet.write(3, 7, ('الوظيفة'), format2)
        sheet.write(3, 8, ('مهنة اﻹقامة'), format2)
        sheet.write(3, 9, ('الجنسية'), format2)
        sheet.write(3, 10, ('فئة التذكرة'), format2)
        sheet.write(3, 11, ('اسم الكفيل'), format2)
        sheet.write(3, 12, ('تاريخ بدء العمل '), format2)
        sheet.write(3, 13, ('سنوات الخدمة(سنة/شهر/يوم)'), format2)
        flag = 1
        x = 14
        for key in mykey:
            if flag == 1:
                for rule in final_dic[key]['rule']:
                    sheet.write(3, x, rule, format2)
                    x += 1
                flag += 1
        sheet.write(3, len_of_salary +14, ('المجموع'), format2)
        sheet.write(3,  len_of_salary + 15, ('مبلغ تذكرة السفر'), format2)
        sheet.write(3,  len_of_salary + 16, ('قيمة الإجازة'), format2)
        sheet.write(3, len_of_salary + 17, ('نهاية الخدمة لأقل من 5 سنة'), format2)
        sheet.write(3, len_of_salary + 18, ('نهاية الخدمة لأكبر من 5 سنة'), format2)
        sheet.write(3, len_of_salary + 19, ('قيمة نهاية الخدمة'), format2)
        sheet.write(3, len_of_salary + 20, ('تأمينات اجتماعية'), format2)
        sheet.write(3, len_of_salary + 21, ('مصاريف اقامة'), format2)
        sheet.write(3, len_of_salary + 22, ('تكلفة التأمين االطبي'), format2)
        sheet.write(3, len_of_salary + 23, ('تامين طبي الشهري'), format2)
        sheet.write(3, len_of_salary + 24, ('تكلفة الموظف الشهرية'), format2)
        row = 3
        for key in mykey:
            row += 1
            n = 14
            data_row = 14
            sheet.write(row, 1, final_dic[key]['employee_code'], format1)
            sheet.write(row, 2, final_dic[key]['identity'], format1)
            sheet.write(row, 3, final_dic[key]['employee_name'], format1)
            sheet.write(row, 4, final_dic[key]['department'], format1)
            sheet.write(row, 5, final_dic[key]['department_parent'], format1)
            sheet.write(row, 6, final_dic[key]['branch'], format1)
            sheet.write(row, 7, final_dic[key]['job'], format1)
            sheet.write(row, 8, final_dic[key]['iqama_job'], format1)
            sheet.write(row, 9, final_dic[key]['nationality'], format1)
            sheet.write(row, 10, final_dic[key]['ticket_type'], format1)
            sheet.write(row, 11, final_dic[key]['company_registry'], format1)
            sheet.write(row, 12, final_dic[key]['date'], format1)
            sheet.write(row, 13, final_dic[key]['experiences_year'], format1)
            for rule in final_dic[key]['rule']:
                sheet.write(row, n, final_dic[key]['rule'][rule], format1)
                n += 1
            sheet.write(row, 14 + len_of_salary, final_dic[key]['total_salary'], format1)
            sheet.write(row, 15 + len_of_salary, final_dic[key]['ticket_price'], format1)
            sheet.write(row, 16 + len_of_salary, final_dic[key]['leave_price'], format1)
            sheet.write(row, 17 + len_of_salary , final_dic[key]['five_year_price'], format1)
            sheet.write(row, 18 + len_of_salary , final_dic[key]['amount'], format1)
            sheet.write(row, 19 + len_of_salary, final_dic[key]['termination_price'], format1)
            sheet.write(row, 20 + len_of_salary, final_dic[key]['social_ins'], format1)
            sheet.write(row, 21 + len_of_salary, final_dic[key]['iqama_cost'], format1)
            sheet.write(row, 22 + len_of_salary, 0, format1)
            sheet.write(row, 23 + len_of_salary, 0, format1)
            sheet.write(row, 24 + len_of_salary, final_dic[key]['total'], format1)

