# -*- coding: utf-8 -*-

from odoo import models, fields, api, _, exceptions


class HrClearanceForm(models.Model):
    _name = 'hr.clearance.form'
    _rec_name = 'employee_id'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    from_hr_department = fields.Boolean()
    # employee_id = fields.Many2one(comodel_name='hr.employee')
    date = fields.Date(default=lambda self: fields.Date.today())
    date_deliver_work = fields.Date()
    job_id = fields.Many2one(related='employee_id.job_id', readonly=True)
    department_id = fields.Many2one(related='employee_id.department_id', readonly=True, store=True)
    employee_id = fields.Many2one('hr.employee', 'Employee Id', default=lambda item: item.get_user_id(),
                                  domain=[('state', '=', 'open')])
    employee_no = fields.Char(related='employee_id.emp_no', readonly=True,string='Employee Number', store=True)

    clearance_type = fields.Selection(selection=[("vacation", _("Vacation Clearance")),
                                                 ("final", _("Final Clearance"))], default='final')
    work_delivered = fields.Text()
    super_mg = fields.Selection(selection=[("approve", _("Approve")),
                                           ("refuse", _("Refuse"))], default='approve')
    super_refuse_cause = fields.Text(default='/')
    direct_mg = fields.Selection(selection=[("approve", _("Approve")),
                                            ("refuse", _("Refuse"))], default='approve')
    direct_refuse_cause = fields.Text(default='/')
    hr_mg = fields.Selection(selection=[("approve", _("Approve")),
                                        ("refuse", _("Refuse"))], default='approve')
    hr_refuse_cause = fields.Text(default='/')

    it_mg = fields.Selection(selection=[("approve", _("Approve")),
                                        ("refuse", _("Refuse"))], default='approve')
    it_refuse_cause = fields.Text(default='/')

    state = fields.Selection(selection=[("draft", _("Draft")),
                                        ("submit", _("Waiting Direct Manager")),
                                        ("direct_manager", _("Waiting IT Department")),
                                        ("info_system", _("Waiting Cyber ​​Security")),
                                        ("cyber_security", _("Waiting Admin Affairs")),
                                        ("admin_manager", _("Waiting Finance Approvals")),
                                        ("wait", _("Waiting HR Manager")),
                                        ("services_manager", _("Waiting Services Manager")),
                                        ("done", _("Approved")),
                                        ("refuse", _("Refused"))], default='draft', tracking=True)

    bank_attachment_id = fields.Many2many('ir.attachment', 'clearance_form_rel', 'bank_id', 'attach_id',
                                          string="Attachment",
                                          help='You can attach the copy of your document', copy=False)
    bank_comments = fields.Text()

    company_id = fields.Many2one('res.company',string="Company", default=lambda self: self.env.user.company_id)


    def check_custody(self):
        # Check if module is installed
        Module = self.env['ir.module.module'].sudo()
        emp_custody = Module.search([('state', '=', 'installed'), ('name', '=', 'exp_employee_custody')])
        petty_cash_modules = Module.search([('state', '=', 'installed'), ('name', '=', 'hr_expense_petty_cash')])
        modules = Module.search([('state', '=', 'installed'), ('name', '=', 'exp_custody_petty_cash')])
        fleet = Module.search([('state', '=', 'installed'), ('name', '=', 'odex_fleet')])
        employee_name = self.sudo().employee_id
        if emp_custody:
            # Check if employee has Employee Custody not in state Return done
            employee_custody = self.env['custom.employee.custody'].sudo().search([('employee_id', '=', employee_name.id), 
                               ('state', 'in', ['direct', 'admin', 'approve'])])
            if len(employee_custody) > 0:
                raise exceptions.Warning(_('Sorry, Can Not Clearance The Employee %s Has custody %s Not Return') % (
                      employee_name.name, len(employee_custody)))
        if petty_cash_modules:
            # Check if employee has Employee Petty Cash Payment not in state Return done
            employee_petty_cash_payment = self.env['petty.cash'].sudo().search([('partner_id', '=', employee_name.user_id.partner_id.id),
                                          ('state', 'in', ['submitted', 'running'])])
            if len(employee_petty_cash_payment) > 0:
                raise exceptions.Warning(_('Sorry, Can Not Clearance The Employee %s Has Petty Cash %s Not Return') % (
                      employee_name.name, len(employee_petty_cash_payment)))

        if fleet:
            # Check if employee has Employee fleet not in state Return done
            employee_fleet = self.env['vehicle.delegation'].sudo().search([('employee_id', '=', employee_name.id),
                 ('state', 'in', ['approve', 'in_progress'])])
            if len(employee_fleet) > 0:
                raise exceptions.Warning(_('Sorry, Can not Clearance The employee %s Has delegation vehicle %s Is Valid') % (
                        employee_name.name, len(employee_fleet)))

    @api.constrains('employee_id')
    def chick_hiring_date(self):
        for item in self:
            if item.employee_id:
                if not item.employee_id.first_hiring_date:
                    raise exceptions.Warning(_('You can not Request Clearance The Employee have Not First Hiring Date'))

    def draft(self):
        self.state = "draft"

    def submit(self):
        self.check_custody()
        '''for item in self:
            mail_content = "Hello I'm", item.employee_id.name, " request to Clearance Of ", item.clearance_type,"Please approved thanks."
            main_content = {
                   'subject': _('Request clearance-%s Employee %s') % (item.clearance_type, item.employee_id.name),
                   'author_id': self.env.user.partner_id.id,
                   'body_html': mail_content,
                   'email_to': item.department_id.email_manager,
                }
            self.env['mail.mail'].create(main_content).send()'''
        self.state = "submit"

    def direct_manager(self):
        self.check_custody()
        for rec in self:
            manager = rec.sudo().employee_id.parent_id
            hr_manager = rec.sudo().employee_id.company_id.hr_manager_id
            if manager:
               if manager.user_id.id == rec.env.uid or hr_manager.user_id.id == rec.env.uid:
                  rec.write({'state': 'direct_manager'})
               else:
                  raise exceptions.Warning(_("Sorry, The Approval For The Direct Manager '%s' Only OR HR Manager!")%(rec.employee_id.parent_id.name))
            else:
                rec.write({'state': 'direct_manager'})

    def info_system(self):
        self.check_custody()
        self.state = "info_system"

    def admin_manager(self):
        self.check_custody()
        self.state = "admin_manager"

    def wait(self):

        for item in self:

            if not item.bank_attachment_id and item.clearance_type != 'vacation':
                raise exceptions.Warning(_('The Clearance to be completed after the Bank Clearance Attachment'))
        self.state = "wait"

    def cyber_security(self):
        self.check_custody()
        self.state = "cyber_security"

    def services_manager(self):
        self.check_custody()
        self.state = "services_manager"

    def done(self):
        self.check_custody()
        if not self.bank_attachment_id:
            raise exceptions.Warning(_('The Clearance to be completed after the Bank Clearance Attachment'))

        self.employee_id.write({'is_calender': True})
        self.state = "done"

    def refuse(self):
        self.state = "refuse"

    #Refuse For The Direct Manager Only
    def direct_manager_refused(self):
        for rec in self:
            manager = rec.sudo().employee_id.parent_id
            hr_manager = rec.sudo().employee_id.user_id.company_id.hr_manager_id
            if manager:
                if manager.user_id.id == rec.env.uid or hr_manager.user_id.id == rec.env.uid:
                   rec.refuse()
                else:
                    raise exceptions.Warning(_("Sorry, The Refuse For The Direct Manager '%s' Only OR HR Manager!") % (manager.name))
            else:
                 rec.refuse()

    def get_user_id(self):
        employee_id = self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)
        if employee_id:
            return employee_id.id
        else:
            return False

    def unlink(self):
        for i in self:
            if i.state != 'draft':
                raise exceptions.Warning(_('You can not delete record in state not in draft'))
        return super(HrClearanceForm, self).unlink()
