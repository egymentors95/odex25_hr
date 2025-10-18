from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class EmployeeSelectionWizard(models.TransientModel):
    _name = 'employee.selection.wizard'
    _description = 'Employee Selection Wizard'


    employee_ids = fields.Many2many(
        'hr.employee',
        string='Employees',
        required=True,
    )

    employee_reward_id = fields.Many2one(comodel_name='hr.employee.reward',string='Employee_reward_id')

    @api.onchange('employee_ids')
    def _onchange_employee_ids(self):
        return {
            'domain': {
                'employee_ids': [
                    ('id', 'not in', self.employee_ids.ids),
                    ('state','=','open'),
                    ('active', '=', True)
                ]
            }
        }

    def _get_active_employee_reward(self):
        reward_id = self.env.context.get('default_employee_reward_id')
        if not reward_id and self.env.context.get('active_model') == 'hr.employee.reward':
            reward_id = self.env.context.get('active_id')
        return reward_id

    def action_confirm(self):
        """
        Action to add employees to current employee reward record
        """
        self.ensure_one()

        # Get the current reward record or create a new one
        reward = self.env['hr.employee.reward'].browse(self._get_active_employee_reward())

        if not reward.exists():
            # Get values from context
            reward_vals = self.env.context.get('default_reward_vals', {})
            reward = self.env['hr.employee.reward'].create(reward_vals)

        print('percentage >>>>>>', self.env.context.get('default_reward_vals', {}))

        # Prepare values for reward lines
        vals_list = [
            {
                'employee_id': employee.id,
                'employee_reward_id': reward.id,
            }
            for employee in self.employee_ids
        ]
        existing_employees = reward.line_ids_reward.mapped('employee_id').ids
        duplicate_employees = set(self.employee_ids.ids) & set(existing_employees)

        if duplicate_employees:
            duplicate_names = self.env['hr.employee'].browse(list(duplicate_employees)).mapped('name')
            raise ValidationError(_(
                "The following employees are already in reward lines: %s" % ', '.join(duplicate_names)
            ))

        # Create all records in a single operation
        reward.write({
            'line_ids_reward': [(0, 0, vals) for vals in vals_list]
        })
        for line in reward.line_ids_reward:
            fields = ['percentage', 'account_id', 'journal_id']
            default_values = line.sudo().default_get(fields)

            # Apply the default values to the line
            line.write(default_values)
            line.sudo().get_percentage_appraisal()
            line.sudo()._compute_calculate_amount()

        return {'type': 'ir.actions.act_window_close'}