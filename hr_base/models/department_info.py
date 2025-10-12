# -*- coding: utf-8 -*-

from odoo import fields, models


class DepartmentInfo(models.Model):
    _name = "department.info"
    _description = "Department Info"
    _rec_name = "department"

    company_name = fields.Many2one(comodel_name="res.company", string="Company Name")
    branch_name = fields.Many2one(comodel_name="res.company", string="Branch Name")
    division = fields.Many2one(comodel_name="division.info", string="Division")
    department = fields.Char("Department", required=True)
    parent_dep = fields.Many2one(comodel_name="hr.department", string="Parent Department")
    manager = fields.Many2one(comodel_name="hr.employee", string="Manager", required=True)
