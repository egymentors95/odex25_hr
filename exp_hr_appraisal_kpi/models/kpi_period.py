from odoo import fields, models, api,_
from odoo.exceptions import ValidationError
from odoo import models, api, exceptions
from datetime import timedelta
class KPIPeriod(models.Model):
    _inherit = 'kpi.period'
    kpi_periods_ids = fields.One2many(
        comodel_name='kpi.period.notes',
        inverse_name='kpi_period_id',
        ondelete='cascade')  # Add this line to enable cascade deletion
    kpi_goals_periods_ids = fields.One2many(
    comodel_name='kpi.period.notes',
    inverse_name='kpi_goal_period_id',
    ondelete='cascade' ) # Add this line to enable cascade deletion



class KIPSkills (models.Model):
    _name = 'kpi.period.notes'
    
    name = fields.Char(string='Name',)
    sequence = fields.Char(string='Sequence',)
    date_start_k = fields.Date(string='Star Date',)
    date_end_k = fields.Date(string='End Date',)
    kpi_period_id = fields.Many2one(comodel_name='kpi.period',ondelete='cascade')
    kpi_goal_period_id = fields.Many2one(comodel_name='kpi.period',ondelete='cascade')

    def create_apprisal_goals_employee(self):
        employee_objs = self.env['hr.employee'].search([('state','=','open')])
        employee_id = self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)

        for item in self:
                # Fill employee appraisal
                for element in employee_objs:
                    appraisal_line = {
                        'employee_id': element.id,
                        'year_id': item.kpi_goal_period_id.id,
                        'department_id': element.department_id.id,
                        'job_id': element.job_id.id,
                        'manager_id': employee_id.id,
                        'date_apprisal': fields.Date.today(),
                        'period_goals_id': item.id,
                    }
                    line_id = self.env['employee.performance.evaluation'].create(appraisal_line)
                    line_id.onchange_emp_goal_ids()
    @api.constrains('date_start_k','kpi_goal_period_id','date_end_k')
    def _check_period_overlap(self):
        print('in constriant..2222.........')
        for record in self:
            if record.kpi_goal_period_id:
                periods = record.kpi_goal_period_id.kpi_goals_periods_ids.sorted(key=lambda r: r.date_start_k)
                for i in range(1, len(periods)):
                    if periods[i-1].date_end_k >= periods[i].date_start_k:
                        raise ValidationError(_("Overlap detected between periods!"))

    @api.constrains('date_start_k','kpi_period_id','date_end_k')
    def _check_period_overlap2(self):
        print('in constriant...........')
        for record in self:
            if record.kpi_period_id:
                periods = record.kpi_period_id.kpi_periods_ids.sorted(key=lambda r: r.date_start_k)
                for i in range(1, len(periods)):
                    if periods[i-1].date_end_k >= periods[i].date_start_k:
                        raise ValidationError(_("Overlap detected between periods!"))
