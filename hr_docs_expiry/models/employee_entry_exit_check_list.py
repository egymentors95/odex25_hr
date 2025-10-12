# -*- coding: utf-8 -*-

from odoo import fields, models


class EmployeeEntryDocuments(models.Model):
    _name = "employee.checklist"
    _inherit = "mail.thread"
    _description = "Employee Documents"

    name = fields.Char(string="Document Name", copy=False, required=1)
    document_type = fields.Selection(selection=[("entry", "Entry Process"), ("exit", "Exit Process"),
                                                ("other", "Other")], string="Checklist Type", required=1)

    def name_get(self):
        result = []
        for each in self:
            name = ""
            if each.document_type == "entry":
                name = each.name + "_en"
            elif each.document_type == "exit":
                name = each.name + "_ex"
            elif each.document_type == "other":
                name = each.name + "_ot"
            result.append((each.id, name))
        return result
