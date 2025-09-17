# -*- coding: utf-8 -*-
from odoo import fields, models


class HrHolidaysStatus(models.Model):
    _inherit = 'hr.holidays.status'

    permission_annual_holiday = fields.Boolean(string="Permissions Half Day Off")


class HRHolidays(models.Model):
    _inherit = 'hr.holidays'

    permission_ids = fields.One2many('hr.personal.permission', 'holiday', string="Permissions")
