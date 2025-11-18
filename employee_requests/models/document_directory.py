# -*- coding: utf-8 -*-
from odoo import models, fields


class DocumentDirectory(models.Model):
    _name = 'document.directory'
    _description = 'Document Directory'

    name = fields.Char(string='Directory')
