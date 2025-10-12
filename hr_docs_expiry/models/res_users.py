# -*- coding: utf-8 -*-

from odoo import fields, models


class User(models.Model):
    _inherit = ["res.users"]

    passport_id = fields.Many2one(
        "hr.employee.document",
        related="employee_id.passport_id",
        readonly=False,
        related_sudo=False,
    )
