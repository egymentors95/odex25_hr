# -*- coding: utf-8 -*-

from odoo import models, fields, api,_
from datetime import datetime,timedelta
import time
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT,DEFAULT_SERVER_DATE_FORMAT
from odoo.exceptions import ValidationError


class HrPersonalPermission(models.Model):
    _inherit = 'hr.personal.permission'

    deduct_from_holiday = fields.Boolean(related='permission_type_id.half_holiday', string="Half Day Off")
    holiday = fields.Many2one('hr.holidays',string="Holiday")
    permission_amount = fields.Float(string="Permission Amount")
    permission_number = fields.Float(compute="get_permission_number", store=True)


    def send(self):
        res = super(HrPersonalPermission,self).send()
        self.get_permission_number()
        #self._get_date_constrains(employee_permissions)
        self.permission_number_decrement()
        return res

    def get_date_to_constrains_value(self):
        current_date = datetime.strptime(str(self.date_to), DEFAULT_SERVER_DATETIME_FORMAT)
        current_month = datetime.strptime(str(self.date_to), DEFAULT_SERVER_DATETIME_FORMAT).month
        date_from = current_date.strftime('%Y-{0}-01'.format(current_month))
        date_to = current_date.strftime('%Y-{0}-01'.format(current_month + 1))
        if current_month == 12:
            date_to = current_date.strftime('%Y-{0}-31'.format(current_month))
        employee_permissions = self.search([
            ('employee_id', '=', self.employee_id.id),
            ('permission_type_id', '=', self.permission_type_id.id),
            ('state', 'in', ('send', 'approve')),
            ('date_from', '>=', date_from),
            ('date_to', '<=', date_to)])
        return date_from, date_to, employee_permissions

    @api.depends('date_to', 'date_from', 'employee_id', 'permission_type_id')
    def get_permission_number(self):
        for rec in self:
            if rec.date_to:
                date_from, date_to, employee_permissions = rec.get_date_to_constrains_value()
                basic = employee_permissions.filtered(lambda r: r.deduct_from_holiday == False)
                permission_type_id = rec.permission_type_id
                all_perission = 0.0
                for item in employee_permissions.filtered(lambda r: r.id != self.id):
                    if item.deduct_from_holiday == False:
                       all_perission += item.duration

                if permission_type_id.monthly_hours - all_perission > 0:
                    rec.permission_number = round(permission_type_id.monthly_hours - all_perission, 2)

    # @api.onchange('date_to', 'date_from', 'employee_id','deduct_from_holiday')
    @api.constrains('date_to', 'date_from', 'employee_id', 'permission_type_id', 'deduct_from_holiday')
    def permission_number_decrement(self):
        for rec in self:
            if not rec.employee_id.first_hiring_date:
               raise ValidationError(_('You can not Request Permission The Employee have Not First Hiring Date'))
            if rec.date_to:
                rec.check_holiday_mission()

                date_from, date_to, employee_permissions = rec.get_date_to_constrains_value()
                calender = rec.employee_id.resource_calendar_id
                day_hours = calender.work_hour
                rec.permission_amount = rec.duration/day_hours
                basic = employee_permissions.filtered(lambda r:r.deduct_from_holiday == False and r.id != self.id)

                for item in employee_permissions.filtered(lambda r:r.id != self.id):

                    if item.date_to and rec.date_to:
                       permission_date1 = datetime.strptime(str(item.date_to),DEFAULT_SERVER_DATETIME_FORMAT).date()
                       date_to_value1 = datetime.strptime(str(rec.date_to), DEFAULT_SERVER_DATETIME_FORMAT).date()
                       if permission_date1 == date_to_value1:
                          raise ValidationError(_('Sorry You Have Used All Your Permission In This Day you have one permission per a Day'))

                employee_permissions_holiday = employee_permissions.filtered(lambda r: r.deduct_from_holiday == True and r.id != self.id)
                if rec.deduct_from_holiday:
                    if rec.permission_number >= 0.0:
                        rec._get_date_constrains(employee_permissions_holiday)
                        annual = rec.env['hr.holidays.status'].search([('leave_type', '=', 'annual')
                                         ,('permission_annual_holiday', '=',True),])
                        for itm in annual:
                            if rec.employee_id and itm:
                               holiday = rec.env['hr.holidays'].search([('employee_id', '=', rec.employee_id.id),('type', '=', 'add'),
                                                  ('holiday_status_id', '=', itm.id),
                                                  ('check_allocation_view', '=', 'balance')
                                                  ], order='id desc', limit=1)
                               if holiday:
                                    rec.holiday = holiday.id
                                    balance = holiday.remaining_leaves or 0.0
                                    if len(employee_permissions_holiday) < rec.permission_type_id.monthly_hours:
                                        if balance < rec.permission_amount:
                                            raise ValidationError(_('Sorry you Have No leave balance'))
                                    else:
                                        raise ValidationError(_
                                              ('Sorry You Have Used All Your Permission To Half Day Off'))
       
                            else:
                                raise ValidationError(_('Sorry You Have No annual Leave To Deduct Permission'))
                    #else:
                        #raise ValidationError(_('Sorry You Need To use Basic Permission Before Use Holidays'))
                else:
                    rec._get_date_constrains(basic)

    def leave_balance_process(self):
        if self.deduct_from_holiday:
            if self.holiday.remaining_leaves >= self.permission_amount:
                self.holiday.remaining_leaves -= self.permission_amount
                self.holiday.leaves_taken += self.permission_amount
            else:
                raise ValidationError(_('Sorry you Have No leave balance'))

    def cancel_leave_balance_process(self):
        if self.deduct_from_holiday:
            self.holiday.remaining_leaves += self.permission_amount
            self.holiday.leaves_taken -= self.permission_amount

    def approve(self):
        res = super(HrPersonalPermission,self).approve()
        self.leave_balance_process()
        self.get_permission_number()
        return res

    def draft_state(self):
        if self.state == 'approve' and self.deduct_from_holiday:
            self.cancel_leave_balance_process()
        res = super(HrPersonalPermission,self).draft_state()
        return res

    def _get_date_constrains(self, employee_permissions):
        for item in self:
            number_of_per = item.permission_type_id.monthly_hours
            if employee_permissions.filtered(lambda r: r.id != self.id):
                employee_permissions_to = employee_permissions.mapped('date_to')
                date_to_value = datetime.strptime(str(item.date_to), DEFAULT_SERVER_DATETIME_FORMAT).date()
                for emp_date in employee_permissions_to:
                    permission_date = datetime.strptime(str(emp_date), DEFAULT_SERVER_DATETIME_FORMAT).date()
                    if permission_date == date_to_value:
                        raise ValidationError(
                            _('Sorry You Have Used All Your Permission In This Day you have one permission per a Day'))
            start_date_value = datetime.strptime(str(item.date_from), "%Y-%m-%d %H:%M:%S")
            end_date = datetime.strptime(str(item.date_to), "%Y-%m-%d %H:%M:%S")
            if start_date_value <= end_date:
                days = (end_date - start_date_value).days
                seconds_diff = (end_date - start_date_value).seconds
                item.duration = (days * 24) + seconds_diff / 3600

                all_perission=0
                for rec in employee_permissions:
                    if rec.deduct_from_holiday == False:
                       all_perission += rec.duration

                if number_of_per < all_perission :
                    raise ValidationError(_('Sorry You Have Used All Your Permission Hours In This Month'))

                if item.duration <= 0.0:
                    raise ValidationError(_('This Duration Must Be Greater Than Zero'))
                if not item.deduct_from_holiday:
                   if item.duration < item.balance and item.duration < item.permission_number:
                      raise ValidationError(_('This Duration must be Greater than or equal to the Permission Limit'))

                if item.duration > item.permission_number and item.deduct_from_holiday== False:
                    raise ValidationError(_('This Duration not Allowed it must be Less Than or equal Permission Hours in Month'))

#################### Half day holiday 4 hours ##########
                if item.deduct_from_holiday:
                   date_from = datetime.strptime(str(item.date_from), "%Y-%m-%d %H:%M:%S")
                   date_to = datetime.strptime(str(item.date_to), "%Y-%m-%d %H:%M:%S")
                   date_from_time = (date_from + timedelta(hours=3)).time()
                   date_to_time = (date_to + timedelta(hours=3)).time()
                   hour_from = date_from_time.hour + date_from_time.minute / 60.0
                   hour_to = date_to_time.hour + date_to_time.minute / 60.0
                   #print('>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>',hour_from,hour_to)

                   if item.duration != item.permission_type_id.daily_hours:
                      raise ValidationError(_('The Number Of Hours should Be %s Hours For the Half Day Leave') % item.permission_type_id.daily_hours)

                   if item.employee_id.contract_id.working_hours.is_full_day== True:
                      hour_sign = item.employee_id.contract_id.working_hours.full_min_sign_in
                      hour_sign_out = item.employee_id.contract_id.working_hours.full_max_sign_out
                      #print('######################################',hour_sign,hour_sign_out)
                      if hour_from < hour_sign or hour_to > hour_sign_out:
                         raise ValidationError(_('Sorry, Must Be a Half Day Period Within Working Hours'))


class HrPersonalPermissionType(models.Model):
    _inherit = 'hr.personal.permission.type'

    half_holiday = fields.Boolean(string="Half Holiday",
                                  help='The permission deducted From The Annual Holiday balance')
 
