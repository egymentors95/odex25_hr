##############################################################################
#
#    LCT, Life Connection Technology
#    Copyright (C) 2011-2012 LCT
#
##############################################################################

from odoo import fields, models


class ResourceResource(models.Model):
    _inherit = "resource.resource"

    name = fields.Char(required=True, translate=True)
