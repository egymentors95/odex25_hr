from odoo import models, fields


class ResPartnerBank(models.Model):
    _inherit = 'res.partner.bank'

    employee_id = fields.Many2one(comodel_name='hr.employee', string="Employee")
    default_number = fields.Boolean(string="الافتراضي")