# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class HrPayrollStructure(models.Model):
    _inherit = 'hr.payroll.structure'

    sequence = fields.Integer(string='Sequence')
    job_ids = fields.Many2many('hr.job', 'rel_job_degree', string='Jobs')

    @api.constrains('sequence', 'salary_scale_id', 'salary_scale_level_id', 'salary_scale_group_id', 'type')
    def check_sequence(self):
        if self.type == 'group':
            if self.search([('salary_scale_level_id', '=', self.salary_scale_level_id.id),
                            ('salary_scale_id', '=', self.salary_scale_id.id),
                            ('sequence', '=', self.sequence),
                            ('type', '=', 'group'),
                            ('id', '!=', self.id)]):
                raise ValidationError(
                    _('Sorry this sequence is already given for another group within level %s, please set another one.')
                    % self.salary_scale_level_id.name)
        elif self.type == 'degree':
            if self.salary_scale_group_id.degree_number < 1:
                raise ValidationError(
                    _('Please set the maximum number of degrees for group %s.') % self.salary_scale_group_id.name)
            if self.sequence > self.salary_scale_group_id.degree_number:
                raise ValidationError(
                    _('Sorry the maximum number of degrees for group %s is %s, you cant have sequence grater than'
                      ' this.') %
                    (self.salary_scale_group_id.name, self.salary_scale_group_id.degree_number))
            if self.search([('salary_scale_level_id', '=', self.salary_scale_level_id.id),
                            ('salary_scale_group_id', '=', self.salary_scale_group_id.id),
                            ('salary_scale_id', '=', self.salary_scale_id.id),
                            ('sequence', '=', self.sequence),
                            ('type', '=', 'degree'),
                            ('id', '!=', self.id)]):
                raise ValidationError(
                    _('Sorry this sequence is already given for another degree of this group please set another one.'))
