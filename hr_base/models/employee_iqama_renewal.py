# -*- coding: utf-8 -*-

from datetime import datetime as dt

from odoo import _, api, exceptions, fields, models


class EmployeeIqamaRenew(models.Model):
    _name = "employee.iqama.renewal"
    _description = "Employee Iqama Renewal"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char(readonly=True)
    date = fields.Date()
    line_ids = fields.One2many("employee.iqama.renewal.line", "line_id")
    x_description = fields.Char()
    state = fields.Selection(
        [('draft', _('Draft')), ('submit', _('Submit')), ('hr_depart', _('HR Department')),
         ('effective_department', _('Effective_Department')),
         ('chief_accountant', _('Transferred')), ('refused', _('Refused'))],
        default="draft",
        tracking=True,
    )

    @api.model
    def create(self, vals):
        employee_id = self.env["hr.employee"].search(
            [("user_id", "=", self.env.uid)], limit=1
        )
        seq = self.env["ir.sequence"].get("employee.iqama.renewal")
        vals["name"] = seq + "/" + employee_id.name
        return super(EmployeeIqamaRenew, self).create(vals)

    def draft_state(self):
        for item in self:
            for record in item.line_ids:
                if record.state == 'chief_accountant':
                    if record.move_id:
                        if record.move_id.state == 'draft':
                            # record.move_id.state ='canceled'
                            record.move_id.unlink()
                            record.state = "draft"
                            record.employee_id.iqama_number.write({
                                'expiry_date': record.iqama_expir_date})
                        else:
                            raise exceptions.Warning(
                                _('You can not cancel account move "%s" in state not draft') % record.move_id.name)
                    if record.move_id2:
                        if record.move_id2.state == 'draft':
                            # record.move_id2.state ='canceled'
                            record.move_id2.unlink()
                            record.state = "draft"
                            record.employee_id.iqama_number.write({
                                'expiry_date': record.iqama_expir_date
                            })
                        else:
                            raise exceptions.Warning(
                                _('You can not cancel account move "%s" in state not draft') % record.move_id.name)
                    item.state = "draft"
                else:
                    item.state = 'draft'
                    record.state = "draft"

    def submit(self):
        for item in self:
            for record in item.line_ids:
                if not record.iqama_new_expiry:
                    raise exceptions.Warning(_("Sorry You must enter New Iqama expiry"))
                item.state = "submit"
                record.state = "submit"

    def hr_depart(self):
        for item in self:
            for record in item.line_ids:
                item.state = "hr_depart"
                record.state = "hr_depart"

    def effective_department(self):
        for item in self:
            for record in item.line_ids:
                item.state = "effective_department"
                record.state = "effective_department"

    def chief_accountant(self):
        for item in self:
            for record in item.sudo().line_ids:
                if record.state == "effective_department":
                    if not record.account_id.id or not record.journal_id.id:
                        raise exceptions.Warning(
                            _(
                                "To Transfer the entry you must enter the account and journal"
                            )
                        )

                    # journal renewal_fees
                    debit_line_vals = {
                        "name": record.employee_id.name,
                        "debit": record.renewal_fees,
                        "account_id": record.account_id.id,
                        "partner_id": record.employee_id.user_id.partner_id.id,
                    }
                    credit_line_vals = {
                        "name": record.employee_id.name,
                        "credit": record.renewal_fees,
                        "account_id": record.journal_id.default_account_id.id,
                        "partner_id": record.employee_id.user_id.partner_id.id,
                    }

                    move = record.env["account.move"].create(
                        {
                            "state": "draft",
                            "journal_id": record.journal_id.id,
                            "date": item.date,
                            "ref": record.employee_id.name,
                            "line_ids": [
                                (0, 0, debit_line_vals),
                                (0, 0, credit_line_vals),
                            ],
                        }
                    )

                    record.move_id = move.id

                    # journal work_premint_fees
                    debit_line_vals = {
                        "name": record.employee_id.name,
                        "debit": record.work_premint_fees,
                        "account_id": record.account_id2.id,
                        "partner_id": record.employee_id.user_id.partner_id.id,
                    }
                    credit_line_vals = {
                        "name": record.employee_id.name,
                        "credit": record.work_premint_fees,
                        "account_id": record.journal_id.default_account_id.id,
                        "partner_id": record.employee_id.user_id.partner_id.id,
                    }

                    move = record.env["account.move"].create(
                        {
                            "state": "draft",
                            "journal_id": record.journal_id.id,
                            "date": item.date,
                            "ref": record.employee_id.name,
                            "line_ids": [
                                (0, 0, debit_line_vals),
                                (0, 0, credit_line_vals),
                            ],
                        }
                    )
                    record.move_id2 = move.id

                    record.sudo().employee_id.iqama_number.write(
                        {"expiry_date": record.iqama_new_expiry}
                    )

                record.state = "chief_accountant"
            item.state = "chief_accountant"

    def refused(self):
        for item in self:
            for record in item.line_ids:
                item.state = "refused"
                record.state = "refused"

    def unlink(self):
        for i in self:
            if i.state != "draft":
                raise exceptions.Warning(
                    _("You can not delete record in state not in draft")
                )
        return super(EmployeeIqamaRenew, self).unlink()

    def b_search(self):
        emp_obj = self.sudo().env["hr.employee"].search(
            [("iqama_expiy_date", "<=", self.date), ("state", "=", "open")]
        )

        self.line_ids.unlink()
        vals = []
        for emp in emp_obj:
            #vals.append((0, False, {"employee_id": emp.id}))
            vals.append((0, False, {"employee_id": emp.id,"iqama_expir_date":emp.iqama_expiy_date}))

        self.write({"line_ids": vals})


class EmployeeIqamaRenewLine(models.Model):
    _name = "employee.iqama.renewal.line"
    _description = "Employee Iqama Renewal Line"

    document_id = fields.Many2one("hr.employee.document", domain=[("document_type", "=", "Iqama")])
    employee_id = fields.Many2one(comodel_name="hr.employee", required=True)
    iqama_no = fields.Many2one(related="employee_id.iqama_number", readonly=True)
    iqama_expir_date = fields.Date(compute='_get_iqama_expiry', store=True, readonly=True)
    work_premit_sedad_no = fields.Char()
    renewal_fees = fields.Float(required=True, default=0)
    work_premint_fees = fields.Float(required=True, default=0)
    total = fields.Float(readonly=True, compute="get_total_fees")
    line_id = fields.Many2one(comodel_name="employee.iqama.renewal")
    iqama_new_expiry = fields.Date()
    account_id = fields.Many2one("account.account")
    account_id2 = fields.Many2one("account.account")
    journal_id = fields.Many2one("account.journal")
    move_id = fields.Many2one("account.move", string="Move Renewal")
    move_id2 = fields.Many2one("account.move", string="Move Work")
    contract_date_end = fields.Date(related="employee_id.contract_id.date_end", readonly=True)
    state = fields.Selection(
        [
            ("draft", _("Draft")),
            ("submit", _("Submit")),
            ("hr_depart", _("HR Department")),
            ("effective_department", _("Effective_Department")),
            ("chief_accountant", _("Chief Accountant")),
            ("refused", _("Refused")),
        ],
        default="draft",
        readonly=True,
    )

    @api.depends("employee_id")
    def _get_iqama_expiry(self):
        for item in self:
            item.iqama_expir_date = item.employee_id.iqama_expiy_date

    @api.depends("work_premint_fees", "renewal_fees")
    def get_total_fees(self):
        for rec in self:
            rec.total = rec.renewal_fees + rec.work_premint_fees

    @api.onchange("iqama_expir_date", "iqama_new_expiry")
    def onchange_dates(self):
        if self.iqama_new_expiry:
            if self.iqama_expir_date:
                expiry_date_1 = dt.strptime(str(self.iqama_expir_date), "%Y-%m-%d")
                new_expiry_date_1 = dt.strptime(str(self.iqama_new_expiry), "%Y-%m-%d")
                if expiry_date_1 > new_expiry_date_1:
                    raise exceptions.Warning(
                        _("New Identity Expiry Date  must be greater than old expiry Date")
                    )

    def unlink(self):
        for i in self:
            if i.state != 'draft':
                raise exceptions.Warning(_('You can not delete record in state not in draft'))
            # i.line_ids.unlink()
        return super(EmployeeIqamaRenewLine, self).unlink()
