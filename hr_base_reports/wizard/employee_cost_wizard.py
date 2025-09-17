## -*- coding: utf-8 -*-
##############################################################################
#
#    Expert
#    Copyright (C) 2020-2021 Expert(Sudan Team A)
#
##############################################################################
from datetime import date
from dateutil.relativedelta import relativedelta
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class EmployeeCostReport(models.TransientModel):
    _name = 'employee.cost.report'
    _description = "Department Cost Report"

    date_from = fields.Date(string='Date From',
                            default=lambda self: date(date.today().year, date.today().month, 1))
    date_to = fields.Date(string='Date To',
                          default=lambda self: date(date.today().year, date.today().month, 1))
    employee_ids = fields.Many2many('hr.employee', string='Employees')
    department_ids = fields.Many2many('hr.department', string='Department')
    mission_type = fields.Many2one('hr.official.mission.type', string="Type")
    old = fields.Boolean(string="Show Old")
    request_type_id = fields.Many2one('loan.request.type')
    report_type = fields.Selection([
        ('employee_cost', 'Employee Cost'),
        ('general', 'General'),
        ('overtime', 'Overtime'),
        ('handover', 'Hand Over'),
        ('mission', 'Mission'),
        ('training', 'Training'),
        ('attendance', 'Attendance'),
        ('saudi', 'Saudi'),
        ('loan', 'Loan'),
        ('appraisal', 'Appraisal'),
        ('iqama', 'Identity'),
        ('re_entry', 'Re-Entry'),
        ('absence', 'Absence'),
        ('promotion', 'Promotion'),
        ('executions', 'Execution'),
    ])

    @api.onchange('department_ids')
    def get_department_employee(self):
        if self.department_ids:
            emps = self.department_ids.mapped('employee_ids').ids
            domain = [('id', 'in', emps)]
            if self.report_type != 'handover':
                domain += [('state', '=', 'open')]
            return {'domain': {'employee_ids': domain}}
        else:
            domain = [('id', 'in', False)]
            if self.report_type != 'handover':
                domain += [('state', '=', 'open')]
            return {'domain': {'employee_ids': domain}}

    def check_data(self):
        if self.date_from and not self.date_to or not self.date_from and self.date_to:
            raise UserError(_('Choose Date From and Date To'))
        if self.date_from and self.date_to and self.date_from > self.date_to:
            raise UserError(_('Date From must be less than or equal Date To'))
        return {'form': (self.read()[0]), }

    def print_report(self):
        datas = self.check_data()
        if self.report_type == 'employee_cost':
            return self.env.ref('hr_base_reports.employee_cost_report_act').report_action(self, data=datas)
        elif self.report_type == 'overtime':
            return self.env.ref('hr_base_reports.employee_overtime_report_act').report_action(self, data=datas)
        elif self.report_type == 'general':
            return self.env.ref('hr_base_reports.employee_general_report_act').report_action(self, data=datas)
        elif self.report_type == 'handover':
            return self.env.ref('hr_base_reports.employee_handover_report_act').report_action(self, data=datas)
        elif self.report_type == 'mission':
            return self.env.ref('hr_base_reports.employee_mission_report_act').report_action(self, data=datas)
        elif self.report_type == 'training':
            return self.env.ref('hr_base_reports.employee_training_report_act').report_action(self, data=datas)
        elif self.report_type == 'attendance':
            return self.env.ref('hr_base_reports.employee_attendance_report_act').report_action(self, data=datas)
        elif self.report_type == 'saudi':
            return self.env.ref('hr_base_reports.employee_saudi_report_act').report_action(self, data=datas)
        elif self.report_type == 'loan':
            return self.env.ref('hr_base_reports.employee_loan_report_act').report_action(self, data=datas)
        elif self.report_type == 'appraisal':
            return self.env.ref('hr_base_reports.employee_appraisal_report_act').report_action(self, data=datas)
        elif self.report_type == 'iqama':
            return self.env.ref('hr_base_reports.employee_iqama_report_act').report_action(self, data=datas)
        elif self.report_type == 'absence':
            return self.env.ref('hr_base_reports.employee_absence_report_act').report_action(self, data=datas)
        elif self.report_type == 'promotion':
            return self.env.ref('hr_base_reports.employee_promotion_report_act').report_action(self, data=datas)
        elif self.report_type == 'executions':
            return self.env.ref('hr_base_reports.employee_executions_report_act').report_action(self, data=datas)
        elif self.report_type == 're_entry':
            return self.env.ref('hr_base_reports.employee_re_entry_report_act').report_action(self, data=datas)

    def print_report_xlsx(self):
        datas = self.check_data()
        if self.report_type == 'employee_cost':
            return self.env.ref('hr_base_reports.employee_cost_report_act_xlsx').report_action(self, data=datas)
        elif self.report_type == 'overtime':
            return self.env.ref('hr_base_reports.employee_overtime_report_act_xlsx').report_action(self, data=datas)
        elif self.report_type == 'general':
            return self.env.ref('hr_base_reports.employee_general_report_act_xlsx').report_action(self, data=datas)
        elif self.report_type == 'handover':
            return self.env.ref('hr_base_reports.employee_handover_report_act_xlsx').report_action(self, data=datas)
        elif self.report_type == 'mission':
            return self.env.ref('hr_base_reports.employee_mission_report_act_xlsx').report_action(self, data=datas)
        elif self.report_type == 'training':
            return self.env.ref('hr_base_reports.employee_training_report_act_xlsx').report_action(self, data=datas)
        elif self.report_type == 'attendance':
            return self.env.ref('hr_base_reports.employee_attendance_report_act_xlsx').report_action(self, data=datas)
        elif self.report_type == 'saudi':
            return self.env.ref('hr_base_reports.employee_saudi_report_act_xlsx').report_action(self, data=datas)
        elif self.report_type == 'loan':
            return self.env.ref('hr_base_reports.employee_loan_report_act_xlsx').report_action(self, data=datas)
        elif self.report_type == 'appraisal':
            return self.env.ref('hr_base_reports.employee_appraisal_report_act_xlsx').report_action(self, data=datas)
        elif self.report_type == 'iqama':
            return self.env.ref('hr_base_reports.employee_iqama_report_act_xlsx').report_action(self, data=datas)
        elif self.report_type == 'absence':
            return self.env.ref('hr_base_reports.employee_absence_report_act_xlsx').report_action(self, data=datas)
        elif self.report_type == 'promotion':
            return self.env.ref('hr_base_reports.employee_promotion_report_act_xlsx').report_action(self, data=datas)
        elif self.report_type == 'executions':
            return self.env.ref('hr_base_reports.employee_executions_report_act_xlsx').report_action(self, data=datas)
        elif self.report_type == 're_entry':
            return self.env.ref('hr_base_reports.employee_re_entry_report_act_xlsx').report_action(self, data=datas)
