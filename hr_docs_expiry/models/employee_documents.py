# -*- coding: utf-8 -*-

from odoo import api, fields, models
from datetime import datetime, date, timedelta
from odoo.tools.translate import _
from odoo.exceptions import Warning



class HrEmployeeDocument(models.Model):
    _name = "hr.employee.document"
    _description = "HR Employee Documents"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    @api.model
    def mail_reminder(self):
        now = datetime.now() + timedelta(days=1)
        date_now = now.date()
        match = self.search([])
        for i in match:
            if i.expiry_date:
                exp_date = fields.Date.from_string(i.expiry_date) - timedelta(days=i.reminder_before)
                if date_now >= exp_date and i.employee_ref.state not in ['draft', 'out_of_service']:
                    template = self.env.ref('hr_docs_expiry.email_template_document_expiry_reminder')
                    template.send_mail(i.id)
                    # template.send_mail(i.id, force_send=True, raise_exception=False)
            if i.employee_ref.state not in ['draft', 'out_of_service'] and i.employee_ref.employee_dependant:
                for dependant in i.employee_ref.employee_dependant:
                    if dependant.relation == 'child' and dependant.age >= 18:
                        template2 = self.env.ref('hr_docs_expiry.email_template_child_age_check')
                        template2.send_mail(i.id)
                        # template.send_mail(i.id, force_send=True, raise_exception=False)

    @api.constrains('expiry_date', 'saudi_id', 'iqama_id', 'issue_date')
    def check_expr_date(self):
        for each in self:
            if self.expiry_date:
                exp_date = fields.Date.from_string(each.expiry_date)
                if exp_date < date.today():
                    raise Warning('Your Document Is Expired.')
        if self.saudi_id:
            if len(self.saudi_id) != 10:
                raise Warning(_('Saudi ID must be 10 digits'))
            if self.saudi_id[0] != '1':
                raise Warning(_('The Saudi ID number should begin with 1'))

        if self.iqama_id:
            if len(self.iqama_id) != 10:
                raise Warning(_('Identity must be 10 digits'))
            if self.iqama_id[0] != '2' and self.iqama_id[0] != '4' and self.iqama_id[0] != '3':
                raise Warning(_('Identity must begin with 2 or 3 or 4'))

        if self.expiry_date and self.issue_date:

            if self.expiry_date <= self.issue_date:
                raise Warning(_('Error, date of issue must be less than expiry date'))

            if date.today() >= self.expiry_date:
                raise Warning(_("Error,the expiry date must be greater than the date of the day"))

    saudi_id = fields.Char(string="Saudi ID")
    license_id = fields.Char(string="License ID")
    passport_id = fields.Char(string="Passport Number")
    iqama_id = fields.Char(string="Identity No")

    place_issue_id = fields.Char(string="Place of Issue")
    name = fields.Char(string="Document Name", required=True, copy=False)
    document_name = fields.Many2one(comodel_name="employee.checklist", string="Document")
    description = fields.Text(string="Description", copy=False)
    expiry_date = fields.Date(string="Expiry Date", tracking=True)
    employee_ref = fields.Many2one('hr.employee',copy=False, string="Employee Name")
    doc_attachment_id = fields.Many2many(
        "ir.attachment",
        "doc_attach_rel",
        "doc_id",
        "attach_id3",
        string="Attachment",
        help="You can attach the copy of your document",
        copy=False)
    file_examination = fields.Char()
    document_type = fields.Selection([
            ("passport", _("Passport")),
            ("license", _("License")),
            ("Iqama", _("Identity")),
            ("saudi", _("Saudi ID")),
            ("medical_Examination", _("medical Examination")),
            ("professional_certificates", _("Professional Certificates")),
            ("other", _("Other"))])
    issue_date = fields.Date(string="Issue Date", default=fields.datetime.now(), copy=False, tracking=True)
    reminder_before = fields.Integer(default=0)
    job_id = fields.Many2one("hr.job", "Job Position")

    emp_iqama_job = fields.Char("Job Position")

    membership_type = fields.Many2one(comodel_name="membership.types", string="Membership Type")
    specialization = fields.Char(string="Specialization")
    category = fields.Many2one(comodel_name="membership.categorys",string="Category")

    company_id = fields.Many2one('res.company',string="Company", default=lambda self: self.env.user.company_id)

    employee_number = fields.Char(related="employee_ref.contract_id.name", copy=False, string='Employee Number')


    def set_last_document(self):
        self.ensure_one()
        emp_id = self.env["hr.employee"].search([("id", "=", self.employee_ref.id)])
        if emp_id:
            if self.document_type == "passport":
                emp_id.passport_id = self.id
            elif self.document_type == "Iqama":
                emp_id.iqama_number = self.id
            elif self.document_type == "saudi":
                emp_id.saudi_number = self.id
            elif self.document_type == "license":
                emp_id.license_number_id = self.id
            elif self.document_type == "medical_Examination":
                emp_id.copy_examination_file = self.id

    @api.model
    def create(self, vals):
        res = super(HrEmployeeDocument, self).create(vals)
        res.set_last_document()
        return res


    def name_get(self):
        result = []
        for rec in self:
            if rec.saudi_id:
                result.append((rec.id, "" + rec.saudi_id))
            if rec.passport_id:
                result.append((rec.id, "" + rec.passport_id))
            if rec.iqama_id:
                result.append((rec.id,""+ rec.iqama_id))
            if rec.license_id:
                result.append((rec.id, "" + rec.license_id))
            if rec.file_examination:
                result.append((rec.id, "" + rec.file_examination))
            if rec.document_type == "other":
                result.append((rec.id, rec.name))
        return result

    @api.constrains( "passport_id", "saudi_id", "iqama_id", "license_id", "file_examination")
    def unique_fields(self):
        for item in self:
            if item.document_type == "passport":
                passport_num = self.search([("passport_id", "=", item.passport_id),("document_type", "=", item.document_type)])
                if len(passport_num) > 1:
                    raise Warning(_("This Passport Number already Exiting"))

            if item.document_type == "saudi":
                saudi_num = self.search([("saudi_id", "=", item.saudi_id),("document_type", "=", item.document_type)])
                if len(saudi_num) > 1:
                    raise Warning(_("This Saudi Identity already Exiting"))

            if item.document_type == "Iqama":
                iqama_num = self.search( [("iqama_id", "=", item.iqama_id),("document_type", "=", item.document_type)])
                if len(iqama_num) > 1:
                    raise Warning(_("This Identity Number already Exiting"))

            if item.document_type == "license":
                license_num = self.search(
                    [("license_id", "=", item.license_id),("document_type", "=", item.document_type)])
                if len(license_num) > 1:
                    raise Warning(_("This License Number already Exiting"))

            if item.document_type == "medical_Examination":
                medical_num = self.search(
                    [("file_examination", "=", item.file_examination),("document_type", "=", item.document_type)])
                if len(medical_num) > 1:
                    raise Warning(_("This Medical Examination Number already Exiting"))


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    passport_id = fields.Many2one(
        "hr.employee.document",
        domain=[("document_type", "=", "passport")],
        tracking=True,
    )
    expiry_license = fields.Date(
        related="license_number_id.expiry_date",
        readonly=True,
        default=fields.date.today(),
        string="License Expiry Date"
    )
    document_count = fields.Integer(compute="_document_count", string="# Documents")

    # Relational fields
    license_number_id = fields.Many2one(
        comodel_name="hr.employee.document", domain="[('document_type','=','license')]"
    )

    def _document_count(self):
        for each in self:
            document_ids = self.env["hr.employee.document"].search([("employee_ref", "=", each.id)])
            each.document_count = len(document_ids)

    def document_view(self):
        self.ensure_one()
        domain = [("employee_ref", "=", self.id)]
        return {
            "name": _("Documents"),
            "domain": domain,
            "res_model": "hr.employee.document",
            "type": "ir.actions.act_window",
            "view_id": False,
            "view_mode": "tree,form",
            "view_type": "form",
            "help": _(
                """<p class="oe_view_nocontent_create">
                           Click to Create for New Documents
                        </p>"""
            ),
            "limit": 80,
            "context": "{'default_employee_ref': '%s'}" % self.id,
        }


class HrEmployeeAttachment(models.Model):
    _inherit = "ir.attachment"

    doc_attach_rel = fields.Many2many("hr.employee.document","doc_attachment_id","attach_id3","doc_id",
        string="Attachment",invisible=1 )


class User(models.Model):
    _inherit = ["res.users"]

    passport_id = fields.Many2one(
        "hr.employee.document",
        related="employee_id.passport_id",
        readonly=False,
        related_sudo=False,
    )


class membership_types(models.Model):
    _name = 'membership.types'
    name = fields.Char()

class membership_categorys(models.Model):
    _name = 'membership.categorys'
    name = fields.Char()

