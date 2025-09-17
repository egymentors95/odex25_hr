# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class DegreeMedical(models.Model):
    _name = "degree.medical.issuance"
    _description = "Medical Insurance Degree"

    # degree_medical_insurance
    name = fields.Char(translate=True)
    company_insurance = fields.Char()


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    # passport fields to private information page
    date_issuance_passport = fields.Date(string="Passport Issue Date")
    expiration_date_passport = fields.Date(string="Passport Expiry Date")
    place_issuance_passport = fields.Char()
    own_license = fields.Boolean()

    # Accommodation and medical insurance page
    ###Residence
    residency_number = fields.Char(string="Insurances Number")
    #date_issuance_residence = fields.Date()
    expiration_date_residence = fields.Date()
    place_issuance_residence = fields.Char()
    first_entry_into_saudi_arabia = fields.Date()
    number_of_visa = fields.Integer()
    ###Guaranty
    on_company_guarantee = fields.Boolean(default=True)
    validity_transfer_sponsorship = fields.Date()
    ###Medical Insurance
    medical_insurance = fields.Boolean(default=True)
    degree_medical_insurance = fields.Many2one('degree.medical.issuance')
    medical_insurance_number = fields.Char()
    date_of_expiry = fields.Date(related='copy_examination_file.expiry_date', readonly=True)
    copy_examination_file = fields.Many2one('hr.employee.document',
                                            domain=[('document_type', '=', 'medical_Examination')])
    filename = fields.Char()

    # Payment method
    payment_method = fields.Selection(selection=[("cash", _("Cash")), ("bank", _("Bank"))])
    date_of_employment = fields.Date()
    length_of_service = fields.Integer()



    @api.onchange('country_id','saudi_number','iqama_number')
    def _get_medical_insurance_number(self):
        for item in self:
            if item.country_id.code == "SA":
                item.medical_insurance_number = item.saudi_number.saudi_id
            else:
                item.medical_insurance_number = item.iqama_number.iqama_id




