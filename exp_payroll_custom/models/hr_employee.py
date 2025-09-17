# -*- coding: utf-8 -*-

from odoo import models, fields


class HrEmployeeSalaryScale(models.Model):
    _inherit = 'hr.employee'

    salary_scale = fields.Many2one(related='contract_id.salary_scale', string='Salary scale', store=True)
    salary_level = fields.Many2one(related='contract_id.salary_level', string='Salary Level', store=True)
    salary_group = fields.Many2one(related='contract_id.salary_group', string='Salary Group', store=True)
    salary_degree = fields.Many2one(related='contract_id.salary_degree', string='Salary Degree', store=True)
