# -*- coding: utf-8 -*-
from odoo import models, fields, api, _, exceptions


class EmployeeEffectiveForm(models.Model):
    _name = 'employee.effective.form'
    _rec_name = 'employee_id'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    from_hr = fields.Boolean()
    contract_id = fields.Many2one(related='employee_id.contract_id', readonly=True, string='Contract')

    job_id = fields.Many2one(related='employee_id.job_id', readonly=True)
    department_id = fields.Many2one(related='employee_id.department_id', readonly=True, store=True)
    employee_salary = fields.Float(related='employee_id.contract_id.salary', readonly=True, tracking=True)
    remarks = fields.Text()
    employee_id = fields.Many2one('hr.employee', 'Employee Id', default=lambda item: item.get_user_id(),
                                  domain=[('state', '=', 'open')])
    employee_no = fields.Char(related='employee_id.emp_no', readonly=True,string='Employee Number', store=True)

    effective_form_type = fields.Selection([('first_tim_job', _('First Time Job')),
                                            ('return_from_leave', _('Return From Leave'))], default="first_tim_job")
    effective_form_date = fields.Date(tracking=True)

    state = fields.Selection(
        [('draft', _('Draft')), ('submit', _('Submit')), ('direct_manager', _('Direct Manager')),
         ('hr_manager', _('Hr Manager')), ('done', _('Done')),
         ('refused', _('Refused'))],
        default="draft", tracking=True)

    contract_start = fields.Date(related='contract_id.date_start', readonly=True,
                                 string='Contract Start Date')
    company_id = fields.Many2one('res.company',string="Company", default=lambda self: self.env.user.company_id)

    @api.onchange('employee_id')
    def get_hiring_date(self):
        for rec in self:
            if rec.employee_id:
                rec.effective_form_date = rec.contract_start

    @api.constrains('employee_id', 'effective_form_date')
    def once_request(self):
        for i in self:
            employee_id = self.env['employee.effective.form'].search([('id', '!=', i.id),('employee_id', '=', i.employee_id.id), ('state', '=', 'done')], limit=1)
            if employee_id:
                raise exceptions.Warning(_('Sorry, Not possible to request a effective Form more than once'))
            if i.contract_start:
               if i.effective_form_date < i.contract_start:
                  raise exceptions.Warning(_('Sorry, The First Hiring Date must be after the Contract Start Date'))

            if i.employee_id.contract_id.state != 'program_directory':
                raise exceptions.Warning(_('Sorry, The Employee Contract Must Be Approved Before Hiring Date'))
            if i.employee_id.state != 'open':
                raise exceptions.Warning(_('Sorry, The Employee Record Must Be Approved Before Hiring Date'))

    def draft_state(self):
        for item in self:
            if item.effective_form_type == 'first_tim_job' and item.state == 'done':
                item.employee_id.sudo().write({'first_hiring_date': False, 'joining_date': False})
                item.employee_id.contract_id.sudo().write({'hiring_date': False})
            item.state = "draft"

    def submit(self):
        '''for item in self:
            mail_content = "Hello I'm", item.employee_id.name, " request Need to ", item.effective_form_type,"Please approved thanks."
            main_content = {
                   'subject': _('Request Effective-%s Employee %s') % (item.effective_form_type, item.employee_id.name),
                   'author_id': self.env.user.partner_id.id,
                   'body_html': mail_content,
                   'email_to': item.department_id.email_manager,
                }
            self.env['mail.mail'].create(main_content).send()'''
        self.once_request()
        self.state = "submit"

    def direct_manager(self):
        self.state = "direct_manager"

    def hr_manager(self):
        self.state = "hr_manager"

    def done(self):
        for item in self:
            if item.effective_form_type == 'first_tim_job':
                item.employee_id.sudo().write({'first_hiring_date': item.effective_form_date,
                                               'joining_date': item.effective_form_date})
                item.employee_id.contract_id.sudo().write({'hiring_date': item.effective_form_date})
            else:
                return False
        self.state = "done"

    def refused(self):
        self.state = "refused"

    def unlink(self):
        for i in self:
            if i.state != 'draft':
                raise exceptions.Warning(_('You can not delete record in state not in draft'))
        return super(EmployeeEffectiveForm, self).unlink()

    def get_user_id(self):
        employee_id = self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)
        if employee_id:
            return employee_id.id
        else:
            return False
