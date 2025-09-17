from odoo import models, fields, api, _


class ModelConfiguration(models.Model):
    _name = 'model.configuration'

    name = fields.Char('Name')
    model_id = fields.Many2one('ir.model', string='Model Ref.')
