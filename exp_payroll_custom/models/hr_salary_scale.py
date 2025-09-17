# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class HrSalaryScale(models.Model):
    _inherit = 'hr.payroll.structure'

    active = fields.Boolean(string='Active', default=True)
    start_date = fields.Date(string='Start Date')
    end_date = fields.Date(string='End Date')
    level_num = fields.Integer(string='Number Of Levels')
    retirement_age = fields.Integer('Retirement Age', default=60)
    type = fields.Selection(selection=[('scale', _('Scale')), ('level', _('Level')),
                                       ('group', _('Group')), ('degree', _('Degree'))], default='scale', string='Type')
    transfer_type = fields.Selection(selection=[('all', _('All Employee')),
                                                ('per_analytic_account', _('Per Analytic Account')),
                                                ('one_by_one', _('Per Employee')),
                                                ('per_bank', _('Per Bank'))], string='Transfer type')

    # relation fields
    salary_scale_levels_ids = fields.One2many('hr.payroll.structure', 'salary_scale_id',
                                              domain=[('type', '=', 'level')], store=True)
    salary_scale_level_degrees_ids = fields.One2many('hr.payroll.structure', 'salary_scale_id',
                                                     domain=[('type', '=', 'degree')], store=True)
    salary_scale_level_groups_ids = fields.One2many('hr.payroll.structure', 'salary_scale_id',
                                                    domain=[('type', '=', 'group')], store=True)

    salary_scale_id = fields.Many2one('hr.payroll.structure', string='Salary Scale', index=True)  # salary scale

    #Percentage_increase = fields.Float('Percentage Increase %',default=0.05)

    analytic_account_id = fields.Many2one(comodel_name='account.analytic.account')

    # Override Function

    def get_all_rules(self):
        """
        @return: returns a list of tuple (id, sequence) of rules that are maybe to apply
        """
        all_rules = []
        for struct in self:
            if struct.benefits_discounts_ids:
                all_rules += struct.benefits_discounts_ids._recursive_search_of_rules()
            else:
                all_rules += struct.rule_ids._recursive_search_of_rules()

        return all_rules

    # filter salary_level,salary_group

    @api.onchange('salary_scale_id')
    def onchange_salary_scale_id(self):
        for item in self:
            if item.salary_scale_id:
                level_ids = self.env['hr.payroll.structure'].search(
                    [('salary_scale_id', '=', item.salary_scale_id.id), ('type', '=', 'level')])
                item.salary_scale_level_id = []
                item.salary_scale_group_id = []
                return {'domain': {'salary_scale_level_id': [('id', 'in', level_ids.ids)]}}

    # filter depend on salary_level

    @api.onchange('salary_scale_level_id')
    def onchange_salary_scale_level_id(self):
        for item in self:
            if item.salary_scale_level_id:
                group_ids = self.env['hr.payroll.structure'].search(
                    [('salary_scale_level_id', '=', item.salary_scale_level_id.id), ('type', '=', 'group')])
                item.salary_scale_group_id = []
                return {'domain': {'salary_scale_group_id': [('id', 'in', group_ids.ids)]}}
