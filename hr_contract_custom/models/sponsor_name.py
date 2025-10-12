from odoo import models, fields, api


class SponsorName(models.Model):
    _name = 'sponsor.name'
    _description = 'Sponsor'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string="اسم الكفيل", tracking=True)
    sponsor_bank_number = fields.Integer(string="رقم حساب الكفيل في البنك", tracking=True)
    # computer_number = fields.Integer(string="رقم الحاسب الالي", tracking=True)
    computer_no = fields.Char(string="رقم الحاسب الالي", tracking=True)
    iban_number = fields.Char(string="رقم الايبان", tracking=True)
    labor_office_number = fields.Char(string="الرقم في مكتب العمل", tracking=True)
