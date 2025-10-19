from odoo import models, fields


class ResPartnerBank(models.Model):
    _inherit = 'res.partner.bank'

    employee_id = fields.Many2one(comodel_name='hr.employee', string="اسم مالك الحساب")
    default_number = fields.Boolean(string="الافتراضي")
    partner_id = fields.Many2one('res.partner', 'Account Holder', ondelete='cascade', index=True, domain=['|', ('is_company', '=', True), ('parent_id', '=', False)], required=False)


