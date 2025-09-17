# -*- coding: utf-8 -*-

from odoo import fields, models, _, api
from odoo.exceptions import ValidationError


class HrHolidaysStatus(models.Model):
    _inherit = 'hr.holidays.status'

    double_validation = fields.Boolean()
    workflow_ids = fields.One2many('workflow.stage', 'holiday_status_id', string="Workflow")

    @api.constrains('double_validation')
    def check_workflow(self):
        for rec in self:
            if rec.double_validation and not rec.workflow_ids:
                raise ValidationError(_("Enter workflow stage first"))

    @api.constrains('workflow_ids')
    def check_workflow_state(self):
        for rec in self:
            for work in rec.workflow_ids:
                records = rec.workflow_ids.filtered(lambda r: r.id != work.id and r.state != 'approved'
                                                    and r.state == work.state)
                if records:
                    raise ValidationError(_("You can duplicate only workflow state"))
            missing_stage = rec.workflow_ids.filtered(lambda r: r.state != 'approved')
            if len(missing_stage) < 5:
                raise ValidationError(_("Enter missing default stage"))

    def update_holiday(self):
        holidays = self.env['hr.holidays'].search(
            [('double_validation', '=', True), ('holiday_status_id', '=', self.id),
             ('type', '=', 'remove')])
        for holiday in holidays:
            if holiday.workflow_ids and holiday.stage_id.state == 'approved' and holiday.state == 'validate':
                holiday.get_workflow_data()
                holiday.check_state = False
                approve = holiday.workflow_ids.sudo().filtered(
                    lambda r: r.stage_id.state == 'approved' and not r.approved)
                if approve:
                    holiday.btn_string = approve[0].btn_string
                    holiday.stage_id = approve[0].stage_id.id
            elif holiday.workflow_ids and holiday.stage_id.state == 'approved' and holiday.state == 'approved':
                holiday.get_workflow_data()
                approve = holiday.workflow_ids.sudo().filtered(
                    lambda r: r.stage_id.state == 'approved' and not r.approved)
                stage = len(approve) - 1
                holiday.stage_id = approve[stage].stage_id.id
                holiday.check_state = True
                holiday.btn_string = ""
            else:
                holiday.get_workflow_data()
                holiday.change_state()
