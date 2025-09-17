# -*- coding: utf-8 -*-

from odoo import models, fields, api


class HrOfficialMissionType(models.Model):
    _inherit = 'hr.official.mission.type'
    pr_product_id = fields.Many2one(comodel_name='product.product', string="PR Product")

