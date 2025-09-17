from typing import Optional, Any, Dict

from odoo import fields, models, api
from odoo.tools.translate import _


class HrEmployeeBase(models.AbstractModel):
    _inherit = 'hr.employee.base'
    attendance_state = fields.Selection(string="Attendance Status", compute='_compute_attendance_state_new',
                                        selection=[('checked_out', "Checked out"), ('checked_in', "Checked in")])

    @api.depends('last_attendance_id.check_in', 'last_attendance_id.check_out', 'last_attendance_id')
    def _compute_attendance_state_new(self):
        for employee in self:
            att = self.env['attendance.attendance'].sudo().search([('employee_id', '=', employee.id)],
                                                                  limit=1, order='id desc')
            if att:
                employee.attendance_state = 'checked_in' if att.action == 'sign_in' else 'checked_out'
            else:
                employee.attendance_state = 'checked_out'


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    def attendance_manual(self, next_action: str, entered_pin: Optional[str] = None, **kwargs: Any) -> Dict[str, Any]:
        selected_action = kwargs.get('selected_action', 'none')
        self.ensure_one()
        attendance_user_and_no_pin = self.user_has_groups(
            'hr_attendance.group_hr_attendance_user,'
            '!hr_attendance.group_hr_attendance_use_pin')
        can_check_without_pin = attendance_user_and_no_pin or (self.user_id == self.env.user and entered_pin is None)
        if can_check_without_pin or entered_pin is not None and entered_pin == self.sudo().pin:
            return self._attendance_action(next_action, selected_action)
        return {'warning': _('Wrong PIN')}

    def _attendance_action(self, next_action: str, selected_action: Optional[str] = None) -> Dict[str, Any]:
        if not selected_action:
            return super(HrEmployee, self)._attendance_action(next_action)
        self.ensure_one()
        employee = self.sudo()
        action_message = self.env["ir.actions.actions"]._for_xml_id(
            "hr_attendance.hr_attendance_action_greeting_message")
        last_attendance_id = self.env['attendance.attendance'].sudo().search([('employee_id', '=', self.id)],
                                                                             limit=1, order='id desc')

        action_message['previous_attendance_change_date'] = last_attendance_id and last_attendance_id.action_date
        action_message['employee_name'] = employee.name
        action_message['barcode'] = employee.barcode
        action_message['next_action'] = next_action
        action_message['hours_today'] = employee.hours_today

        if employee.user_id:
            modified_attendance = employee.with_user(employee.user_id)._attendance_action_change(selected_action)
        else:
            modified_attendance = employee._attendance_action_change(selected_action)
        action_message['attendance'] = modified_attendance.read()[0]
        if modified_attendance.action == 'sign_in':
            action_message['attendance']['check_in'] = action_message['attendance']['name']
        else:
            action_message['attendance']['check_out'] = action_message['attendance']['name']
        return {'action': action_message}

    def _attendance_action_change(self, selected_action: Optional[str] = None) -> "models.Model":
        if not selected_action:
            return super(HrEmployee, self)._attendance_action_change()
        self.ensure_one()
        if selected_action in ('sign_out', 'sign_in'):
            vals = {
                'employee_id': self.id,
                'action': selected_action,
                'action_type': 'manual'
            }
            return self.env['attendance.attendance'].create(vals)

        attendance = self.env['attendance.attendance'].search([('employee_id', '=', self.id)],
                                                              limit=1, order='id desc')
        if not attendance:
            return self._attendance_action_change(selected_action='sign_in')

        vals = {
            'employee_id': self.id,
            'action': 'sign_in' if attendance.action == 'sign_out' else 'sign_out',
            'action_type': 'manual'
        }
        return self.env['attendance.attendance'].create(vals)
