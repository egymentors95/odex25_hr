# -*- coding: utf-8 -*-

from odoo import models, fields, api


class PenaltyRegister(models.Model):
    _inherit = 'hr.penalty.register'

    deduction_days = fields.Float('Days to Deduct', help='Number of days not counted for candidacy for promotions')
    penalty_with_days = fields.Boolean('Days Deducted Penalties', default=False)

    @api.onchange('punishment_id')
    def onchange_punishments(self):
        for p in self.punishment_id:
            if p.days_deduction:
                self.penalty_with_days = True
                break
            else:
                self.penalty_with_days = False
