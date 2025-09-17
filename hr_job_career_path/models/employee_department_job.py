# -*- coding: utf-8 -*-

from datetime import timedelta

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class EmployeeDepartmentJobs(models.Model):
    _inherit = 'employee.department.jobs'

    eligible = fields.Boolean(string='Eligible', )
    unmet_condition = fields.Text(string='Unmet Conditions')
    permit = fields.Boolean(string='Permit Nomination')
    permission_reason = fields.Text(string='Nomination Permission Reason')

    job_date_to = fields.Date(string='Job Date To', readonly=True)
    department_date_to = fields.Date(string='Department Date To', readonly=True)

    @api.onchange('employee_id', 'promotion_type', 'new_job_id', 'new_department_id')
    def onchange_check_eligibility(self):
        job_eligibility = {}
        if self.promotion_type == 'job':
            if self.employee_id and self.new_job_id:
                job_eligibility = self.employee_id.check_job_eligibility(self.new_job_id)
        elif self.promotion_type == 'both':
            if self.employee_id and self.new_job_id and self.new_department_id:
                job_eligibility = self.employee_id.check_job_eligibility(self.new_job_id, self.new_department_id)
        if bool(job_eligibility):
            self.eligible = job_eligibility['eligible']
            self.unmet_condition = job_eligibility['unmet_condition']

    @api.constrains('state')
    def check_permission(self):
        if self.state != 'draft' and not self.eligible and not self.permit and self.promotion_type != 'department':
            raise ValidationError(_('Sorry employee %s is not eligible, that you can not proceed with approval without '
                                    'granting him a permission to be nominated.') % self.employee_id.name)

        if self.state != 'draft' and self.promotion_type == 'department' and self.new_department_id.job_ids:
            if self.old_job_2_id not in self.new_department_id.job_ids and not self.permit:
                raise ValidationError(
                    _('Sorry Employee Job %s does not Exist among The New Departments Jobs.') % self.old_job_2_id.name)

    def approved(self):
        super(EmployeeDepartmentJobs, self).approved()
        if self.promotion_type != 'department' and self.old_job_2_id:
            previous_job = self.search([('employee_id', '=', self.employee_id.id),
                                        ('new_job_id', '=', self.old_job_2_id.id),
                                        ('id', '!=', self.id),
                                        ('state', '=', 'approved'),
                                        ('promotion_type', '!=', 'department')], order='date desc', limit=1)
            if previous_job:
                previous_job.job_date_to = fields.Date.to_string(fields.Date.from_string(self.date) - timedelta(days=1))
                previous_job.last_record = False

        if self.promotion_type != 'job' and self.old_department_2_id:
            previous_dep = self.search([('employee_id', '=', self.employee_id.id),
                                        ('new_department_id', '=', self.old_department_2_id.id),
                                        ('id', '!=', self.id),
                                        ('state', '=', 'approved'),
                                        ('promotion_type', '!=', 'job')], order='date desc', limit=1)
            if previous_dep:
                previous_dep.department_date_to = fields.Date.to_string(
                    fields.Date.from_string(self.date) - timedelta(days=1))
                previous_dep.last_record = False

    def draft(self):
        super(EmployeeDepartmentJobs, self).draft()
        if self.promotion_type != 'department' and self.old_job_2_id:
            self.job_date_to = False
            previous_job = self.search([('employee_id', '=', self.employee_id.id),
                                        ('new_job_id', '=', self.old_job_2_id.id),
                                        ('id', '!=', self.id),
                                        ('state', '=', 'approved'),
                                        ('promotion_type', '!=', 'department')], order='date desc', limit=1)

            if previous_job:
                previous_job.job_date_to = False
                previous_job.last_record = True

        if self.promotion_type != 'job' and self.old_department_2_id:
            previous_dep = self.search([('employee_id', '=', self.employee_id.id),
                                        ('new_department_id', '=', self.old_department_2_id.id),
                                        ('id', '!=', self.id),
                                        ('state', '=', 'approved'),
                                        ('promotion_type', '!=', 'job')], order='date desc', limit=1)
            if previous_dep:
                previous_dep.department_date_to = False
                previous_dep.last_record = True
