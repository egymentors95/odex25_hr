# -*- coding: utf-8 -*-
from datetime import timedelta

from odoo import models, fields, _, exceptions


class HrReasonsLateness(models.Model):
    _name = 'hr.reasons.lateness'
    _rec_name = 'reasons'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    request_date = fields.Date(default=lambda self: fields.Date.today())
    latest_date = fields.Date()
    reasons = fields.Text()
    from_hr_depart = fields.Boolean(string='Another Employee')
    department_id = fields.Many2one(related="employee_id.department_id", readonly=True, store=True)
    job_id = fields.Many2one(related="employee_id.job_id", readonly=True)
    employee_id = fields.Many2one('hr.employee', 'Employee Id', default=lambda item: item.get_user_id())
    state = fields.Selection([('draft', _('Draft')),
                              ('send', _('Send')),
                              ('direct_manager', _('Direct Manager')),
                              ('hr_manager', _('HR Manager')),
                              ('refused', _('Refused'))], default="draft")
    company_id = fields.Many2one(related='employee_id.company_id')
    employee_no = fields.Char(related='employee_id.emp_no', string='Employee Number',store=True)
    is_branch = fields.Many2one(related='department_id.branch_name', store=True, readonly=True)

    def unlink(self):
        for rec in self:
            if rec.state != 'draft':
                raise exceptions.Warning(_('You can not delete record in state not in draft'))
        return super(HrReasonsLateness, self).unlink()

    def get_user_id(self):
        employee_id = self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)
        if employee_id:
            return employee_id.id
        else:
            return False

    def draft_state(self):
        self.state = "draft"
        self.call_cron_function()

    def button_submit(self):
        self.state = "send"

    def hr_manager(self):
        self.state = "hr_manager"
        self.call_cron_function()

    def call_cron_function(self):
        transaction = self.env['hr.attendance.transaction']
        start_date = self.request_date
        end_date = self.latest_date
        delta = end_date - start_date
        for i in range(delta.days + 1):
            day = start_date + timedelta(days=i)
            transaction.process_attendance_scheduler_queue(day, self.employee_id)

    def direct_manager(self):
        self.state = "direct_manager"

    def set_to_draft(self):
        self.state = "draft"
        self.call_cron_function()

    def refused(self):
        self.state = "refused"
