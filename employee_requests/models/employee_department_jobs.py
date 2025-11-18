# -*- coding: utf-8 -*-
import datetime
from dateutil import relativedelta
from odoo import api, fields, models, _, exceptions


class EmployeeDepartmentJobs(models.Model):
    _name = 'employee.department.jobs'
    _rec_name = 'employee_id'
    _description = 'Employee Department and Jobs'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    date = fields.Date()
    comment = fields.Text()
    state = fields.Selection(selection=[('draft', _('Draft')),
                                        ('confirm', _('Department Manager')),
                                        ('hr_officer', _('HR Officer')),
                                        ('confirm2', _('Department Manager2')),
                                        ('hr_manager', _('HR Manager')),
                                        ('approved', _('Approved')), ('refused', _('Refused'))],
                             default='draft', tracking=True)
    promotion_type = fields.Selection(
        selection=[('department', _('Department')), ('job', _('Job')), ('both', _('Both'))], tracking=True)

    # relational fields
    employee_id = fields.Many2one(comodel_name="hr.employee", tracking=True, domain=[('state', '=', 'open')])
    employee_no = fields.Char(related='employee_id.emp_no', readonly=True,string='Employee Number', store=True)
    # old_department_id = fields.Many2one(comodel_name='hr.department', related='employee_id.department_id')
    old_department_2_id = fields.Many2one(comodel_name='hr.department')
    # old_job_id = fields.Many2one(comodel_name='hr.job', related='employee_id.job_id')
    old_job_2_id = fields.Many2one(comodel_name='hr.job')
    new_department_id = fields.Many2one(comodel_name='hr.department')
    new_job_id = fields.Many2one(comodel_name='hr.job')

    new_manager_id = fields.Many2one(comodel_name='hr.employee', related='new_department_id.manager_id')
    old_manager_id = fields.Many2one(comodel_name='hr.employee', related='old_department_2_id.manager_id')

    old_job_date = fields.Date(string='Old Job Date', readonly=True)
    last_record = fields.Boolean(string='Is Last Record?', default=True)

    service_year = fields.Integer(compute='_compute_duration', store=True)
    service_month = fields.Integer(compute='_compute_duration', store=True)
    service_day = fields.Integer(compute='_compute_duration', store=True)

    company_id = fields.Many2one(related='employee_id.company_id', string="Company")

    @api.onchange('new_department_id', 'new_job_id')
    def not_reused_same_dep_job(self):
        for item in self:
            if item.new_department_id.department_type == 'unit':
                item.new_manager_id = item.new_department_id.parent_id.manager_id
            else:
                item.new_manager_id = item.new_department_id.manager_id

            if item.employee_id:
                if item.old_department_2_id.id == item.new_department_id.id:
                    raise exceptions.Warning(_('You Can Not Choose The Same Department Name'))
                if item.old_job_2_id.id == item.new_job_id.id:
                    raise exceptions.Warning(_('You Can Not Choose The Same Job Name'))

            if  item.new_job_id:
              if item.new_job_id.no_of_recruitment < 1:
                 raise exceptions.Warning(_('There Is No Vacancy For This Job Name %s')% item.new_job_id.name)

    # store department and job
    @api.onchange('employee_id')
    def store_level_group_and_degree_values(self):
        for item in self:
            if item.sudo().employee_id:
                if not item.employee_id.first_hiring_date:
                    raise exceptions.Warning(
                        _('You can not Request Change Department or job The Employee have Not First Hiring Date'))
            item.old_department_2_id = item.employee_id.department_id
            item.old_job_2_id = item.employee_id.job_id
            item.old_manager_id = item.old_department_2_id.manager_id
            item.old_job_date = item.employee_id.joining_date

    @api.depends('date', 'old_job_date')
    def _compute_duration(self):
        for item in self:
            if item.sudo().employee_id.first_hiring_date and item.date:
                if item.date <= item.sudo().employee_id.first_hiring_date:
                    raise exceptions.Warning(_('Sorry, Procedure Date Must Be After Employee Hiring Date'))
            if item.old_job_date and item.date:
                date_start = datetime.datetime.strptime(str(item.old_job_date), '%Y-%m-%d').date()
                date_end = datetime.datetime.strptime(str(item.date), '%Y-%m-%d').date()
                item.service_year = relativedelta.relativedelta(date_end, date_start).years
                item.service_month = relativedelta.relativedelta(date_end, date_start).months
                item.service_day = relativedelta.relativedelta(date_end, date_start).days
                if item.date <= item.old_job_date and item.promotion_type != 'department':
                    raise exceptions.Warning(_('Sorry, Procedure Date Must Be After Old Job Date'))

    def confirm(self):
        for item in self:
            previous_record = self.search([('employee_id', '=', item.employee_id.id),
                                           ('id', '!=', item.id),
                                           ('state', '=', 'approved'),
                                           ('promotion_type', '=', item.promotion_type),
                                           ('last_record', '=', True)
                                           ], order='date desc', limit=1)
            if previous_record:
                previous_record.last_record = False
        self.state = 'confirm'

    def hr_officer(self):
        for rec in self:
            if rec.promotion_type == 'job':
                rec.state = 'confirm2'
            else:
                rec.state = 'hr_officer'

    def confirm2(self):
        for rec in self:
            if rec.promotion_type != 'job':
                if rec.new_manager_id and rec.new_manager_id.user_id.id != rec.env.user.id:
                    raise exceptions.Warning(
                        _('Sorry, It Must Be Approved By The %s Manager') % rec.new_manager_id.name)
            else:
                if rec.old_manager_id.user_id.id != rec.env.user.id:
                    raise exceptions.Warning(
                        _('Sorry, It Must Be Approved By The %s Manager') % rec.old_manager_id.name)
        self.state = 'confirm2'

    def hr_manager(self):
        self.state = 'hr_manager'

    def approved(self):
        for item in self:
            if item.promotion_type == 'department':
                if item.new_department_id:
                    item.employee_id.write({
                        'department_id': item.new_department_id.id
                    })
                    item.employee_id._onchange_department()
            elif item.promotion_type == 'job':
                if item.new_job_id:
                    item.employee_id.write({
                        'job_id': item.new_job_id.id,
                        'joining_date': item.date
                    })
            elif item.promotion_type == 'both':
                if item.new_job_id and item.new_department_id:
                    item.employee_id.write({
                        'department_id': item.new_department_id.id,
                        'job_id': item.new_job_id.id,
                        'joining_date': item.date
                    })
                    item.employee_id._onchange_department()
        self.state = 'approved'

    def refused(self):
        self.state = 'refused'

    def draft(self):
        for item in self:
            if not item.last_record:
                raise exceptions.Warning(_('The record Cannot be Set To Draft Because It Is Not Last Record'))
            previous_record = self.search([('employee_id', '=', item.employee_id.id),
                                           ('id', '!=', item.id),
                                           ('state', '=', 'approved'),
                                           ('promotion_type', '=', item.promotion_type),
                                           ('last_record', '=', False)], order='date desc', limit=1)

            if item.promotion_type == 'department':
                if item.new_department_id:
                    item.employee_id.write({
                        'department_id': item.old_department_2_id.id
                    })
                    item.employee_id._onchange_department()
            elif item.promotion_type == 'job':
                if item.new_job_id:
                    item.employee_id.write({
                        'job_id': item.old_job_2_id.id,
                        'joining_date': item.old_job_date
                    })
            elif item.promotion_type == 'both':
                if item.new_job_id and item.new_department_id:
                    item.employee_id.write({
                        'department_id': item.old_department_2_id.id,
                        'job_id': item.old_job_2_id.id,
                        'joining_date': item.old_job_date
                    })
                    item.employee_id._onchange_department()
            if previous_record:
                previous_record.last_record = True
        self.state = 'draft'

    def unlink(self):
        for i in self:
            if i.state != 'draft':
                raise exceptions.Warning(_('You can not delete record in state not in draft'))
        return super(EmployeeDepartmentJobs, self).unlink()

    def print_report(self):
        return self.env.ref('employee_requests.employee_department_jobs_action_report').report_action(self)
