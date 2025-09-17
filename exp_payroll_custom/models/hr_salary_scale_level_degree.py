# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class HrSalaryScaleDegree(models.Model):
    _inherit = 'hr.payroll.structure'

    base_salary = fields.Float(string='Base Salary')
    interval_time = fields.Integer(string='Interval Time')
    salary_scale_group_id = fields.Many2one(comodel_name='hr.payroll.structure', index=True)

    @api.constrains('base_salary', 'salary_scale_group_id')
    def base_salary_constrains(self):
        if self.salary_scale_group_id.gread_max > 0 and self.salary_scale_group_id.gread_min > 0:
            if self.base_salary > self.salary_scale_group_id.gread_max or \
                    self.base_salary < self.salary_scale_group_id.gread_min:
                raise UserError(_('The Basic Salary Is Greater Than Group Gread Max Or less than Gread Min'))
