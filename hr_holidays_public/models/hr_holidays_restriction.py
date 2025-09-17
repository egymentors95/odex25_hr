# -*- coding: utf-8 -*-

from odoo import models, fields, api, _, exceptions


class HrHolidaysRestriction(models.Model):
    _name = 'hr.holidays.restriction'
    _rec_name = 'date_from'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    date_from = fields.Date('Date From', required=True, default=fields.Date.today())
    date_to = fields.Date('Date To', required=True)
    leave_ids = fields.Many2many(comodel_name='hr.holidays.status', string='Leaves')
    employee_ids = fields.Many2many(comodel_name='hr.employee', string='Employees')


class HRHolidays(models.Model):
    _inherit = 'hr.holidays'

    @api.constrains('holiday_status_id', 'employee_id', 'date_from', 'date_to')
    def check_leave_restriction(self):
        restricted_leaves = self.env['hr.holidays.restriction']
        for leave in self:
            if leave.holiday_status_id and leave.date_from and leave.date_to:
                restricted = restricted_leaves.search([('date_from', '<=', leave.date_to),
                                                       ('date_to', '>=', leave.date_from)
                                                       ])
                if leave.employee_id in restricted.mapped('employee_ids') and \
                        leave.holiday_status_id in restricted.mapped('leave_ids'):
                    msg = ''
                    for r in restricted: msg += str(r.date_from) + ' - ' + str(r.date_to) + '\n'
                    raise exceptions.ValidationError(_('Sorry you are restricted from applying for %s durring '
                                                       'the following periods \n %s') % (
                                                     leave.holiday_status_id.name, msg))
