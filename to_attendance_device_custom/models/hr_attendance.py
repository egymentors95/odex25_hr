# -*- coding: utf-8 -*-
from odoo import models, fields, api


class Attendance(models.Model):
    _inherit = 'attendance.attendance'

    device_id = fields.Many2one('attendance.device', string='Device', readonly=True,
                                help='The device with which user took check in/out action')
    attendance_id = fields.Many2one('hr.attendance', string='Attendance')


class AttendanceTransaction(models.Model):
    _inherit = 'hr.attendance.transaction'

    checkin_device_id = fields.Many2one('attendance.device', string='Checkin Device', readonly=True,
                                        help='The device with which user took check in action')
    checkout_device_id = fields.Many2one('attendance.device', string='Checkout Device', readonly=True,
                                         help='The device with which user took check out action')


class HrAttendance(models.Model):
    _inherit = 'hr.attendance'

    @api.model
    def create(self, vals):
        res_id = super(HrAttendance, self).create(vals)
        val = {'employee_id': res_id.employee_id.id,
               'action_type': 'finger_print',
               'attendance_id': res_id.id,
               'device_id': res_id.checkin_device_id and res_id.checkin_device_id.id or False
               }
        if res_id.check_in:
            val['name'] = res_id.check_in
            val['action'] = 'sign_in'
            val['action_date'] = fields.Datetime.from_string(res_id.check_in).date()
            self.env['attendance.attendance'].create(val)
        if res_id.check_out:
            val['name'] = res_id.check_out
            val['action'] = 'sign_out'
            val['device_id'] = res_id.checkout_device_id and res_id.checkout_device_id.id
            self.env['attendance.attendance'].create(val)
        return res_id

    def write(self, vals):
        super(HrAttendance, self).write(vals)
        if 'check_out' or 'checkout_device_id' in vals:
            self.env['attendance.attendance'].create({'employee_id': self.employee_id.id,
                                                      'action_type': 'finger_print',
                                                      'attendance_id': self.id,
                                                      'name': self.check_out,
                                                      'action': 'sign_out',
                                                      'action_date': fields.Datetime.from_string(self.check_out).date(),
                                                      'device_id': self.checkout_device_id and
                                                                self.checkout_device_id.id or False
                                                      })
