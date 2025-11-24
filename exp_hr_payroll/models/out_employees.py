from odoo import models, fields, api


class OutEmployees(models.Model):
    _name = 'out.employees'
    _description = 'Out Employees'
    _rec_name = 'employee_id'

    hr_payslip_run_id = fields.Many2one(
        'hr.payslip.run',
        string='Payslip Run',
        ondelete='cascade'
    )
    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee',
    )