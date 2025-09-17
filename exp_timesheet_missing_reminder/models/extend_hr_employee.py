# -*- coding: utf-8 -*-

from odoo import models, fields


class ExtendEmployee(models.Model):
    _inherit = 'hr.employee'

    skipp_timesheet_reminder = fields.Boolean(string='Skip Timesheet Reminder')
