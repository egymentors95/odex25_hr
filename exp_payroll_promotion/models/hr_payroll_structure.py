# -*- coding: utf-8 -*-

from odoo import models, fields


class HrPayrollStructure(models.Model):
    _inherit = 'hr.payroll.structure'

    time_margin = fields.Integer(string='Time Margin', required=True)
