from odoo import api, fields, models
from lxml import etree


class ResPartner(models.Model):
    _inherit = 'res.partner'

    signup_token = fields.Char(copy=False,groups=False)
    signup_type = fields.Char(string='Signup Token Type', copy=False, groups=False)
    signup_expiration = fields.Datetime(copy=False, groups=False)

