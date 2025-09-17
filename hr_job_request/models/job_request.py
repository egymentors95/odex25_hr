# -*- coding: utf-8 -*-

from odoo import models, fields, api, _, exceptions
from odoo.exceptions import ValidationError


class HrJobRequest(models.Model):
    _name = 'hr.job.request'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    @api.model
    def default_get(self, field_list):
        result = super(HrJobRequest, self).default_get(field_list)
        employee = self.env['hr.employee'].search([('user_id', '=', self.env.user.id)], limit=1)
        if employee:
            result['department_id'] = employee.department_id.id if employee.department_id else False
        return result

    name = fields.Char(string="Name of Request", required=True)
    date = fields.Date(string="Request Date", required=True)
    quarter = fields.Selection(string="Quarter",
                               selection=[('all_quarter', 'All Quarter'), ('first_quarter', 'First Quarter'),
                                          ('second_quarter', 'Second Quarter'),
                                          ('third_quarter', 'Third Quarter'),
                                          ('fourth_quarter', 'Fourth Quarter')], default='all_quarter')
    department_id = fields.Many2one('hr.department', string="Department", required=True)
    job_id = fields.Many2one('hr.job', string="Job", required=True)
    state = fields.Selection(selection=[('draft', 'Draft'),
                                        ('confirm', 'Confirm'),
                                        ('hr_approve', 'Hr Approve'),
                                        ('manager_approve', 'Manager Approve'),
                                        ('refused', 'Refused')], default='draft')
    needed_employee = fields.Integer(string="Needed Employee", required=True)
    number_of_employees = fields.Integer(related="job_id.no_of_employee", string="Current Employees", store=True)
    expected_employee = fields.Integer(string="Expected jobs", compute="get_jobs", store=True)
    number_of_job_empty = fields.Integer(string="Empty jobs", compute="get_jobs", store=True)
    number_of_job_empty_total = fields.Integer(string="Total Empty jobs", compute="get_jobs", store=True)
    job_requirements = fields.Html('Job Requirements')
    company_id = fields.Many2one('res.company',string="Company", default=lambda self: self.env.user.company_id)

    def unlink(self):
        for rec in self:
            if rec.state != 'draft':
                raise exceptions.Warning(_('You can not delete record in state not in draft'))
        return super(HrJobRequest, self).unlink()

    @api.depends('needed_employee', 'job_id', 'state')
    def get_jobs(self):
        for rec in self:
            if rec.job_id.no_of_employee == rec.job_id.expected_employees:
                rec.number_of_job_empty_total = rec.needed_employee
            else:
                rec.number_of_job_empty_total = rec.needed_employee + rec.job_id.no_of_recruitment
            rec.number_of_job_empty = rec.job_id.no_of_recruitment
            rec.expected_employee = rec.number_of_job_empty_total + rec.number_of_employees

    def action_confirm(self):
        for rec in self:
            rec.state = 'confirm'

    def department_manager(self):
        for rec in self:
            rec.state = 'department_manager'

    def action_hr_approve(self):
        for rec in self:
            rec.state = 'hr_approve'

    def action_manage_approve(self):
        for rec in self:
            rec.state = 'manager_approve'
            rec.job_id.sudo().write({'no_of_recruitment': rec.number_of_job_empty_total, })
            # 'expected_employees':rec.expected_employee})

    def action_refused(self):
        for rec in self:
            if rec.state == 'manager_approve':
                empty = rec.job_id.expected_employees - rec.job_id.no_of_employee
                record = rec.job_id.no_of_recruitment - rec.needed_employee
                if empty < rec.needed_employee or record < 0:
                    raise ValidationError(_("You Can not Cancel used jobs"))
                rec.job_id.sudo().write({'no_of_recruitment': record, })
            rec.state = 'refused'

    def action_set_draft(self):
        for rec in self:
            rec.state = 'draft'
