# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class HrSalaryScaleLevel(models.Model):
    _inherit = 'hr.payroll.structure'

    degree_number = fields.Integer(string='Number of Degrees')
    salary_scale_level_id = fields.Many2one(comodel_name='hr.payroll.structure', string='Salary Scale Level',
                                            index=True)
    gread_min = fields.Float(string='Gread Min')
    gread_max = fields.Float(string='Gread Max')

    @api.constrains('gread_min', 'gread_max')
    def zero_constrains(self):

        if self.gread_max < 0 or self.gread_min < 0:
            raise UserError(_('The Gread Max Or Gread Min is not Negative'))

        if self.gread_max < self.gread_min:
            raise UserError(_('The Gread Max Is Greater Than Gread Min'))
