# -*- coding: utf-8 -*-

from odoo import api, fields, models, _, exceptions


class EmployeeAppraisal(models.Model):
    _inherit= 'hr.employee.appraisal'

    mission_id = fields.Many2one('hr.official.mission', string="Training Course",domain=[("mission_type.work_state", "=", "training")])
    course_name = fields.Many2one(related='mission_id.course_name',string="Course Name",store=True)

    @api.onchange('department_id', 'mission_id', 'appraisal_type')
    def employee_ids_domain(self):
        self.employee_id = False
        if self.mission_id and self.appraisal_type == 'training':
            employee_list = self.mission_id.employee_ids.mapped('employee_id').ids
            return {'domain': {'employee_id': [('id', 'in', employee_list)]}}




