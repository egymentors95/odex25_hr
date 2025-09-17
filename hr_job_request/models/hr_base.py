# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


# Hr_Employee
class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    def create_contract(self):
        self.constrain_on_job_creation()
        res = super(HrEmployee, self).create_contract()
        return res

    def open_sate(self):
        self.constrain_on_job_creation()
        res = super(HrEmployee, self).open_sate()
        return res

    @api.constrains('job_id', 'department_id')
    def constrain_on_job_creation(self):
        for rec in self:
            if rec.job_id.state != 'recruit':
                raise ValidationError(_("You need To open recruitment Before create New employee"))
            if rec.job_id.department_ids:
                if rec.department_id and rec.department_id not in rec.job_id.department_ids:
                    raise ValidationError(_("This Job not available for this department"))
            if rec.job_id.no_of_employee >= rec.job_id.expected_employees:
                raise ValidationError(_("No empty job position for this employee"))


# Hr_job
class Job(models.Model):
    _inherit = 'hr.job'

    expected_employees = fields.Integer(string='Total Forecasted Employees', compute="get_no_job", store=True,
                                        help='Expected number of employees for this job position after new recruitment.')
    no_of_recruitment = fields.Integer(string='Expected New Employees', copy=False, tracking=True,
                                       help='Number of new employees you expect to recruit.', default=1)
    job_request_ids = fields.One2many('hr.job.request', 'job_id', string="Job Requests")

    @api.depends('no_of_recruitment','employee_ids.job_id', 'employee_ids.active', 'employee_ids.state')
    def _compute_employees(self):
        employee_data = self.env['hr.employee'].read_group([('job_id', 'in', self.ids), ('state', '=', 'open')],
                                                           ['job_id'], ['job_id'])
        result = dict((data['job_id'][0], data['job_id_count']) for data in employee_data)
        for job in self:
            job.no_of_employee = result.get(job.id, 0)
            job.expected_employees = result.get(job.id, 0) + job.no_of_recruitment

    @api.depends('no_of_recruitment')
    def get_no_job(self):
        for rec in self:
            rec.expected_employees = rec.no_of_employee + rec.no_of_recruitment

    def set_recruit(self):
        for record in self:
            no_of_recruitment = record.no_of_recruitment
            record.write({'state': 'recruit', 'no_of_recruitment': no_of_recruitment, })
        return True

    def set_open(self):
        return self.write({
            'state': 'open',
            'no_of_recruitment': self.no_of_recruitment,
            # 'no_of_hired_employee': 0,
        })
