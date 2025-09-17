# -*- coding: utf-8 -*-
from odoo import models, fields, api, _, exceptions
from odoo.exceptions import ValidationError


class HRHolidays(models.Model):
    _inherit = 'hr.exit.return'

    leave_request_id = fields.Many2one(comodel_name='hr.holidays', store=True)
    vacation_start_date = fields.Datetime(related='leave_request_id.date_from')
    vacation_end_date = fields.Datetime(related='leave_request_id.date_to')
    vacation_duration = fields.Float(related='leave_request_id.number_of_days_temp')

    # one Exit Return holiday for each holiday request

    @api.constrains('leave_request_id')
    def ticket_holiday_request(self):
        for rec in self:
            holiday_req = self.env['hr.exit.return'].search([('employee_id', '=', rec.employee_id.id),
                                                             ('leave_request_id', '=', rec.leave_request_id.id)])

            if len(holiday_req) > 1:
                raise exceptions.Warning(
                    _('This Holiday Request Has Been take Exit Return %s') % rec.leave_request_id.display_name)

    # dynamic domain on leave_request_id & constraint if the employee does not have family
    @api.onchange('request_for', 'employee_id')
    def check_request(self):
        self.leave_request_id = False
        if self.employee_id and self.request_for:
            #if self.employee_id.marital == 'single' and self.request_for in ['family', 'all']:
                #raise ValidationError('You are single, can not request ticket for family')

            if self.request_for in ['family', 'all']:
                dependant_list = []
                if self.contract_id.employee_dependant:
                    for item in self.contract_id.employee_dependant:
                        dependant_list.append(item.id)
                    self.employee_dependant = self.env['hr.employee.dependent'].browse(dependant_list)
        record_id = self.env['hr.holidays'].search([('employee_id', '=', self.employee_id.id)])
        employee_leaves = []
        for item in record_id:
            employee_leaves.append(item.id)

        return {'domain': {
            'leave_request_id': [('id', 'in', employee_leaves), ('state', '=', 'validate1'),
                                 ('type', '=', 'remove'), ('issuing_exit_return', '=', 'yes')]}}
