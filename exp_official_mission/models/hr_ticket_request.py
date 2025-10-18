from odoo import models, fields, api


class HrTicketRequest(models.Model):
    _inherit = 'hr.ticket.request'

    account_ids = fields.One2many('hr.mission.type.account', 'ticket_id')
    transfer_by_emp_type = fields.Boolean('Transfer By Emp Type')
    account_id = fields.Many2one('account.account')
    analytic_account_id = fields.Many2one(comodel_name='account.analytic.account')


