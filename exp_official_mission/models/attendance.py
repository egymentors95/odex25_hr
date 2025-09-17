from odoo import models, fields, api, exceptions


class AttendanceTransactions(models.Model):
    _inherit = 'hr.attendance.transaction'

    is_official = fields.Boolean(string='Mission')
    official_id = fields.Many2one('hr.official.mission', string='Mission Request')
    total_mission_hours = fields.Float()
    mission_name = fields.Many2one(related='official_id.mission_type', string='Mission Type', store=True)



class ResPartner(models.Model):
    _inherit = 'res.partner'

    training = fields.Boolean(string="Training",default=False)
