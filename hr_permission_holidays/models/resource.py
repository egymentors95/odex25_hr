# -*- coding: utf-8 -*-

from odoo import models, fields


class HrAttendances(models.Model):
    _inherit = 'resource.calendar'

    holiday_permission_deducted = fields.Integer(string="Permission to Deduct From holiday",
                                  help='The Number of permission deducted From The Annual Holiday balance')
