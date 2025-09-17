# -*- coding: utf-8 -*-

import datetime

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class EmployeeDependent(models.Model):
    _name = "hr.employee.dependent"
    _description = "Employee Dependent"

    name = fields.Char()
    age = fields.Integer(string="Age", compute="_compute_age")
    birthday = fields.Date(string="Birthday")
    gender = fields.Selection(
        selection=[("male", "Male"), ("female", "Female")], default="male"
    )
    relation = fields.Selection(
        selection=[('Husband', 'Husband/Wife'), ('child', 'child'), ('father', 'Father'), ('mother', 'Mother'), ('other', 'Other')])
    nationality = fields.Many2one(comodel_name="res.country")
    passport_no = fields.Char()
    passport_issue_date = fields.Date(string="Passport Issue Date")
    passport_expire_date = fields.Date(string="Passport Expire Date")
    remarks = fields.Text(string="Remarks")
    contract_id = fields.Many2one(comodel_name="hr.contract")
    degree_medical_insu = fields.Char(string="Degree Medical Insurance")
    medical_insurance_num = fields.Char(string="Medical Insurance Number")
    identity_num = fields.Char(string="Identity Number")
    has_ticket = fields.Boolean(string="Has Ticket?", default=False)
    attachment = fields.Many2many('ir.attachment', 'dependent_rel', 'dependent_id', 'attachment_id',
                                  string="Attachment",
                                  help='You can attach the copy of your document', copy=False)

    has_Insurance = fields.Boolean(_('Has Insurance?'))

    @api.onchange("birthday")
    def _compute_age(self):
        today = datetime.date.today()
        format_str = "%Y-%m-%d"  # The format
        for item in self:
            if item.birthday:
                birthday = datetime.datetime.strptime(str(item.birthday), format_str)
                age = today.year - birthday.year
                if today.month < birthday.month or today.month == birthday.month and today.day < birthday.day:
                    age -= 1
                if item.birthday >= today:
                    raise ValidationError(_("Sorry,The Birthday Must Be Less than Date Today"))
                item.age = age


class EmployeeDependentAttachment(models.Model):
    _inherit = 'ir.attachment'
    dependent_id = fields.Many2one('hr.employee.dependent',
                                   string="Attachment", invisible=1)
