# -*- coding: utf-8 -*-

from odoo import fields, models


class FamilyIqama(models.Model):
    _name = "employee.family.iqama"
    _description = "Employee Family Iqama"
    _rec_name = "iqama_no"

    iqama_no = fields.Char("Identity/ID No", required=True)
    serial_no = fields.Char()
    iqama_position = fields.Char()
    place_issue = fields.Char("Place of Issue")
    issue_date = fields.Date()
    expiry_date = fields.Date(required=True)
    # date_hijri = fields.Char('Date of Expiry(Hijri)')
    arrival_date = fields.Date("Arrival Date in Suadi")
    in_saudi = fields.Boolean("Is Saudi?")
    link = fields.Many2one(comodel_name="employee.iqama")
