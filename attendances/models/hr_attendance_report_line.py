# -*- coding: utf-8 -*-
from odoo import models, fields, api


class HrAttendanceReportLine(models.Model):
    _name = 'hr.attendance.report.line'

    employee_name = fields.Many2one(comodel_name='hr.employee')
    delay = fields.Float()
    leave = fields.Float(string='Holiday Hours')
    exist_hours = fields.Float()
    extra_break_duration = fields.Float()
    absent = fields.Float(string='Absent Hours')
    mission_by_days = fields.Float(string='Mission Hours')
    line_id = fields.Many2one(comodel_name='hr.attendance.report')
    absent_days_by_hr = fields.Float(string='Absent Hours By HR')
    dummy_field = fields.Float()
    total_hours = fields.Float(string='Total Absence Hours')  # get total hours in month from attendance configuration
    total_amount = fields.Float(string='Total Salary')  # get from total allowance in contract
    amount_per_hour = fields.Float()  # get from total_amount / total_hours
    total_deduction = fields.Float()  # get from delay+leave+absent * amount_per_hour
    actual_absent_hours = fields.Float(string='Actual Absent Hours')
    total_permission_hours = fields.Float(string='Total Permission Hours')
    missing_punch_hours =  fields.Float(string='Total Punch Hours')

    additional_hours = fields.Float(string='Additional Hours', default=0)

    advantage_id = fields.Many2one(comodel_name='contract.advantage', string='Deduction Employee')

    @api.onchange('absent_days_by_hr')
    def onchange_absent_days_by_hr(self):
        for item in self:
            if item.absent == 0:
                item.dummy_field = item.delay + item.exists + item.extra_break_duration + item.absent
                hours = item.dummy_field - item.absent_days_by_hr
                if hours < 0:
                    hours = 0
                deduction = hours * item.amount_per_hour
                return {'value': {'total_hours': hours,
                                  'total_deduction': deduction}}

            else:
                item.dummy_field = item.absent
                hourss = item.dummy_field - item.absent_days_by_hr
                if hourss < 0:
                    hourss = 0
                deduction = hourss * item.amount_per_hour
                return {'value': {'total_hours': hourss,
                                  'total_deduction': deduction}}
