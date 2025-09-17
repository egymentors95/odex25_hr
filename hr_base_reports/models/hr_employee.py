# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from datetime import datetime ,timedelta
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    def get_employee_data_report(self, contract, date_from, date_to):
        for rec in self:
            end_date = datetime.strptime(str(date_to), DEFAULT_SERVER_DATE_FORMAT)
            start_date = datetime.strptime(str(date_from), DEFAULT_SERVER_DATE_FORMAT)
            month = (end_date.year - start_date.year) * 12 + (end_date.month - start_date.month) + 1
            day_salary = contract.total_allowance / 30
            other_allowance = self.get_other_allowance(contract)
            annual = (contract.total_allowance + contract.gosi_employer_deduction) * month
            return [day_salary, other_allowance, annual]

    def get_time_permission(self, personal_permission_id):
        if personal_permission_id:
            start = (fields.Datetime.from_string(personal_permission_id.date_from) + timedelta(
                hours=3))
            end = (fields.Datetime.from_string(personal_permission_id.date_to) + timedelta(
                hours=3))
            return [start, end]
        else:
            return ["", ""]

    def get_other_allowance(self, contract):
        for rec in self:
            other_allowance = abs(contract.total_allowance - (contract.salary + contract.house_allowance_temp + contract.transport_allowance))
            localdict = dict(employee=self.id, contract=contract)
            salary_scale = contract.salary_scale

            return other_allowance

    def get_transport_allowance(self, contract):
        for rec in self:
            other_allowance = self.get_other_allowance(contract)
            localdict = dict(employee=self.id, contract=contract)
            salary_scale = contract.salary_scale.sudo()
            total_remaining_leaves = 0.0
            rules = salary_scale.rule_ids.filtered(lambda r: r.rules_type == 'transport')
            transport_allowance = 0
            for r in rules:
                transport_allowance += r.sudo()._compute_rule(localdict)[0]
            annual_leaves = self.env['hr.holidays'].sudo().search([('employee_id', '=', self.id), ('type', '=', 'add'), ('holiday_status_id.leave_type', '=', 'annual'),
                                                              ('check_allocation_view', '=', 'balance')])
            if annual_leaves:

                total_remaining_leaves = sum(annual_leaves.mapped('remaining_leaves'))
            else:
                total_remaining_leaves = 0.0
            balance = total_remaining_leaves
            return [other_allowance, transport_allowance, balance]


class HrAttendanceTransactions(models.Model):
    _inherit = 'hr.attendance.transaction'

    def get_attendance_value(self, employee, employees):
        records = employees.filtered(lambda r: r.employee_id.id in employee.department_id.employee_ids.ids)
        total_late = sum(records.mapped('lateness')) if records else 0
        hour = employee.resource_calendar_id.work_hour if employee.resource_calendar_id else 8
        hour_price = hour * employee.contract_id.total_allowance / 30 if employee.contract_id.total_allowance > 0 else 0
        return [hour_price, total_late]


class Mission(models.Model):
    _inherit = 'hr.official.mission'

    def get_mission_data(self, mission, employee, departments):
        for rec in self:
            department = employee.department_id
            ticket = sum(self.env['hr.ticket.request'].sudo().search([('mission_request_id', '=', mission.id),
                                                                      ('employee_id', '=', employee.id)])
                         .mapped('cost_of_tickets')) or 0
            department_cost = sum(
                departments.filtered(lambda r: r.employee_id.department_id == department).mapped('amount'))
            return [ticket, department_cost]
