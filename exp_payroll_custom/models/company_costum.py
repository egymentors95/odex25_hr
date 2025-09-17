from odoo import api, fields, models


class CompanyCustom(models.Model):
    _inherit = 'res.company'

    company_hr_no = fields.Char(string="Number Of Company For HR")
    company_pay_no = fields.Char(string="Company Pay Number")
