from odoo import api, fields, models, _
from datetime import datetime, date, timedelta
from odoo.exceptions import ValidationError
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT



class EmployeeMissionSelectionWizard(models.TransientModel):
    _name = 'employee.mission.selection.wizard'
    _description = 'Employee Selection Wizard'


    employee_ids = fields.Many2many(
        'hr.employee',
        string='Employees',
        required=True,
    )

    employee_mission_id = fields.Many2one(comodel_name='hr.official.mission',string='Employee Mission')

    def _get_active_employee_mission(self):
        mission_id = self.env.context.get('default_employee_mission_id')
        if not mission_id and self.env.context.get('active_model') == 'hr.official.mission':
            mission_id = self.env.context.get('active_id')
        return mission_id

    @api.onchange('employee_ids')
    def _onchange_employee_ids(self):

        mission = self.env['hr.official.mission'].browse(self._get_active_employee_mission())

        if mission.department_id:
            # for dep in self.official_mission_id.department_id:

            if mission.course_name and mission.course_name.job_ids:
                employee_id = self.env['hr.employee'].search(
                    [('department_id', 'in', mission.department_id.ids), ('state', '=', 'open'),
                     ('job_id', 'in', mission.course_name.job_ids.ids)]).ids
            else:
                employee_id = self.env['hr.employee'].search(
                    [('department_id', 'in', mission.department_id.ids),
                     ('state', '=', 'open')]).ids
            if employee_id:
                for line in mission.employee_ids:
                    if line.employee_id:
                        if line.employee_id.id in employee_id:
                            employee_id.remove(line.employee_id.id)
                return {'domain': {'employee_ids': [('id', 'in', employee_id)]}}
        else:
            if mission.course_name and mission.course_name.job_ids:
                employee_id = self.env['hr.employee'].search(
                    [('state', '=', 'open'), ('job_id', 'in', mission.course_name.job_ids.ids)]).ids
            else:
                employee_id = self.env['hr.employee'].search([('state', '=', 'open')]).ids
            if employee_id:
                for line in mission.employee_ids:
                    if line.employee_id:
                        if line.employee_id.id in employee_id:
                            employee_id.remove(line.employee_id.id)
                return {'domain': {'employee_ids': [('id', 'in', employee_id)]}}

    def action_confirm(self):
        """
        Action to add employees to current employee reward record
        """
        self.ensure_one()

        # Get the current mission record or create a new one
        mission = self.env['hr.official.mission'].browse(self._get_active_employee_mission())

        if not mission.exists():
            # Get values from context
            mission_vals = self.env.context.get('default_mission_vals', {})
            mission = self.env['hr.official.mission'].create(mission_vals)

        date_to = datetime.strptime(str(mission.date_to), DEFAULT_SERVER_DATE_FORMAT)
        date_from = datetime.strptime(str(mission.date_from), DEFAULT_SERVER_DATE_FORMAT)

        # Prepare values for mission lines
        vals_list = [
            {
                'employee_id': employee.id,
                'date_from': date_from,
                'date_to': date_to,
                'hour_from': mission.hour_from,
                'hour_to': mission.hour_to,
            }
            for employee in self.employee_ids
        ]

        existing_employees = mission.employee_ids.mapped('employee_id').ids
        duplicate_employees = set(self.employee_ids.ids) & set(existing_employees)

        if duplicate_employees:
            duplicate_names = self.env['hr.employee'].browse(list(duplicate_employees)).mapped('name')
            raise ValidationError(_(
                "The following employees are already in training lines: %s" % ', '.join(duplicate_names)
            ))

        # Create all records in a single operation
        mission.write({
            'employee_ids': [(0, 0, vals) for vals in vals_list]
        })
        for line in mission.employee_ids:
            line.compute_number_of_days()
            line.compute_number_of_hours()
            line.compute_day_price()
            line.compute_Training_cost_emp()
            line.chick_not_overtime()

        return {'type': 'ir.actions.act_window_close'}