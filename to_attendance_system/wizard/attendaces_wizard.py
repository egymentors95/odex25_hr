from odoo import models, fields, api, _
from odoo.exceptions import UserError

import logging

_logger = logging.getLogger(__name__)


class AttendanceWizard(models.TransientModel):
    _name = 'finger.attendance_wizard'
    _description = 'Attendance Wizard'

    @api.model
    def _get_all_systems_ids(self):
        all_systems = self.env['finger.biotime_api'].search([('state', '=', 'authentic')])
        if all_systems:
            return all_systems.ids
        else:
            return []

    system_ids = fields.Many2many('finger.biotime_api', string='System', default=_get_all_systems_ids,
                                  domain=[('state', '=', 'confirmed')])

    def download_attendance_manually(self):
        if not self.system_ids:
            raise UserError(_('You must select at least one device to continue!'))
        self.system_ids.action_attendance_download()

    def download_system_attendance(self):
        systems = self.env['finger.biotime_api'].search([('state', '=', 'authentic')])
        systems.action_attendance_download()

    def cron_sync_attendance(self):
        self.with_context(synch_ignore_constraints=True).sync_attendance()

    def sync_attendance(self):

        synch_ignore_constraints = self.env.context.get('synch_ignore_constraints', False)
        HR = self.env['hr.employee']
        attendance = self.env['attendance.attendance']
        attendance_ids = self.env['finger.system_attendance'].search([('state', '=', 'draft')])

        for tx in attendance_ids:
            if tx.emp_code and tx.emp_code.hr_employee:
                attendance.create({
                    'employee_id': tx.emp_code.hr_employee.id,
                    'name': tx.punch_time,
                    'action': 'sign_in' if tx.punch_state in ["1", "4", "5"] else 'sign_out',
                    'action_date': tx.punch_time,
                })
                tx.write({
                    'state': 'confirmed'
                })
