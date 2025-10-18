# -*- coding: utf-8 -*-

from datetime import datetime

from odoo import models, fields, api, _, exceptions


class EmployeePromotions(models.Model):
    _name = 'employee.promotions'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'employee_id'
    _description = 'Employee Promotions'

    date = fields.Date(required=True)
    comment = fields.Text()
    state = fields.Selection(selection=[('draft', _('Draft')),
                                        ('confirm', _('HR Officer')),
                                        ('hr_manager', _('HR Manager')),
                                        ('approved', _('Approved')), ('refuse', 'Refused')],
                             default='draft', tracking=True)

    # relational fields
    employee_id = fields.Many2one('hr.employee', domain=[('state', '=', 'open')])
    old_scale = fields.Many2one('hr.payroll.structure')
    old_level = fields.Many2one('hr.payroll.structure')
    old_group = fields.Many2one('hr.payroll.structure')
    old_degree = fields.Many2one('hr.payroll.structure')
    old_level_2 = fields.Many2one('hr.payroll.structure')
    old_group_2 = fields.Many2one('hr.payroll.structure')
    old_degree_2 = fields.Many2one('hr.payroll.structure')
    new_level = fields.Many2one('hr.payroll.structure', domain=[('id', 'in', [])])
    new_group = fields.Many2one('hr.payroll.structure', domain=[('id', 'in', [])])
    new_degree = fields.Many2one('hr.payroll.structure', domain=[('id', 'in', [])])
    company_id = fields.Many2one('res.company', string='Company',default=lambda self: self.env.company)

    @api.onchange('employee_id')
    def store_level_group_and_degree_values(self):
        if self.employee_id:
            self.old_scale = self.employee_id.salary_scale
            self.old_level = self.employee_id.salary_level
            self.old_group = self.employee_id.salary_group
            self.old_degree = self.employee_id.salary_degree
            self.old_level_2 = self.employee_id.salary_level
            self.old_group_2 = self.employee_id.salary_group
            self.old_degree_2 = self.employee_id.salary_degree

    # dynamic domain to get new level and new group domain

    @api.onchange('old_scale')
    def _get_new_level_and_new_group_domain(self):
        for item in self:
            if item.old_scale:
                level_ids = self.env['hr.payroll.structure'].search(
                    [('salary_scale_id', '=', item.old_scale.id), ('type', '=', 'level')])
                group_ids = self.env['hr.payroll.structure'].search(
                    [('salary_scale_id', '=', item.old_scale.id), ('type', '=', 'group')])
                degree_ids = self.env['hr.payroll.structure'].search(
                    [('salary_scale_id', '=', item.old_scale.id), ('type', '=', 'degree')])
                domain = {'new_level': [('id', 'in', level_ids.ids)],
                          'new_group': [('id', 'in', group_ids.ids)],
                          'new_degree': [('id', 'in', degree_ids.ids)]}
                return {'domain': domain}
            else:
                domain = {'new_level': [('id', 'in', [])],
                          'new_group': [('id', 'in', [])],
                          'new_degree': [('id', 'in', [])]}
                return {'domain': domain}

    # filter depend on salary_level

    @api.onchange('new_level')
    def onchange_salary_level(self):
        for item in self:
            if item.new_level:
                group_ids = self.env['hr.payroll.structure'].search(
                    [('salary_scale_level_id', '=', item.new_level.id), ('type', '=', 'group')])
                return {'domain': {'new_group': [('id', 'in', group_ids.ids)],
                                   'new_degree': [('id', 'in', [])]}}
            else:
                return {'domain': {'new_group': [('id', 'in', [])],
                                   'new_degree': [('id', 'in', [])]}}

    # dynamic domain to get new degree domain

    @api.onchange('new_group')
    def _get_new_degree_domain(self):
        for item in self:
            if item.new_group:
                # item.new_degree = False
                degree_ids = self.env['hr.payroll.structure'].search(
                    [('salary_scale_group_id', '=', item.new_group.id), ('type', '=', 'degree')])
                domain = {'new_degree': [('id', 'in', degree_ids.ids)]}
                return {'domain': domain}
            else:
                domain = {'new_degree': [('id', 'in', [])]}
                return {'domain': domain}

    def confirm(self):
        module_obj = self.env['ir.module.module'].sudo()
        modules = module_obj.search([('state', '=', 'installed'), ('name', '=', 'hr_disciplinary_tracking')])
        year_promotion = datetime.strptime(str(self.date), '%Y-%m-%d').strftime('%y')
        if modules:
            employee_penalty = self.env['hr.penalty.register'].search([('employee_id', '=', self.employee_id.id),
                                                                       ('state', 'not in', ['draft', 'refuse'])])
            if employee_penalty:
                for penalty in employee_penalty:
                    year_penalty = datetime.strptime(str(penalty.date), '%Y-%m-%d').strftime('%y')
                    if year_promotion == year_penalty:
                        for punish in penalty.punishment_id:
                            if punish.type == "deprivation":
                                raise exceptions.Warning(_('You can not promotions Employee has Penalty %s in this '
                                                           'Period.') % punish.name)
        self.state = 'confirm'

    def hr_manager(self):
        self.confirm()
        self.state = 'hr_manager'

    def approved(self):
        for rec in self:
            rec.employee_id.contract_id.write({
                'salary_level': rec.new_level.id,
                'salary_group': rec.new_group.id,
                'salary_degree': rec.new_degree.id,
                'salary': rec.new_degree.base_salary,
                'salary_insurnce': rec.new_degree.base_salary,
            })
            rec.state = 'approved'

    def act_refuse(self):
        self.state = 'refuse'

    # change state to draft
    def re_draft(self):
        for rec in self:
            rec.employee_id.contract_id.write({
                'salary_level': rec.old_level_2.id,
                'salary_group': rec.old_group_2.id,
                'salary_degree': rec.old_degree_2.id,
                'salary': rec.old_degree_2.base_salary,
                'salary_insurnce': rec.old_degree_2.base_salary,
            })

            rec.state = 'draft'

    @api.model
    def create(self, values):
        result = super(EmployeePromotions, self).create(values)
        result.old_level_2 = result.old_level
        result.old_group_2 = result.old_group
        result.old_degree_2 = result.old_degree
        return result

    def unlink(self):
        for item in self:
            if item.state != 'draft':
                raise exceptions.Warning(_(
                    'You can not delete employee promotions  for  "%s" in state not in draft.') % item.employee_id.name)
        return super(EmployeePromotions, self).unlink()


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    promotions_count = fields.Integer(compute='get_employee_promotions')

    def get_employee_promotions(self):
        for item in self:
            promotions = item.sudo().env['employee.promotions'].search([
                ('state', '=', 'approved'), ('employee_id', '=', item.id)])
            item.sudo().promotions_count = len(promotions)
            return promotions
