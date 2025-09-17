# -*- coding: utf-8 -*-
from odoo import models, fields


class AttendanceTransactions(models.Model):
    _inherit = 'hr.attendance.transaction'

    normal_leave = fields.Boolean(string='Normal Leave')
    leave_id = fields.Many2one(comodel_name='hr.holidays')
    total_leave_hours = fields.Float()

    public_holiday = fields.Boolean(string='Public Holiday', default=False)
    public_holiday_id = fields.Many2one('hr.holiday.officials', string='Public Holiday')

    holiday_name = fields.Many2one(comodel_name='hr.holidays.status', related='leave_id.holiday_status_id',
                                   string='Holiday Name', store=True)

