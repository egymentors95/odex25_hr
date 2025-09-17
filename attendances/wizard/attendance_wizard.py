# -*- coding: utf-8 -*-
from odoo import models, fields
from datetime import datetime, timedelta


class HrAttendanceWizard(models.TransientModel):
    _name = 'hr.attendance.wizard'

    date_from = fields.Datetime(string='Date From')
    date_to = fields.Datetime(string='Date To')
    get_attendance_from = fields.Selection(selection=[('finger_print', 'Finger Print'),
                                                      ('manual', 'Manual')], string='Get Attendances From')

    def generate_missing_attendance(self):
        transactions = self.env['hr.attendance.transaction']
        if self.get_attendance_from == 'manual':
            start_date = datetime.strptime(str(self.date_from), "%Y-%m-%d %H:%M:%S")+ timedelta(hours=3)
            end_date = datetime.strptime(str(self.date_to), "%Y-%m-%d %H:%M:%S")+ timedelta(hours=3)
            delta = end_date - start_date
            for i in range(delta.days + 1):
                day = start_date + timedelta(days=i)
                transactions.process_attendance_scheduler_queue(day)
        else:
            if self.env['ir.module.module'].sudo().search([('state', '=', 'installed'),
                                                           ('name', '=', 'to_attendance_device')]):
                self.env['attendance.wizard'].cron_sync_attendance()
