# -*- coding: utf-8 -*-

from odoo import fields, models


class CategoryInfo(models.Model):
    _name = "category.info"
    _description = "Category Info"
    _rec_name = "category"

    company_name = fields.Many2one(comodel_name="res.company", string="Company Name", required=True)
    branch_name = fields.Many2one(comodel_name="res.company", string="Branch Name")
    division = fields.Many2one(comodel_name="division.info", string="Division")
    department = fields.Many2one(comodel_name="department.info", string="Department")
    category = fields.Char("Category Info")
