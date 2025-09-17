# -*- coding: utf-8 -*-

from odoo import models, fields, api


class HrClearanceFormCustom(models.Model):
    _inherit = 'hr.clearance.form'

    leave_request_id = fields.Many2one(comodel_name='hr.holidays', domain=[('id', 'in', [])])
    start_of_vacation = fields.Datetime(related='leave_request_id.date_from')
    end_of_vacation = fields.Datetime(related='leave_request_id.date_to')

    @api.onchange('employee_id')
    def _get_holidays_id(self):

        for item in self:
            item.leave_request_id = False
            holiday_ids = self.env['hr.holidays'].search(
                [('employee_id', '=', item.employee_id.id), ('state', '=', 'validate1'),
                 ('holiday_status_id.issuing_clearance_form', '=', 'True'), ('type', '=', 'remove')]).ids

            if holiday_ids:
                return {'domain': {'leave_request_id': [('id', 'in', holiday_ids)]}}
            else:
                return {'domain': {'leave_request_id': [('id', 'in', [])]}}
