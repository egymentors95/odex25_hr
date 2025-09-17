# -*- coding: utf-8 -*-

from datetime import datetime, date
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class HRPenaltyReport(models.TransientModel):

    _name = 'hr.penalty.report'
    _description = 'HR Penalty Report'

    employee_ids = fields.Many2many('hr.employee')
    date_from = fields.Date()
    date_to = fields.Date()
    penalty_ids = fields.Many2many('hr.penalty.ss')
    punishment_ids = fields.Many2many('hr.punishment')


    def action_print(self):
        employee_ids = self.employee_ids and self.employee_ids.ids or self.env['hr.employee'].search([]).ids
        data = {
            'employee_ids': employee_ids,
            'date_from': self.date_from,
            'date_to': self.date_to,
            'penalty_ids': self.penalty_ids.ids,
            'punishment_ids': self.punishment_ids.ids,
        }

        return self.env.ref('hr_base_reports.action_hr_penalty_report').report_action([], data=data)


class HRPenaltyReportView(models.AbstractModel):

    _name = 'report.hr_base_reports.hr_penalty_report'

    @api.model
    def _get_report_values(self, docids, data=None):
        report_values = []
        employee_ids = data['employee_ids']
        date_from = data['date_from']
        date_to = data['date_to']
        penalty_ids = data['penalty_ids']
        punishment_ids = data['punishment_ids']

        for employee_id in employee_ids:
            penalty_domain = [('start_date', '>=', date_from), ('end_date', '<=', date_to),
                              ('penalty_id', 'in', penalty_ids), ('punishment_id', 'in', punishment_ids),
                              ('employee_id', '=', employee_id)]
            emp_penalty_ids = self.env['hr.penalty.register'].search(penalty_domain)
            if emp_penalty_ids:
                report_values.append({'employee_id': self.env['hr.employee'].browse(employee_id),
                                      'penalties': emp_penalty_ids,})

        if len(report_values) == 0:
            raise ValidationError(_("There is no Data"))

        return {
            'print_date': datetime.now().date(),
            'user_name': self.env.user.name,
            'docs': report_values,
            'doc': self,
        }
