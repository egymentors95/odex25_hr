# -*- coding: utf-8 -*-

from odoo import models, fields, api, _, exceptions


class HRHolidaysCustom(models.Model):
    _inherit = 'hr.employee'

    remaining_leaves = fields.Float(compute='_gte_balance_employee')
    leaves_count = fields.Float(compute='_gte_balance_employee')
    leave_line = fields.One2many(comodel_name='hr.holidays', inverse_name='employee_id',
                                 domain=[('type', '=', 'remove'), ('state', '=', 'validate1')])
    # leave_request_id = fields.Many2one('hr.holidays', string='Leave Request')
    # leave_type = fields.Many2one('hr.holidays.status', string='Leave Type',
    #                              related='leave_request_id.holiday_status_id', readonly=True)
    current_leave_state = fields.Selection(selection_add=[('approved', 'Workflow'), ('refused', 'Refused')])

    def _gte_balance_employee(self):
        for item in self:
            employee_balance = self.env['hr.holidays'].search(
                [('type', '=', 'add'), ('holiday_status_id.leave_type', '=', 'annual'),
                 ('employee_id', '=', item.id), ('check_allocation_view', '=', 'balance')],
                limit=1)
            item.remaining_leaves = employee_balance.remaining_leaves
            item.leaves_count = employee_balance.remaining_leaves

    # dynamic domain on leave_request_id , and constrain on employee if he is single
    # @api.onchange('employee_id')
    # def _get_leave_request_domain(self):
    #     self.leave_request_id = False
    #     record_id = self.env['hr.holidays'].search([('employee_id', '=', self.employee_id.id)])
    #     employee_leaves = []
    #     for item in record_id:
    #         employee_leaves.append(item.id)
    #     return {'domain': {'leave_request_id': [('id', 'in', employee_leaves), ('state', '=', 'validate1'),
    #                                             ('type', '=', 'remove')]}}
