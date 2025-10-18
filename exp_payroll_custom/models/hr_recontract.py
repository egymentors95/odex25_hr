# -*- coding: utf-8 -*-

from odoo import models, fields, api


class HrReContract(models.Model):
    _inherit = 'hr.re.contract'

    salary_scale = fields.Many2one('hr.payroll.structure', string='Salary Scale', compute='_get_employee_data')
    salary_group = fields.Many2one('hr.payroll.structure', string='Salary Group', compute='_get_employee_data')
    salary_level = fields.Many2one('hr.payroll.structure', string='Salary Level', compute='_get_employee_data')
    salary_degree = fields.Many2one('hr.payroll.structure', string='Salary Degree', compute='_get_employee_data')
    new_salary_scale = fields.Many2one(comodel_name='hr.payroll.structure')
    new_salary_level = fields.Many2one(comodel_name='hr.payroll.structure')
    new_salary_group = fields.Many2one(comodel_name='hr.payroll.structure')
    new_salary_degree = fields.Many2one(comodel_name='hr.payroll.structure')

    @api.onchange('new_salary_scale')
    def onchange_new_salary_scale(self):
        for item in self:
            if item.new_salary_scale:
                level_ids = self.env['hr.payroll.structure'].search(
                    [('salary_scale_id', '=', item.new_salary_scale.id), ('type', '=', 'level')])
                group_ids = self.env['hr.payroll.structure'].search(
                    [('salary_scale_id', '=', item.new_salary_scale.id), ('type', '=', 'group')])
                degree_ids = self.env['hr.payroll.structure'].search(
                    [('salary_scale_id', '=', item.new_salary_scale.id), ('type', '=', 'degree')])
                return {'domain': {'new_salary_level': [('id', 'in', level_ids.ids)],
                                   'new_salary_group': [('id', 'in', group_ids.ids)],
                                   'new_salary_degree': [('id', 'in', degree_ids.ids)]}}
            else:
                item.new_salary = 0.0
                return {'domain': {'new_salary_level': [('id', 'in', [])],
                                   'new_salary_group': [('id', 'in', [])],
                                   'new_salary_degree': [('id', 'in', [])]}}

    # filter depend on new_salary_level

    @api.onchange('new_salary_level')
    def onchange_new_salary_level(self):
        for item in self:
            if item.new_salary_level:
                group_ids = self.env['hr.payroll.structure'].search(
                    [('salary_scale_level_id', '=', item.new_salary_level.id), ('type', '=', 'group')])
                return {'domain': {'new_salary_group': [('id', 'in', group_ids.ids)],
                                   'new_salary_degree': [('id', 'in', [])]}}
            else:
                return {'domain': {'new_salary_group': [('id', 'in', [])],
                                   'new_salary_degree': [('id', 'in', [])]}}

    # filter depend on salary_group

    @api.onchange('new_salary_group')
    def onchange_salary_group(self):
        for item in self:
            if item.new_salary_group:
                degree_ids = self.env['hr.payroll.structure'].search(
                    [('salary_scale_group_id', '=', item.new_salary_group.id), ('type', '=', 'degree')])
                return {'domain': {'new_salary_degree': [('id', 'in', degree_ids.ids)]}}
            else:
                return {'domain': {'new_salary_degree': [('id', 'in', [])]}}

    @api.onchange('new_salary_degree')
    def onchange_degree(self):
        if self.new_salary_degree:
            self.new_salary = self.new_salary_degree.base_salary

    @api.depends('employee_id')
    def _get_employee_data(self):
        for rec in self:
            rec.hire_date = False
            rec.contract_id = False
            rec.start_date = False
            rec.eoc_date = False
            rec.job_id = False
            rec.department_id = False
            rec.salary_scale = False
            rec.salary_level = False
            rec.salary_group = False
            rec.salary_degree = False
            if rec.employee_id:
                rec.hire_date = rec.employee_id.first_hiring_date
                rec.contract_id = rec.employee_id.contract_id.id
                rec.start_date = rec.employee_id.contract_id.date_start
                rec.eoc_date = rec.employee_id.contract_id.date_end
                rec.job_id = rec.employee_id.job_id.id
                rec.department_id = rec.employee_id.department_id.id
                rec.salary_scale = rec.employee_id.contract_id.salary_scale.id
                rec.salary_level = rec.employee_id.contract_id.salary_level.id
                rec.salary_group = rec.employee_id.contract_id.salary_group.id
                rec.salary_degree = rec.employee_id.contract_id.salary_degree.id

    def _get_default_category(self):
        return self.env['hr.salary.rule.category'].search([('code', '=', 'NET')], limit=1)
