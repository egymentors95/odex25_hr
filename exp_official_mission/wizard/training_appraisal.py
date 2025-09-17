from odoo import api, fields, models, _
from datetime import datetime, date, timedelta
from odoo.exceptions import ValidationError
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT



class TrainingAppraisalWizard(models.TransientModel):
    _name = 'training.appraisal.wizard'
    _description = 'Training Appraisal Wizard'

    appraisal_plan_id = fields.Many2one('appraisal.plan', string="Appraisal Plan", required=True)
    employee_ids = fields.Many2many(
        'hr.employee',
        string='Employees',
        required=True,
    )

    def _get_active_employee_mission(self):
        if self.env.context.get('active_model') == 'hr.official.mission':
            mission_id = self.env.context.get('active_id')
        return mission_id

    @api.onchange('employee_ids')
    def _onchange_employee_ids(self):
        mission = self.env['hr.official.mission'].browse(self._get_active_employee_mission())
        employee_id = []
        if mission.employee_ids:
            for line in mission.employee_ids:
                if line.employee_id:
                    if line.employee_id.id in employee_id:
                        employee_id.remove(line.employee_id.id)
                    if line.status == 'done' and not line.appraisal_id:
                        employee_id.append(line.employee_id.id)

            return {'domain': {'employee_ids': [('id', 'in', employee_id)]}}



    def create_employee_appraisal(self):
        mission = self.env['hr.official.mission'].browse(self._get_active_employee_mission())

        if not mission.exists():
            # Get values from context
            mission_vals = self.env.context.get('default_mission_vals', {})
            mission = self.env['hr.official.mission'].create(mission_vals)

        for employee in mission.employee_ids:
            if employee.employee_id in self.employee_ids:
                vals_list = {
                    'employee_id': employee.employee_id.id,
                    'date_from': employee.date_from,
                    'date_to': employee.date_to,
                    'appraisal_plan_id': self.appraisal_plan_id.id,
                    'appraisal_type': 'training',
                    'appraisal_date': date.today(),
                    'mission_id': mission.id,
                }

                appraisal = self.env['hr.employee.appraisal'].sudo().create(vals_list)
                appraisal.fill_employee_or_manager_appraisal()
                employee.appraisal_id = appraisal.id


        return {'type': 'ir.actions.act_window_close'}