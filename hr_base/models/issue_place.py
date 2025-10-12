# -*- coding: utf-8 -*-
from odoo import fields, models


# issue_place
class IssuePlace(models.Model):
    _name = "issued_place.issued_place"
    _description = "Issued place"
    _rec_name = "name"

    name = fields.Char()
