# -*- coding:utf-8 -*-

from odoo import models, fields, _, exceptions


class Employee_Amedment(models.Model):
    _name = 'hr.deduction'
    _rec_name = 'employee_id'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char()
    bank_loan = fields.Boolean()
    loan_number = fields.Char()
    bank_branch = fields.Char()
    employee_id = fields.Many2one(comodel_name='hr.employee')
    department_id = fields.Many2one(comodel_name='hr.department')
    job_id = fields.Many2one(comodel_name='hr.job')
    con_start = fields.Date()
    con_end = fields.Date()

    # hijri date will be added
    con_start_hijri = fields.Date()
    con_end_hijri = fields.Date()

    amount = fields.Float()
    months = fields.Integer()
    total_paid_installment = fields.Float()
    remaining_loan_amount = fields.Float()

    start_date = fields.Date()
    # deductions_line = fields.One2many('employee.deduction.line' , inverse='deductions_lines')
    deductions_line = fields.Char()
    note = fields.Text()

    state = fields.Selection(selection=[
        ('draft', 'Draft'),
        ('submit', 'Submit'),
        ('manager', 'HR Manager'),
        ('gm', 'GM'),
        ('refuse', 'Refuse'),
        ('done', 'Done'),
    ], default='draft')

    next_state = fields.Selection(selection=[
        ("draft", "Draft"),
        ("submit", "Submit"),
        ("manager", "HR Manager"),
        ("gm", "GM"),
        ("refuse", "Refuse"),
        ("done", "Done"),
    ], default='draft')

    def submit(self):
        self.state = 'submit'

    def unlink(self):
        for i in self:
            if i.state != 'draft':
                raise exceptions.Warning(_('You can not delete record in state not in draft'))
        return super(Employee_Amedment, self).unlink()
