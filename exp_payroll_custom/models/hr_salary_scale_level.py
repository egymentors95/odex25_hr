# -*- coding: utf-8 -*-

from odoo import models, fields


class HrSalaryScaleLevel(models.Model):
    _inherit = 'hr.payroll.structure'

    groups_number = fields.Integer(string='Number Of Groups')
    salary_scale_id = fields.Many2one('hr.payroll.structure', string='Salary Scale', index=True)
    benefits_discounts_ids = fields.Many2many('hr.salary.rule', string='Benefits and discounts')
