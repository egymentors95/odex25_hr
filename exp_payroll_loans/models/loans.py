from odoo import models, fields, api, _, exceptions


class HrSalaryAdvance(models.Model):
    _inherit = 'hr.loan.salary.advance'

    monthly_salary = fields.Float(related='employee_id.contract_id.total_allowance')

    # Override percentage_constrain function
    # percentage constrain depending on the start date
    @api.constrains('date')
    def percentage_constrain(self):
        result = super(HrSalaryAdvance, self).percentage_constrain()
        return result


class LoanRequestTypes(models.Model):
    _inherit = 'loan.request.type'

    # Relational fields
    career_level_ids = fields.Many2many('hr.payroll.structure', relation='loan_request_relation',
                                        domain=[('type', '=', 'level')])


class Loans(models.Model):
    _inherit = 'payslip.loans'

    loan_id = fields.Many2one('hr.loan.salary.advance')
