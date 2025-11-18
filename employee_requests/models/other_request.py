# -*- coding: utf-8 -*-

from odoo import api, fields, models, _, exceptions
from hijri_converter import convert


class EmployeeOtherRequest(models.Model):
    _name = 'employee.other.request'
    _rec_name = 'employee_id'
    _description = 'Other Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc'

    from_hr = fields.Boolean()
    date = fields.Date(default=lambda self: fields.Date.today())
    comment = fields.Text()
    state = fields.Selection(selection=[('draft', _('Draft')), 
                                        ('submit', _('Waiting Direct Manager')),
                                        ('confirm', _('Wait HR Department')),
                                        ('approved', _('Approval')),
                                        ('refuse', _('Refused'))],
                             default='draft', tracking=True)
    request_type = fields.Selection(selection=[('dependent', _('Dependent')),
                                               ('insurance', _('Insurance')), ('card', _('Business Card')),
                                               ('qualification', _('Qualification')),
                                               ('certification', _('Certification')),
                                               ('salary_define', _('Salary Define')),
                                               ('salary_fixing', _('Salary Fixing')),
                                               ('suggestion', _('Suggestion')),
                                               ('complaint', _('Complaint')),
                                               ('other_requests', _('Other Requests'))], tracking=True)

    # relational fields
    employee_id = fields.Many2one('hr.employee', default=lambda item: item.get_user_id(),
                                  domain=[('state', '=', 'open')])
    employee_no = fields.Char(related='employee_id.emp_no', readonly=True,string='Employee Number', store=True)
    department_id = fields.Many2one(comodel_name='hr.department', related='employee_id.department_id', readonly=True,store=True)
    job_id = fields.Many2one(comodel_name='hr.job', related='employee_id.job_id', readonly=True)
    contract_statuss = fields.Selection(related='employee_id.contract_id.contract_status', readonly=True)

    employee_dependant = fields.One2many('hr.employee.dependent', 'request_id', _('Employee Dependants'))

    qualification_employee = fields.One2many('hr.qualification', 'request_id', _('Employee Qualification'))
    certification_employee = fields.One2many('hr.certification', 'request_id', _('Employee Certification'))
    create_insurance_request = fields.Boolean()
    print_type = fields.Selection(selection=[('detail', _("With Details")),
                                             ('no_detail', _("Without Details")),
                                             ('no_salary', _("Without Salary"))], string='Print Type')
    destination = fields.Many2one('salary.destination', string='Destination')
    parent_request_id = fields.Many2one('employee.other.request')

    company_id = fields.Many2one('res.company', string="Company", default=lambda self: self.env.user.company_id)

    is_branch = fields.Many2one(related='department_id.branch_name', store=True, readonly=True)

    classification_id = fields.Many2one('hr.classification',string ='Classification')
    def print_with_details(self):
        return self.env.ref('employee_requests.action_report_employee_identification').report_action(self)

    def print_with_details2(self):
        return self.env.ref('employee_requests.action_report_employee_identify_2').report_action(self)

    def print_with_details3(self):
        return self.env.ref('employee_requests.action_report_employee_identify_3').report_action(self)

    def print_without_details(self):
        return self.env.ref('employee_requests.action_report_employee_identify_3').report_action(self)

    def print_salary_confirmation(self):
        return self.env.ref('employee_requests.salary_conf_report_act').report_action(self)

    '''@api.onchange('employee_id')
    def chick_hiring_date(self):
        for item in self:
            if item.employee_id:
                if not item.employee_id.first_hiring_date:
                    raise exceptions.Warning(
                        _('You can not Request Other Request The Employee have Not First Hiring Date'))'''

    def get_user_id(self):
        employee_id = self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)
        if employee_id:
            return employee_id.id
        else:
            return False

    def submit(self):
        for item in self:
            if item.employee_id:
                if not item.employee_id.first_hiring_date:
                    raise exceptions.Warning(
                        _('You can not Request Other Request The Employee have Not First Hiring Date'))
            if item.request_type == 'dependent':
                if not item.employee_dependant:
                    raise exceptions.Warning(_('Please The dependents were not Included'))
                # if item.employee_id.contract_id.contract_status == 'single':
                # raise exceptions.Warning(_('You can not Add Fimaly record Because Employee is Single'))
                else:
                    for rec in item.employee_dependant:
                        if not rec.attachment:
                            raise exceptions.Warning(_('Please Insert dependents Attachments Files Below!'))

            if item.request_type == 'qualification':
                if not item.qualification_employee:
                    raise exceptions.Warning(_('Please The qualification or certification were not Insert Below!'))
                for rec in item.qualification_employee:
                    if not rec.attachment:
                        raise exceptions.Warning(_('Please Insert Attachments Files Below!'))

            if item.request_type == 'certification':
                if not item.certification_employee:
                    raise exceptions.Warning(_('Please The qualification or certification were not Insert Below!'))
                for rec in item.certification_employee:
                    if not rec.attachment:
                        raise exceptions.Warning(_('Please Insert Attachments Files Below!'))

            if item.request_type in ['suggestion', 'complaint']:
                item.state = "submit"
            else:
                item.state = "confirm"

    def confirm(self):
        #self.state = 'confirm'
        for rec in self:
            manager = rec.sudo().employee_id.parent_id
            hr_manager = rec.sudo().employee_id.company_id.hr_manager_id
            if manager:
               if (manager.user_id.id == rec.env.uid or hr_manager.user_id.id == rec.env.uid):
                    rec.write({'state': 'confirm'})
               else:
                   raise exceptions.Warning(_("Sorry, The Approval For The Direct Manager '%s' Only OR HR Manager!")%(rec.employee_id.parent_id.name))
            else:
                rec.write({'state': 'confirm'})

    def approved(self):
        for item in self:
            if item.request_type == 'dependent':
                if item.employee_dependant:
                    item.employee_dependant.write({
                        'contract_id': item.employee_id.contract_id.id,
                    })
                    if self.create_insurance_request:
                        self.env['employee.other.request'].create({
                            'employee_id': item.employee_id.id,
                            'department_id': item.department_id.id,
                            'job_id': item.job_id.id,
                            'contract_statuss': item.contract_statuss,
                            'date': item.date,
                            'request_type': 'insurance',
                            'parent_request_id': item.id,
                            'comment': item.comment,
                            # 'employee_dependant': [(0, 0, line) for line in line_vals],
                            'state': 'submit'
                        })

            if item.request_type == 'qualification':
                if item.qualification_employee:
                    item.qualification_employee.write({
                        'qualification_relation_name': item.employee_id.id,
                    })

            if item.request_type == 'certification':
                if item.certification_employee:
                    item.certification_employee.write({
                        'certification_relation': item.employee_id.id,
                    })

        self.state = 'approved'

    def refuse(self):
        for item in self:
            if item.request_type == 'dependent':
                if item.employee_dependant:
                    item.employee_dependant.write({
                        'contract_id': False
                    })

            if item.request_type == 'qualification':
                if item.qualification_employee:
                    item.qualification_employee.write({
                        'qualification_relation_name': False
                    })

            if item.request_type == 'certification':
                if item.certification_employee:
                    item.certification_employee.write({
                        'certification_relation': False
                    })

        self.state = 'refuse'

    #Refuse For The Direct Manager
    def direct_manager_refused(self):
        for rec in self:
            manager = rec.sudo().employee_id.parent_id
            hr_manager = rec.sudo().employee_id.company_id.hr_manager_id
            if manager:
                if manager.user_id.id == rec.env.uid or hr_manager.user_id.id == rec.env.uid:
                   rec.refuse()
                else:
                    raise exceptions.Warning(_("Sorry, The Refuse For The Direct Manager '%s' Only OR HR Manager!") % (manager.name))
            else:
                 rec.refuse()

    def draft(self):
        for item in self:
            if item.request_type == 'dependent':
                if item.employee_dependant:
                    item.employee_dependant.write({
                        'contract_id': False
                    })

        self.state = 'draft'

    def change_current_date_hijri(self):
        date = fields.Date.from_string(self.date)
        year = date.year
        day = date.day
        month = date.month
        hijri_date = convert.Gregorian(year, month, day).to_hijri()
        return hijri_date

    def unlink(self):
        for rec in self:
            if rec.state != 'draft':
                raise exceptions.Warning(_('You can not delete record in state not in draft'))
        return super(EmployeeOtherRequest, self).unlink()


class salaryDestination(models.Model):
    _name = 'salary.destination' 
    _description = 'Salary Destination'

    name = fields.Char(string='Name')
    english_name = fields.Char(string='English Name')

# Hr_Employee_dependent
class EmployeeDependent(models.Model):
    _inherit = 'hr.employee.dependent'

    request_id = fields.Many2one('employee.other.request')


# Hr_Employee_Qualification
class Qualification(models.Model):
    _inherit = 'hr.qualification'

    request_id = fields.Many2one('employee.other.request')


# Hr_Employee_Certification
class HrCerti(models.Model):
    _inherit = 'hr.certification'

    request_id = fields.Many2one('employee.other.request')

class HrCclassification(models.Model):
    _name = 'hr.classification'
    _rec_name = 'name'

    name = fields.Char(string='الاسم')  # Translatable
    active = fields.Boolean(default=True, string='نشط')
