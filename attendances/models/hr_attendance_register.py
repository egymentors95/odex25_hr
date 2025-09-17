# -*- coding: utf-8 -*-
from datetime import datetime

from odoo import models, fields, api, _, exceptions


class HrAttendanceRegister(models.Model):
    _name = 'hr.attendance.register'
    _rec_name = 'employee_id'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'action_date DESC'

    action_type = fields.Selection(selection=[('sign_in', _('Sign In')),
                                              ('sign_out', _('Sign Out'))], string='Action Type')
    action_date = fields.Datetime(string='Attendance Date')
    from_hr_depart = fields.Boolean(string='Another Employee')
    department_id = fields.Many2one(related="employee_id.department_id", readonly=True, store=True)
    job_id = fields.Many2one(related="employee_id.job_id", readonly=True)
    employee_id = fields.Many2one('hr.employee', index=True, default=lambda item: item.get_user_id())
    employee_no = fields.Char(related='employee_id.emp_no', readonly=True,string='Employee Number', store=True)

    note_text = fields.Text()
    register_date = fields.Date(string='Register Date', default=lambda self: fields.Date.today())
    state = fields.Selection(
        [('draft', _('Draft')),
         ('send', _('Send')),
         ('direct_manager', _('Direct Manager')),
         ('hr_manager', _('HR Manager')),
         ('refused', _('Refused'))], default="draft",tracking=True)
    date = fields.Date(string='Date')

    company_id = fields.Many2one(related='employee_id.company_id',string='Company')

    is_branch = fields.Many2one(related='department_id.branch_name', store=True, readonly=True)

    all_employees = fields.Boolean(string='All Employees',default=False)

    employee_ids = fields.Many2many('hr.employee', string='Employees')

    @api.onchange('all_employees')
    def chick_all_employees(self):
        if self.all_employees==False:
           self.employee_ids=False

    def unlink(self):
        for rec in self:
            if rec.state != 'draft':
                raise exceptions.Warning(_('You can not delete record in state not in draft'))
        return super(HrAttendanceRegister, self).unlink()

    @api.constrains('action_date')
    def compute_date(self):
        for item in self:
            today = fields.Date.from_string(fields.Date.today())
            datee = item.action_date
            max_days = item.employee_id.resource_calendar_id.register_before
            if datee:
                attendance_date = datetime.strptime(str(datee), "%Y-%m-%d %H:%M:%S")
                currnt_hour = datetime.now().hour + 3
                hour_attendance = attendance_date.hour + 3

                now_date = datetime.now().strftime('%Y-%m-%d')
                currnt_date = datetime.strptime(str(datee), '%Y-%m-%d %H:%M:%S').strftime('%Y-%m-%d')
                deff_days = (today - fields.Date.from_string(currnt_date)).days
                if deff_days > max_days:
                    raise exceptions.Warning(_('Sorry, You can not Register Attendance Before %s Days.')% max_days)
                if deff_days < 0 and item.all_employees==False:
                    raise exceptions.Warning(_('You can not Register Attendance After Today'))
                # item.date = currnt_date
                priv_register = self.env['hr.attendance.register'].search([('employee_id', '=', item.employee_id.id),('id','!=',item.id)])
                #for reg in priv_register:
                #   date = datetime.strptime(str(reg.action_date), '%Y-%m-%d %H:%M:%S').strftime('%Y-%m-%d')
                #   if date == currnt_date:
                #      raise exceptions.Warning(_('You can not Register Attendance More Than once in The Same day'))

                if currnt_date > str(item.register_date) and item.all_employees==False:
                   raise exceptions.Warning(_('You can not Register Attendance At Future Date'))

                if hour_attendance > currnt_hour and now_date==currnt_date and item.all_employees==False:
                   raise exceptions.Warning(_('You can not Register Attendance Before The Time'))

    def draft_state(self):
        self.state = "draft"

    def button_submit(self):
        if self.all_employees == True and not self.employee_ids:
           raise exceptions.Warning(_("Sorry,You must enter the Names Of Employees!"))
        self.state = "send"

    def direct_manager(self):
        for rec in self:
            manager = rec.sudo().employee_id.parent_id
            hr_manager = rec.sudo().employee_id.company_id.hr_manager_id
            if rec.all_employees == True and not rec.employee_ids:
               raise exceptions.Warning(_("Sorry,You must enter the Names Of Employees!"))

            if manager:
               if (manager.user_id.id == rec.env.uid or hr_manager.user_id.id == rec.env.uid):
                    rec.write({'state': 'direct_manager'})
               else:
                   raise exceptions.Warning(_("Sorry, The Approval For The Direct Manager '%s' Only OR HR Manager!")%(rec.employee_id.parent_id.name))
            else:
                rec.write({'state': 'direct_manager'})

    #Refuse For The Direct Manager
    def direct_manager_refused(self):
        for rec in self:
            manager = rec.sudo().employee_id.parent_id
            hr_manager = rec.sudo().employee_id.company_id.hr_manager_id
            if manager:
                if manager.user_id.id == rec.env.uid or hr_manager.user_id.id == rec.env.uid:
                   rec.refused()
                else:
                    raise exceptions.Warning(_("Sorry, The Refuse For The Direct Manager '%s' Only OR HR Manager!") % (manager.name))
            else:
                 rec.refused()

    def hr_manager(self):
        for rec in self:
            extract_date = datetime.strptime(str(rec.action_date), "%Y-%m-%d %H:%M:%S").date()
            if rec.all_employees== False:
               rec.env['attendance.attendance'].create({
                   'employee_id': rec.employee_id.id,
                   'name': rec.action_date,
                   'action': rec.action_type,
                   'action_date': rec.action_date.date(),
                   'action_type': 'manual',
               })

               rec.state = "hr_manager"
               rec.call_cron_function()
            else:
               for emp in rec.employee_ids:
                   rec.env['attendance.attendance'].create({
                      'employee_id': emp.id,
                      'name': rec.action_date,
                      'action': rec.action_type,
                      'action_date': rec.action_date.date(),
                      'action_type': 'manual',
                   })
               rec.call_cron_function()
               rec.state = "hr_manager"


    def set_to_draft(self):
        for item in self:
            if item.all_employees== False:
               attendances = self.env['attendance.attendance'].search([('action_date', '=', item.action_date),
                                  ('employee_id', '=', item.employee_id.id)],order="name asc")
               for attendance in attendances:
                   if attendance.name == item.action_date:
                      attendance.sudo().unlink()
               item.state = "draft"
               item.call_cron_function()
            else:
               for emp in item.employee_ids:
                   attendances = self.env['attendance.attendance'].search([('action_date', '=', item.action_date),
                                      ('employee_id', '=', emp.id)],order="name asc")

                   for attendance in attendances:
                       if attendance.name == item.action_date:
                          attendance.sudo().unlink()
               item.call_cron_function()
               item.state = "draft"


    def call_cron_function(self):
        for rec in self:
            if rec.all_employees== False:
               self.env['hr.attendance.transaction'].process_attendance_scheduler_queue(rec.action_date, rec.employee_id)
            else:
               for emp in rec.employee_ids:
                   self.env['hr.attendance.transaction'].process_attendance_scheduler_queue(rec.action_date, emp)

    def refused(self):
        self.state = "refused"

    def get_user_id(self):
        employee_id = self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)
        if employee_id:
            return employee_id.id
        else:
            return False
