# -*- coding: utf-8 -*-
from odoo import fields, models


# office
class Office(models.Model):
    _name = "office.office"
    _description = "Office"
    _rec_name = "name"

    name = fields.Char()
