# -*- coding: utf-8 -*-

from odoo import models, fields


class HrEmployeeHistory(models.Model):
    _name = 'hr.employee.history.reminder'
    _rec_name = 'employee_id'

    employee_id = fields.Many2one('hr.employee', string='Employee Name')
    date = fields.Date()
    miss_hour = fields.Float(string='Miss Hour')
    actual_hour = fields.Float(string='Actual')
    entered_hour = fields.Float(string='Entered Hour')
    break_hour = fields.Float(string='Break Hour')
    overtime_hour = fields.Float(string='Overtime Hour')
    is_completed_timesheet = fields.Boolean('Is completed Timesheet', default=False)
