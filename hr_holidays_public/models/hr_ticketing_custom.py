# -*- coding: utf-8 -*-
from datetime import datetime
from odoo import models, fields, api, exceptions, _


class HRTICKETCUSTOM(models.Model):
    _inherit = 'hr.ticket.request'

    vacation_start_date = fields.Datetime(string='Vacation Start Date', related='leave_request_id.date_from')
    vacation_end_date = fields.Datetime(string='Vacation End Date', related='leave_request_id.date_to')
    vacation_duration = fields.Float(string='Vacation Duration', compute="_get_vacation_no")

    # Relational fields
    leave_request_id = fields.Many2one('hr.holidays', store=True)

    # one tiket holiday for each holiday request

    @api.constrains('leave_request_id')
    def ticket_holiday_request(self):
        for rec in self:
            holiday_req = self.env['hr.ticket.request'].search([('employee_id', '=', rec.employee_id.id),
                                                                ('leave_request_id', '=', rec.leave_request_id.id)])
            if len(holiday_req) > 1 and rec.leave_request_id:
                raise exceptions.Warning(_('This Holiday Request Has Been take Ticket %s')
                                         % rec.leave_request_id.display_name)

    # Dynamic domain on leave request Git only leaves for selected employee

    @api.onchange('request_type', 'employee_id', 'mission_check')
    def _get_leave_request_domain(self):
        leaves_ids = self.env['hr.holidays'].search([('employee_id', '=', self.employee_id.id)]).ids
        return {'domain': {'leave_request_id': [('id', 'in', leaves_ids), ('state', '=', 'validate1'),
                                                ('type', '=', 'remove'), ('issuing_ticket', '=', 'yes')]}}

    @api.depends('vacation_start_date', 'vacation_end_date')
    def _get_vacation_no(self):
        for vacation in self:
            vacation.vacation_duration = 0
            if vacation.vacation_start_date and vacation.vacation_end_date:
                start_vacation_date = datetime.strptime(str(vacation.vacation_start_date), "%Y-%m-%d %H:%M:%S")
                end_vacation_date = datetime.strptime(str(vacation.vacation_end_date), "%Y-%m-%d %H:%M:%S")
                if start_vacation_date < end_vacation_date:

                    days = (end_vacation_date - start_vacation_date).days
                    # relative_months_mission = relativedelta.relativedelta(start_mission_date, end_mission_date).months
                    vacation.vacation_duration = days + 1

                else:
                    vacation.vacation_duration = 0.0
                    raise exceptions.Warning(_('End vacation Date must be greater than Start vacation Date'))
