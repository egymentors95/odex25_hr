# -*- coding: utf-8 -*-
from __future__ import division
from datetime import datetime

from odoo import models, fields, api, _, exceptions
from odoo.exceptions import UserError
import calendar

# import logging


class employee_overtime_request(models.Model):
    _name = 'employee.overtime.request'
    _rec_name = 'request_date'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'request_date DESC'

    request_date = fields.Date(default=lambda self: fields.Date.today())
    reason = fields.Text()
    date_to = fields.Date()
    date_from = fields.Date()
    transfer_type = fields.Selection([('accounting', 'Accounting'), ('payroll', 'Payroll')], default='payroll')

    overtime_plase = fields.Selection([('inside', 'Inside'), ('outside', 'Outside')])
    state = fields.Selection(
        [('draft', _('Draft')),
         ('submit', _('Waiting Direct Manager')),
         ('direct_manager', _('Waiting Department Manager')),
         ('financial_manager', _('Wait HR Department')),
         ('hr_aaproval', _('Wait Approval')),
         ('executive_office', _('Wait Transfer')),
         ('validated', _('Transferred')),
         ('refused', _('Refused'))], default="draft", tracking=True)

    # Relation fields
    account_id = fields.Many2one(comodel_name='account.account', string='Account')
    journal_id = fields.Many2one(comodel_name='account.journal', string='Payment Method')

    benefits_discounts = fields.Many2one(comodel_name='hr.salary.rule', string='Benefits/Discounts',
                                         domain=[('rules_type', '=', 'overtime')])
    line_ids_over_time = fields.One2many(comodel_name='line.ids.over.time', inverse_name='employee_over_time_id',
                                         tracking=True)

    department_id = fields.Many2one('hr.department')
    employee_id = fields.Many2one('hr.employee', 'Responsible', default=lambda item: item.get_user_id(),
                                  domain=[('state', '=', 'open')])
    employee_no = fields.Char(related='employee_id.emp_no', readonly=True,string='Employee Number', store=True)
    exception = fields.Boolean(string="Exception Hours", default=False,
                               help='Exceeding The Limit Of Overtime Hours Per Month')

    company_id = fields.Many2one('res.company',string="Company", default=lambda self: self.env.user.company_id)

    is_branch = fields.Many2one(related='department_id.branch_name', store=True, readonly=True)

    def get_user_id(self):
        employee_id = self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)
        if employee_id:
            return employee_id.id
        else:
            return False

    @api.onchange('employee_id')
    def get_department_id(self):
        if self.employee_id:
            self.department_id = self.employee_id.department_id.id

    @api.onchange('request_date','date_from')
    def chick_date_request(self):
        for rec in self:
            days_after = rec.employee_id.contract_id.working_hours.request_after_day
            if days_after > 0 and rec.date_from:
               rec.date_to=False
               date_from = datetime.strptime(str(rec.date_from), "%Y-%m-%d").date()
               request_date = datetime.strptime(str(rec.request_date), "%Y-%m-%d").date()
               last_day_date = date_from.replace(day=calendar.monthrange(date_from.year, date_from.month)[1])
               diff_days = (request_date - last_day_date).days
               if diff_days > days_after:
                  raise exceptions.Warning(_(
                        'Sorry, Cannot Be Request after %s Days From The End Of The Overtime Month') % days_after)


    #get account and journal from setting
    @api.onchange('transfer_type','employee_id')
    def get_account_ids(self):
        if self.transfer_type == 'accounting':
           self.journal_id = self.employee_id.contract_id.working_hours.journal_overtime_id
           self.account_id = self.employee_id.contract_id.working_hours.account_overtime_id

    @api.onchange('transfer_type', 'account_id', 'journal_id', 'line_ids_over_time')
    def onchange_transfer_type(self):
        if self.transfer_type == 'payroll':
            self.account_id = False
            self.journal_id = False
            for line in self.line_ids_over_time:
                line.account_id = False
                line.journal_id = False
        if self.transfer_type == 'accounting':
            for line in self.line_ids_over_time:
                if self.state == 'hr_aaproval':
                    if not line.account_id:
                        line.account_id = self.account_id
                    if not line.journal_id:
                        line.journal_id = self.journal_id
                #else:
                   # line.account_id = False
                   # line.journal_id = False

    @api.onchange('account_id')
    def onchange_account_id(self):
        for line in self.line_ids_over_time:
            line.account_id = self.account_id

    @api.onchange('journal_id')
    def onchange_journal_id(self):
        for line in self.line_ids_over_time:
            line.journal_id = self.journal_id

    def re_draft(self):
        # when redraft cancel the created account move
        if self.transfer_type == 'payroll':
            for record in self.line_ids_over_time:
                record.advantage_id.draft()
                record.advantage_id.unlink()

            self.state = 'draft'
        if self.transfer_type == 'accounting':
            if self.line_ids_over_time[0].move_id:
                move_id_not_draft = False
                for line in self.line_ids_over_time:
                    if line.move_id.state == 'posted':
                        move_id_not_draft_name = line.move_id.name
                        move_id_not_draft = True
                if move_id_not_draft:
                    raise exceptions.Warning(_(
                        'You can not cancel account move "%s" in state not draft') % move_id_not_draft_name)
                else:
                    for record in self.line_ids_over_time:
                        # record.move_id.write({'state': 'canceled'})
                        record.move_id.unlink()
                        record.write({
                            'move_id': False
                        })
                        #record.account_id = False
                        #record.journal_id = False
                    self.write({'state': 'draft'})
                    #self.account_id = False
                    #self.journal_id = False
            else:
                self.write({
                    'state': 'draft',
                    #'account_id': False,
                    #'journal_id': False
                })
                for record in self.line_ids_over_time:
                    record.write({
                        'move_id': False,
                        #'account_id': False,
                        #'journal_id': False
                    })

    def submit(self):
        if not self.line_ids_over_time:
            raise exceptions.Warning(_('Sorry, Can Not Request without The Employees'))
        self.line_ids_over_time.get_max_remain_hours()
        self.chick_not_mission()
        self.state = "submit"

    def direct_manager(self):
        for rec in self:
            rec.line_ids_over_time.chick_price_hour()
            rec.chick_not_mission()
            manager = rec.sudo().employee_id.parent_id
            hr_manager = rec.sudo().employee_id.company_id.hr_manager_id
            if manager:
               if manager.user_id.id == rec.env.uid or hr_manager.user_id.id == rec.env.uid:
                  rec.write({'state': 'direct_manager'})
               else:
                  raise exceptions.Warning(_("Sorry, The Approval For The Direct Manager '%s' Only OR HR Manager!")%(rec.employee_id.parent_id.name))
            else:
                rec.write({'state': 'direct_manager'})

    def financial_manager(self):
        for rec in self:
            rec.chick_not_mission()
            manager = rec.sudo().employee_id.coach_id
            hr_manager = rec.sudo().employee_id.company_id.hr_manager_id
            if manager:
               if manager.user_id.id == rec.env.uid or hr_manager.user_id.id == rec.env.uid:
                  rec.write({'state': 'financial_manager'})
               else:
                   raise exceptions.Warning(_("Sorry, The Approval For The Department Manager '%s' Only OR HR Manager!")%(rec.employee_id.coach_id.name))
            else:
                rec.write({'state': 'financial_manager'})

    def hr_aaproval(self):
        self.chick_not_mission()
        if self.exception == True:
            self.state = "hr_aaproval"
        else:
            self.state = "executive_office"

    def executive_office(self):
        self.chick_not_mission()
        self.state = "executive_office"

    def validated(self):
        if self.transfer_type == 'accounting':
            for item in self:
                for record in item.line_ids_over_time:
                    emp_type = record.employee_id.employee_type_id
                    account_debit_id = record.employee_id.contract_id.working_hours.get_debit_overtim_account_id(emp_type)
                    journal_id = record.employee_id.contract_id.working_hours.journal_overtime_id
                    analytic_account_id = record.employee_id.contract_id.working_hours.analytic_account_id
                    if not analytic_account_id:
                       analytic_account_id = record.employee_id.department_id.analytic_account_id
                    if not journal_id:
                        raise exceptions.Warning(_('You Must Enter The Journal Name Overtim Setting.'))
                    if not account_debit_id:
                        raise exceptions.Warning(_('Employee %s, has no Overtime Account Setting Base On Employee Type.'
                                                   ) % record.employee_id.name)
                    debit_line_vals = {
                        'name': record.employee_id.name,
                        'debit': record.price_hour,
                        'account_id': account_debit_id.id,
                        'partner_id': record.employee_id.user_id.partner_id.id,
                        'analytic_account_id': analytic_account_id.id,
                    }
                    credit_line_vals = {
                        'name': record.employee_id.name,
                        'credit': record.price_hour,
                        'account_id': journal_id.default_account_id.id,
                        'partner_id': record.employee_id.user_id.partner_id.id
                    }
                    if not record.move_id:
                       move = record.env['account.move'].create({
                           'state': 'draft',
                           'journal_id': journal_id.id,
                           'date': item.request_date,
                           'ref': record.employee_id.name,
                           'line_ids': [(0, 0, debit_line_vals), (0, 0, credit_line_vals)],
                           'res_model': 'employee.overtime.request',
                           'res_id': self.id
                       })
                       record.account_id = account_debit_id.id
                       record.journal_id = journal_id.id
                       record.move_id = move.id
            self.state = "validated"
        if self.transfer_type == 'payroll':
            # last_day_of_current_month = date.today().replace(day=calendar.monthrange(date.today().year, date.today().month)[1])
            # first_day_of_current_month = date.today().replace(day=1)
            for item in self:
                for record in item.line_ids_over_time:
                    if record.employee_id.contract_id:

                        advantage_arc = record.env['contract.advantage'].create({
                            'benefits_discounts': item.benefits_discounts.id,
                            'type': 'customize',
                            'date_from': item.date_from,
                            'date_to': item.date_to,
                            'amount': record.price_hour,
                            'over_time_id': True,
                            'employee_id': record.employee_id.id,
                            'contract_advantage_id': record.employee_id.contract_id.id,
                            'out_rule': True,
                            'state': 'confirm',
                            'comments': item.reason})
                        record.advantage_id = advantage_arc.id

                    else:
                        raise exceptions.Warning(_('Employee "%s" has no contract Please create contract to add '
                                                   'line to advantages') % record.employee_id.name)

            self.state = "validated"

    def refused(self):
        self.state = "refused"

    #Refuse For The Direct Manager Only
    def direct_manager_refused(self):
        for rec in self:
            manager = rec.sudo().employee_id.parent_id
            hr_manager = rec.sudo().employee_id.user_id.company_id.hr_manager_id
            if manager:
                if manager.user_id.id == rec.env.uid or hr_manager.user_id.id == rec.env.uid:
                   rec.refused()
                else:
                    raise exceptions.Warning(_("Sorry, The Refuse For The Direct Manager '%s' Only OR HR Manager!") % (manager.name))
            else:
                 rec.refused()

    #Refuse For The Department Manager Only
    def dep_manager_refused(self):
        for rec in self:
            manager = rec.sudo().employee_id.coach_id
            hr_manager = rec.sudo().employee_id.user_id.company_id.hr_manager_id
            if manager:
                if manager.user_id.id == rec.env.uid or hr_manager.user_id.id == rec.env.uid:
                   rec.refused()
                else:
                    raise exceptions.Warning(_("Sorry, The Refuse For The Department Manager '%s' Only !")%(rec.employee_id.coach_id.name))
            else:
                 rec.refused()

    def unlink(self):
        for i in self:
            if i.state != 'draft':
                raise exceptions.Warning(_('You can not delete record in state not in draft'))
            i.line_ids_over_time.unlink()
        return super(employee_overtime_request, self).unlink()

    @api.onchange('line_ids_over_time.employee_id', 'date_from', 'date_to')
    def chick_not_mission(self):
        for rec in self:
            Module = self.env['ir.module.module'].sudo()
            modules_mission = Module.search([('state', '=', 'installed'), ('name', '=', 'exp_official_mission')])
            if modules_mission:
                if rec.date_to and rec.date_from:
                    if rec.date_to < rec.date_from:
                        raise exceptions.Warning(_('Date Form Must Be Less than Date To'))
                    for line in rec.line_ids_over_time:
                        clause_1 = ['&', ('official_mission_id.date_from', '<=', rec.date_from),
                                    ('official_mission_id.date_to', '>=', rec.date_from)]
                        clause_2 = ['&', ('official_mission_id.date_from', '<=', rec.date_to),
                                    ('official_mission_id.date_to', '>=', rec.date_to)]
                        clause_3 = ['&', ('official_mission_id.date_from', '>=', rec.date_from),
                                    ('official_mission_id.date_to', '<=', rec.date_to)]
                        mission = self.env['hr.official.mission.employee'].search(
                            [('employee_id', '=', line.employee_id.id), ('official_mission_id.state', '!=', 'refused'),
                             ('official_mission_id.mission_type.related_with_financial', '=', True),
                             #('official_mission_id.mission_type.work_state', '=', 'legation'),
                             '|', '|'] + clause_1 + clause_2 + clause_3)
                        if mission:
                            raise exceptions.Warning(_('Sorry The Employee %s Actually Has Legation '
                                                       'Amount For this Period') % line.employee_id.name)

    # TOOO DOOO
    @api.onchange('overtime_plase', 'date_from', 'date_to', 'exception')
    def chick_hours_calenders(self):
        self.line_ids_over_time.chick_hours_calender()
        

class HrEmployeeOverTime(models.Model):
    _name = 'line.ids.over.time'
    _rec_name = 'employee_id'

    over_time_workdays_hours = fields.Float(string="workdays hours", tracking=True)
    over_time_vacation_hours = fields.Float(string="Vacation days hours", tracking=True)
    daily_hourly_rate = fields.Float(string='Daily Hourly Rate', compute='get_over_time_amount', store=True)
    holiday_hourly_rate = fields.Float(string='Holiday Hourly Rate', compute='get_over_time_amount', store=True)

    price_hour = fields.Float(string='Overtime Amount', compute='get_over_time_amount', store=True)

    # Relational fields
    account_id = fields.Many2one('account.account')
    journal_id = fields.Many2one('account.journal', string='Payment Method', domain=[('type', 'in', ('bank', 'cash'))])
    move_id = fields.Many2one('account.move')
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True)
    employee_over_time_id = fields.Many2one('employee.overtime.request', string='Employee')
    calculate_from_total = fields.Boolean(string="Calculate From Total")
    transfer_type = fields.Selection(related='employee_over_time_id.transfer_type')

    advantage_id = fields.Many2one(comodel_name='contract.advantage', string='Allowance Employee')

    max_hours = fields.Float(compute='get_max_remain_hours', string="Max Hours", store=True)
    remaining_hours = fields.Float(compute='get_max_remain_hours', string="Remaining Hours", store=True)
    #exception = fields.Boolean(string="Exception", default=False)
    exception  = fields.Boolean(related='employee_over_time_id.exception', string="Exception Hours", store=True)
    overtime_plase = fields.Selection(related='employee_over_time_id.overtime_plase', store=True,
                                      string="Overtime Plase")
    state = fields.Selection(related='employee_over_time_id.state', store=True, string="State")

    @api.constrains('price_hour')
    def chick_price_hour(self):
        for rec in self:
            if rec.employee_id:
               if rec.price_hour < 0:
                    raise exceptions.Warning(_('You can not Request Overtime The Employee %s The Overtime Amount Less Than Zero') % rec.employee_id.name)
               if rec.price_hour == 0:
                    raise exceptions.Warning(_('You can not Request Overtime The Employee %s The Overtime Amount Zero') % rec.employee_id.name)

    @api.onchange('overtime_plase', 'over_time_workdays_hours', 'over_time_vacation_hours', 'employee_id', 'exception')
    def chick_hours_calender(self):
        for rec in self:
            overtime_day_hour = 0
            overtime_holi_hour = 0
            # day_hour=0.0
            # holiday_hour=0.0
            if rec.employee_id:
                if not rec.employee_id.first_hiring_date:
                    raise exceptions.Warning(
                        _('You can not Request Overtime The Employee %s have Not First Hiring Date') % rec.employee_id.name)
            if rec.overtime_plase == 'inside' and rec.employee_id:
                attendance_transaction = self.env['hr.attendance.transaction'].search(
                    [('employee_id', '=', rec.employee_id.id),
                     ('date', '>=', rec.employee_over_time_id.date_from),
                     ('date', '<=', rec.employee_over_time_id.date_to)])
                for tran in attendance_transaction:
                    if tran.additional_hours > 0 and not tran.public_holiday:
                        overtime_day_hour += tran.additional_hours
                    if tran.public_holiday:
                        overtime_holi_hour += tran.office_hours
                if rec.over_time_workdays_hours > overtime_day_hour and not rec.exception:
                    raise exceptions.Warning(
                        _('The Overtime Workdays Employee %s Exceeded The Attendance workdays '
                          'Hours') % rec.employee_id.name)

                if rec.over_time_vacation_hours > overtime_holi_hour and not rec.exception:
                    raise exceptions.Warning(
                        _('The Overtime Publice Holiday Employee %s Exceeded The Attendance Public '
                          'Holiday Hours') % rec.employee_id.name)



    # dynamic domain on employee_id
    # Select employee once in Over Time Line
    @api.onchange('employee_id')
    def get_emplyee_id_domain(self):
        # Check if employee selected once
        if self.employee_over_time_id.department_id:
            # for dep in self.official_mission_id.department_id:
            employee_id = self.env['hr.employee'].search(
                [('department_id', '=', self.employee_over_time_id.department_id.id), ('state', '=', 'open')]).ids
            if employee_id:
                for line in self.employee_over_time_id.line_ids_over_time:
                    if line.employee_id:
                        if line.employee_id.id in employee_id:
                            employee_id.remove(line.employee_id.id)
                return {'domain': {'employee_id': [('id', 'in', employee_id)]}}
        else:
            employee_id = self.env['hr.employee'].search([('state', '=', 'open')]).ids
            if employee_id:
                for line in self.employee_over_time_id.line_ids_over_time:
                    if line.employee_id:
                        if line.employee_id.id in employee_id:
                            employee_id.remove(line.employee_id.id)
                return {'domain': {'employee_id': [('id', 'in', employee_id)]}}

    '''@api.model
    def default_get(self, fields):
        res = super(HrEmployeeOverTime, self).default_get(fields)
        if self._context.get('account_id') and self._context.get('journal_id'):
            res['account_id'] = self._context.get('account_id')
            res['journal_id'] = self._context.get('journal_id')
        return res'''

    @api.depends('employee_id.contract_id', 'over_time_workdays_hours', 'over_time_vacation_hours', 'employee_id',
                 'calculate_from_total')
    def get_over_time_amount(self):
        for line in self:
            contract_id = line.employee_id.contract_id
            if contract_id.working_hours:
                wage_daily = contract_id.total_allowance + (
                        contract_id.salary * contract_id.working_hours.overtime_factor_daily)
                # 1/2 Basic salary + total Salaey
                wage_holiday = contract_id.total_allowance + (
                        contract_id.salary * contract_id.working_hours.overtime_factor_holiday)
                # 1 Basic salary + total Salaey
                total_hours = contract_id.working_hours.work_days * contract_id.working_hours.work_hour
                # 240 per month
                if total_hours != 0:

                    price_hour_daily = wage_daily / total_hours
                    price_hour_holiday = wage_holiday / total_hours
                    # if line.over_time_workdays_hours > 0 or line.over_time_vacation_hours > 0:
                    if line.employee_id:
                        line.daily_hourly_rate = price_hour_daily
                        o_t_a_d = price_hour_daily * line.over_time_workdays_hours

                        line.holiday_hourly_rate = price_hour_holiday
                        o_t_a_v = price_hour_holiday * line.over_time_vacation_hours
                        line.price_hour = o_t_a_d + o_t_a_v

                        emp_total_hours = line.over_time_workdays_hours + line.over_time_vacation_hours

                        # if emp_total_hours > contract_id.working_hours.max_overtime_hour:
                        # raise exceptions.Warning(_('The Number Of Overtime Hours For The Employee %s Is Greater
                        # Max Hours per Month')% line.employee_id.name)

                else:
                    raise exceptions.Warning(_('The Number Of Overtime Hours And Days is Missing'))
            # else:
            #     line.daily_hourly_rate = 0
            #     line.holiday_hourly_rate = 0
            #
            #     line.price_hour = 0

    @api.depends('employee_id.contract_id', 'employee_id', 'employee_over_time_id.date_from',
                 'employee_over_time_id.date_to','over_time_workdays_hours','over_time_vacation_hours')
    def get_max_remain_hours(self):
        for line in self:
            contract_id = line.employee_id.contract_id
            if contract_id.working_hours:
                line.max_hours = contract_id.working_hours.max_overtime_hour
                if line.employee_over_time_id.date_to and line.employee_over_time_id.date_from:
                    month_current_from = datetime.strptime(str(line.employee_over_time_id.date_from),
                                                           '%Y-%m-%d').strftime('%m')
                    year_current_from = datetime.strptime(str(line.employee_over_time_id.date_from),
                                                          '%Y-%m-%d').strftime('%y')
                    month_current_to = datetime.strptime(str(line.employee_over_time_id.date_to),
                                                         '%Y-%m-%d').strftime('%m')
                    year_current_to = datetime.strptime(str(line.employee_over_time_id.date_to),
                                                        '%Y-%m-%d').strftime('%y')
                    if month_current_from != month_current_to or year_current_from != year_current_to:
                        raise exceptions.Warning(
                            _('Sorry, The overtime period Must be During the same Month for the Year'))
                    overtime_ids = self.search(
                        [('employee_id', '=', line.employee_id.id), ('employee_over_time_id.state', '!=', 'refused')])
                    total_hours = 0.0
                    remaining_hours = line.max_hours
                    for rec in overtime_ids:
                        month_previous = datetime.strptime(str(rec.employee_over_time_id.date_from),
                                                           '%Y-%m-%d').strftime('%m')
                        year_previous = datetime.strptime(str(rec.employee_over_time_id.date_from),
                                                          '%Y-%m-%d').strftime('%y')
                        if month_current_from == month_previous and year_current_from == year_previous:
                            total_hours += rec.over_time_workdays_hours + rec.over_time_vacation_hours
                            remaining_hours = line.max_hours - total_hours
                    line.remaining_hours = remaining_hours
                    if remaining_hours < 0 and line.exception == False:
                        raise  UserError(
                            _('The Number Of Overtime Hours For The Employee %s Is Greater Max Hours per '
                              'Month') % line.employee_id.name)

    def unlink(self):
        for i in self:
            if i.state != 'draft':
                raise exceptions.Warning(_('You can not delete record in state not in draft'))
        return super(HrEmployeeOverTime, self).unlink()
