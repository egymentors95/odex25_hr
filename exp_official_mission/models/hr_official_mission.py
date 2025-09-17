# -*- coding: utf-8 -*-
import calendar
from datetime import datetime, date, timedelta
from odoo.exceptions import ValidationError
from odoo import models, fields, api, exceptions
from odoo.exceptions import UserError
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT
from odoo.tools.translate import _

EMPLOYEE_DOMAIN = []


class HrOfficialMission(models.Model):
    _name = 'hr.official.mission'
    _rec_name = 'mission_type'
    _description = 'Official mission'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_from desc'

    date = fields.Date(default=lambda self: fields.Date.today())
    date_from = fields.Date()
    date_to = fields.Date()
    hour_from = fields.Float(default=8)
    hour_to = fields.Float(default=16)
    date_duration = fields.Float()
    hour_duration = fields.Float(default=8)
    total_hours = fields.Float(compute='compute_number_of_hours',store=True,)
    balance = fields.Float()
    early_exit = fields.Boolean()
    mission_purpose = fields.Text()
    state = fields.Selection([('draft', _('Draft')),
                              ('send', _('Waiting Direct Manager')),
                              ('direct_manager', _('Waiting Department Manager')),
                              ('depart_manager', _('Wait HR Department')),
                              ('hr_aaproval', _('Wait Approval')),
                              ('approve', _('Approved')),
                              ('refused', _('Refused'))], default="draft", tracking=True)
    duration_type = fields.Selection(default='days', related='mission_type.duration_type')
    move_type = fields.Selection(selection=[('payroll', _('Payroll')),
                                            ('accounting', _('Accounting'))], default='payroll')
    related_with_financial = fields.Boolean(related='mission_type.related_with_financial')

    # Relational fields
    department_id = fields.Many2many('hr.department')
    attach_ids = fields.One2many('ir.attachment', 'mission_id')
    employee_ids = fields.One2many('hr.official.mission.employee', 'official_mission_id')
    table_ids = fields.One2many('mission.table', 'destination_id',)

    approved_by = fields.Many2one(comodel_name='res.users')
    refused_by = fields.Many2one(comodel_name='res.users')
    mission_type = fields.Many2one('hr.official.mission.type', tracking=True)
    country_id = fields.Many2one('res.country', )
    # add new field
    miss_state = fields.Selection(related='mission_type.work_state')
    official_mission = fields.Many2one('hr.salary.rule', domain=[('rules_type', '=', 'mandate')])

    ticket_insurance = fields.Char()
    car_insurance = fields.Char()
    self_car = fields.Char()
    car_type = fields.Char()
    rent_days = fields.Integer()
    max_rent = fields.Float()
    visa = fields.Char()
    note = fields.Char()
    course_name = fields.Many2one('employee.course.name')
    process_type = fields.Selection(
        selection=[('mission', _('Mission')), ('training', _('Training')), ('especially_hours', _('Especially Hours'))])
    train_category = fields.Selection(selection=[('training', _('Training')), ('workshop', _('Workshop')),
                                                 ('seminar', _('Seminar')), ('conference', _('Conference')),
                                                 ('other', _('Other'))])
    partner_id = fields.Many2one('res.partner')
    destination = fields.Many2one('mission.destination')

    # ticket_cash_request########################
    issuing_ticket = fields.Selection(selection=[('yes', _('Yes')), ('no', _('No'))], default='no')
    ticket_cash_request_type = fields.Many2one('hr.ticket.request.type')
    ticket_cash_request_for = fields.Selection(selection=[('employee', _('For Employee Only')),
                                                          ('family', _('For Family Only')),
                                                          ('all', _('For Employee And Family Only'))])
    # to link with the account invoice entry
    Training_cost = fields.Float()
    appraisal_check = fields.Boolean()
    appraisal_found = fields.Boolean(compute="check_appraisal")
    Tra_cost_invo_id = fields.Many2one('account.move', string="Training Cost Invoice", readonly=True)

    max_of_employee = fields.Integer()
    min_of_employee = fields.Integer()

    employee_id = fields.Many2one('hr.employee', 'Responsible', default=lambda item: item.get_user_id(),
                                  domain=[('state', '=', 'open')])
    employee_no = fields.Char(related='employee_id.emp_no', readonly=True, string='Employee Number', store=True)
    reference = fields.Char(string="Reference Number")

    company_id = fields.Many2one('res.company', string="Company", default=lambda self: self.env.user.company_id)

    ticket_request_id = fields.Many2one('hr.ticket.request', string="Ticket Request", readonly=True)
    department_id2 = fields.Many2one(related='employee_id.department_id', readonly=True, store=True,
                                     string='Department')
    is_branch = fields.Many2one(related='department_id2.branch_name', store=True, readonly=True)
    attachment_count = fields.Integer(string="Attachments", compute="_compute_attachment_count")
    training_details = fields.Html('Training Details')
    trainer_id = fields.Many2one('res.partner', string="Trainer")
    appraisal_count = fields.Integer(string="Appraisals", compute="get_employees_appraisal")
    hr_nomination = fields.Boolean(string="HR Nomination")


    @api.depends('hour_duration', 'date_duration')
    def compute_number_of_hours(self):
        for item in self:
            # if item.hour_duration and item.date_duration:
            item.total_hours = item.hour_duration * item.date_duration




    @api.constrains('employee_ids')
    def chick_employee_ids(self):
        for item in self:
           if not item.employee_ids:
             raise exceptions.Warning(_('The Request cannot Be completed without Employees'))

    ### context process_type solve ###########
    @api.onchange('mission_type')
    def _add_process_type(self):
        if self.mission_type.work_state != 'training' and self.mission_type.special_hours != True:
            self.process_type = 'mission'
        if self.mission_type.work_state == 'training' and self.mission_type.special_hours != True:
            self.process_type = 'training'
        if self.mission_type.special_hours == True:
            self.process_type = 'especially_hours'

    @api.model
    def create(self, vals):
        if self.process_type == 'mission':
            seq = self.env['ir.sequence'].next_by_code('hr.official.mission') or '/'
            vals['reference'] = seq
        new_record = super(HrOfficialMission, self).create(vals)

        return new_record

    #########################################

    def _compute_attachment_count(self):
        attachment_data = self.env['ir.attachment'].read_group(
            [('res_model', '=', 'hr.official.mission'), ('res_id', 'in', self.ids)], ['res_id'], ['res_id'])
        attachment = dict((data['res_id'], data['res_id_count']) for data in attachment_data)
        for rec in self:
            rec.attachment_count = attachment.get(rec.id, 0) + sum(rec.employee_ids.mapped('attachment_count'))

    def action_get_attachment_view(self):
        res = self.env['ir.actions.act_window']._for_xml_id('base.action_attachment')
        related_ids = self.ids + self.employee_ids.ids
        related_models = ['hr.official.mission', 'hr.official.mission.employee']
        res['domain'] = [('res_model', 'in', related_models), ('res_id', 'in', related_ids)]
        res['context'] = {
            'default_res_model': 'hr.official.mission',
            'default_res_id': self.id,
            'create': True,
            'edit': True,
        }

        return res

    def action_add_employees(self):
        self.ensure_one()
        ctx = dict(self.env.context)
        if not self.id:
            ctx.update({
                'default_mission_vals': {
                    'name': self.name,
                }
            })
        else:
            ctx['default_official_mission_id'] = self.id

        ctx['default_employee_id'] = self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)

        return {
            'name': _('Add Employees to Mission'),
            'view_mode': 'form',
            'res_model': 'employee.mission.selection.wizard',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': ctx,
        }

    def action_training_appraisal(self):
        self.ensure_one()
        ctx = dict(self.env.context)

        return {
            'name': _('Training Course Appraisal'),
            'view_mode': 'form',
            'res_model': 'training.appraisal.wizard',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': ctx,
        }

    def get_employees_appraisal(self):
        for rec in self:
            rec.appraisal_count = 0
            employee_ids = rec.employee_ids.mapped('employee_id')
            training = rec.env['hr.employee.appraisal'].search(
                [('employee_id', 'in', employee_ids.ids), ('mission_id', '=', rec.id)])
            rec.appraisal_count = len(training)

    def action_employees_appraisal(self):
        employee_ids = self.employee_ids.mapped('employee_id')
        training = self.env['hr.employee.appraisal'].search(
            [('employee_id', 'in', employee_ids.ids), ('mission_id', '=', self.id)])
        return {
            'name': (_("Employees Appraisal")),
            'view_mode': 'tree,form',
            'view_id': False,
            'res_model': 'hr.employee.appraisal',
            'type': 'ir.actions.act_window',
            'target': 'current',
            'domain': "[('id', 'in', %s)]" % training.ids,
            'context': {}
        }

    def check_appraisal(self):
        if all(record.appraisal_id for record in self.employee_ids):
            self.appraisal_found = True
        else:
            self.appraisal_found = False

    def get_user_id(self):
        employee_id = self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)
        if employee_id:
            return employee_id.id
            self.get_line_employee()
        else:
            return False

    @api.onchange('country_id')
    def _country_id_destination(self):
        for item in self:
            item.destination = False

    @api.constrains('max_of_employee', 'min_of_employee')
    def chick_min_max(self):
        for item in self:
            if item.min_of_employee > item.max_of_employee:
                raise exceptions.Warning(
                    _('The maximum number of employees must be greater than the minimum number of employees'))
            if item.max_of_employee < 0 or item.min_of_employee < 0:
                raise exceptions.Warning(_('The Max Or Min Number Of Employees Must be Greater than Zero'))

    @api.constrains('course_name', 'employee_ids')
    def chick_course_employee(self):
        for item in self:
            if item.course_name.id >= 1:
                course_job = item.env['hr.job'].search([('course_ids', '=', item.course_name.id)]).ids
                for emp in item.employee_ids:
                    if course_job:
                        jobs = item.env['hr.job'].search(
                            [('course_ids', '=', item.course_name.id), ('id', '=', emp.employee_id.job_id.id)]).ids
                        if not jobs:
                            raise exceptions.Warning(
                                _('Employee %s, The course does not follow the career record') % emp.employee_id.name)


    @api.onchange('date_from', 'date_to', 'hour_to', 'hour_from', 'mission_type','mission_type.working_days', 'state','table_ids')
    def _get_mission_no(self):
        for item in self:

            # Initialize values
            item.date_duration, item.hour_duration = 0.0, 0.0

            # Difference of date duration
            if item.mission_type.duration_type == 'days' or item.mission_type.duration_type == 'hours':
                if item.date_from and item.date_to:
                    start_mission_date = datetime.strptime(str(item.date_from), "%Y-%m-%d")
                    end_mission_date = datetime.strptime(str(item.date_to), "%Y-%m-%d")

                    if not item.table_ids:
                        print("khgggggg")
                        if end_mission_date >= start_mission_date:
                            if not item.table_ids:
                                days = (end_mission_date - start_mission_date).days
                                item.date_duration = days + 1


                            # days = (end_mission_date - start_mission_date).days
                            # item.date_duration = days + 1
                            date_range = [start_mission_date.date() + timedelta(days=i)
                                          for i in range((end_mission_date - start_mission_date).days + 1)]

                            if item.mission_type.working_days:
                                calendar = item.company_id.resource_calendar_id
                                if not calendar:
                                    raise ValidationError(_('Company working calendar is not configured.'))

                                weekend_days = calendar.full_day_off or calendar.shift_day_off
                                weekend_names = [d.name.lower() for d in weekend_days]
                                date_range = [d for d in date_range if d.strftime('%A').lower() not in weekend_names]


                            item.date_duration = len(date_range)

                        else:
                            # item.duration = 0.0
                            raise exceptions.Warning(_('Date Form Must Be Less than Date To'))

                        if item.mission_type.maximum_days > 0.0:
                            if item.date_duration > item.mission_type.maximum_days:
                                raise exceptions.Warning(
                                    _('mission duration must be less than "%s" maximum days in mission type "%s" ') % (
                                        item.mission_type.maximum_days, item.mission_type.name))

                    else:
                        unique_dates = set(item.table_ids.mapped('date'))
                        item.date_duration = len(unique_dates)

                # Difference hour duration
                # elif item.mission_type.duration_type == 'hours':
                if item.hour_from == 0.0:
                    item.hour_duration = (item.hour_to - 0.0)
                elif item.hour_to == 0.0:
                    item.hour_duration = (23.999 - item.hour_from)
                elif item.hour_from and item.hour_to:
                    if item.hour_to > item.hour_from:
                        item.hour_duration = (item.hour_to - item.hour_from)
                    else:
                        item.hour_duration = (24 - item.hour_from) + item.hour_to

                        # raise exceptions.Warning(_('Hour to must be greater than hour from.'))
                    if item.mission_type.maximum_hours > 0.0:
                        if item.hour_duration > item.mission_type.maximum_hours:
                            item.hour_duration = 0.0
                            raise exceptions.Warning(
                                _('mission duration must be less than "%s" maximum hours in mission type "%s" ') % (
                                    item.mission_type.maximum_hours, item.mission_type.name))

            # Re-compute values for each in employee_ids line
            # ------------------------------------------------
            if item.employee_ids or not item.employee_ids:
                for line in item.employee_ids:
                    # Compute number of days and get DATE FROM and DATE TO values
                    if item.mission_type.duration_type == 'days' or item.mission_type.duration_type == 'hours':
                        if item.date_to and item.date_from:
                            line.date_from = item.date_from
                            line.date_to = item.date_to
                            leave_to = datetime.strptime(str(line.date_to), "%Y-%m-%d")
                            leave_from = datetime.strptime(str(line.date_from), "%Y-%m-%d")
                            if leave_to < leave_from:
                                raise exceptions.Warning(_('date form must be less than date to'))

                            else:
                                # dayss = (leave_to - leave_from).days
                                # line.days = dayss + 1
                                date_range = [leave_from.date() + timedelta(days=i)
                                              for i in range((leave_to - leave_from).days + 1)]

                                if item.mission_type.working_days:
                                    calendar = item.company_id.resource_calendar_id
                                    if not calendar:
                                        raise ValidationError(_('Company working calendar is not configured.'))

                                    weekend_days = calendar.full_day_off or calendar.shift_day_off
                                    weekend_names = [d.name.lower() for d in weekend_days]
                                    date_range = [d for d in date_range if
                                                  d.strftime('%A').lower() not in weekend_names]

                                if not item.table_ids:
                                    print("55555555556")
                                    line.days = len(date_range)
                                else:
                                    unique_dates = set(item.table_ids.mapped('date'))
                                    line.days = len(unique_dates)
                                print("555ooooo")
                                print(line.days)
                                if item.mission_type.related_with_financial is True:
                                    if item.mission_type.type_of_payment == 'fixed':
                                        if item.mission_type.day_price:
                                            line.day_price = item.mission_type.day_price
                                            line.amount = line.day_price * line.days
                                    # dealing with salary rules
                                    else:
                                        total = 0.0
                                        if item.mission_type.allowance_id:
                                            for rule in item.mission_type.allowance_id:
                                                if line.employee_id:
                                                    total += item.compute_rule(rule,
                                                                               line.sudo().employee_id.contract_id)
                                            line.day_price = total
                                            line.amount = total * line.days

                        # Compute number of hours and get hour_from and hour_to values
                        # elif item.mission_type.duration_type == 'hours':
                        if item.hour_to and item.hour_from:
                            line.hour_from = item.hour_from
                            line.hour_to = item.hour_to
                        elif item.hour_from == 0.0:
                            line.hour_from = 0.0
                            line.hour_to = item.hour_to
                        elif item.hour_to == 0.0:
                            line.hour_to = 23.999
                            line.hour_from = item.hour_from

                        if (line.hour_to - line.hour_from) < 0:
                            hours = (24 - line.hour_from) + line.hour_to
                            # raise exceptions.Warning(_('Number of hours to must be greater than hours from'))
                        else:
                            line.hours = (line.hour_to - line.hour_from)
                            line.total_hours = line.hours * line.days
                            print("11111111111")
                            if item.mission_type.related_with_financial is True:
                                if item.mission_type.type_of_payment == 'fixed':
                                    if item.mission_type.hour_price:
                                        line.hour_price = item.mission_type.hour_price
                                        line.amount = line.hour_price * line.hours
                                # dealing with salary rules
                                else:
                                    total = 0.0
                                    for rule in item.mission_type.allowance_id:
                                        if line.employee_id:
                                            total += item.compute_rule(rule, line.sudo().employee_id.contract_id)
                                        line.hour_price = total
                                        line.amount = total * line.hours
            self.sudo().employee_ids.chick_not_overtime()
            self.sudo().re_compute()

    def re_compute(self):
        self.employee_ids.compute_Training_cost_emp()
        self.employee_ids.compute_day_price()
        if not self.table_ids:
            self.employee_ids.compute_number_of_days()
        self.employee_ids.compute_number_of_hours()
        return True

    def draft_state(self):
        # check if the moved journal entry if un posted then canceled
        for item in self:
            # if item.employee_ids:
            if item.move_type == 'accounting':
                for line in item.employee_ids:
                    if item.state == 'approve' and line.account_move_id:
                        if line.account_move_id.state == 'draft':
                            # line.account_move_id.state = 'canceled'
                            line.account_move_id.unlink()
                            line.account_move_id = False
                        else:
                            raise exceptions.Warning(_(
                                'You can not re-draft official mission because account move with ID "%s" in state '
                                'Posted') % line.account_move_id.name)


            elif item.move_type == 'payroll':

                for record in item.employee_ids:
                    record.advantage_id.draft()
                    record.advantage_id.unlink()

            #### delete ticket_record when state not in draft
            if item.issuing_ticket == 'yes':
                for miss in item:
                    ticket_record = item.env['hr.ticket.request'].search([('mission_request_id', '=', miss.id)])
                    for tick in ticket_record:
                        if tick.state != 'draft':
                            raise exceptions.Warning(_
                                                     ('You Can Not Set To Draft Because Ticket Employee "%s" In State '
                                                      'Not Draft') % tick.employee_id.name)
                        else:
                            tick.unlink()

            #### delete Trainig Cost when state not in draft
            if item.Tra_cost_invo_id:
                if item.state == 'approve':
                    if item.Tra_cost_invo_id.state == 'draft':
                        item.Tra_cost_invo_id.unlink()
                        item.Tra_cost_invo_id = False
                    else:
                        raise exceptions.Warning(_(
                            'You can not re-draft official mission because account Invoice with ID "%s" in state Not Draft') % item.Tra_cost_invo_id.number)

            if item.mission_type.work_state == 'training' and item.appraisal_found == True:
                for line in item.employee_ids:
                    if line.appraisal_id:
                        if line.appraisal_id.state == 'draft':
                            line.appraisal_id.unlink()
                            line.appraisal_id = False
                            line.appraisal_result = 0.0
                        else:
                            raise exceptions.Warning(_(
                                'You can not re-draft official mission because Appraisal with ID "%s" in not draft state ') % line.appraisal_id.employee_id.name)

            item.state = 'draft'
            self.reset_emp_work_state()
            self.call_cron_function()

    def call_cron_function(self):
        transaction = self.env['hr.attendance.transaction']
        # if self.duration_type == 'days':
        if self.duration_type:
            if self.date_to and self.date_from:
                start_date = datetime.strptime(str(self.date_from), '%Y-%m-%d')
                end_date = datetime.strptime(str(self.date_to), "%Y-%m-%d")
                delta = end_date - start_date
                today = datetime.now().date()
                today = datetime.strptime(str(today), "%Y-%m-%d").date()
                for i in range(delta.days + 1):
                    day = start_date + timedelta(days=i)
                    if today >= day.date():
                        transaction.process_attendance_scheduler_queue(day, self.employee_ids.mapped(
                            'employee_id'))
        # else:
        # day = datetime.strptime(str(self.date), '%Y-%m-%d')
        # transaction.process_attendance_scheduler_queue(day, self.employee_ids.mapped(
        #  'employee_id'))

    def send(self):
        for item in self:
            if not item.employee_ids:
                raise exceptions.Warning(_('The Request cannot Be completed without Employees'))

            item.employee_ids.compute_Training_cost_emp()
            # item.chick_employee_ids()
            for line in item.employee_ids:
                mail_content = "Hello I'm", line.employee_id.name, " request Need to ", item.mission_type.name, "Please approved thanks."
                main_content = {
                    'subject': _('Request To %s Employee %s') % (item.mission_type.name, line.employee_id.name),
                    'author_id': self.env.user.partner_id.id,
                    'body_html': mail_content,
                    'email_to': line.employee_id.department_id.email_manager,
                }
                self.env['mail.mail'].sudo().create(main_content).send()
        
        self.employee_ids.chick_not_overtime()
        self.state = "send"

    def send_depart_manager(self):
        for item in self:
            if not item.employee_ids:
                raise exceptions.Warning(_('The Request cannot Be completed without Employees'))

            item.employee_ids.compute_Training_cost_emp()
            # item.chick_employee_ids()
            item.employee_ids.write({'status': 'direct_manager'})

        self.employee_ids.chick_not_overtime()
        if self.hr_nomination:
            self.state = "depart_manager"
        else:
            self.state = "send"

    def direct_manager(self):
        # self.chick_employee_ids()
        self.employee_ids.chick_not_overtime()
        self.employee_ids.compute_Training_cost_emp()
        self.employee_ids.write({'status': 'approved'})
        self.state = 'depart_manager'
        for rec in self:
            manager = rec.sudo().employee_id.parent_id
            hr_manager = rec.sudo().employee_id.company_id.hr_manager_id
            if manager:
                if manager.user_id.id == rec.env.uid or hr_manager.user_id.id == rec.env.uid:
                    rec.write({'state': 'depart_manager'})
                else:
                    raise exceptions.Warning(
                        _("Sorry, The Approval For The Direct Manager '%s' Only OR HR Manager!") % (manager.name))
            else:
                rec.write({'state': 'depart_manager'})
        if self.mission_type.approve_by == 'direct_manager':
            self.approve()

    # Refuse For The Direct Manager Only
    def direct_manager_refused(self):
        for rec in self:
            manager = rec.sudo().employee_id.parent_id
            hr_manager = rec.sudo().employee_id.user_id.company_id.hr_manager_id
            if manager:
                if manager.user_id.id == rec.env.uid or hr_manager.user_id.id == rec.env.uid:
                    rec.refused()
                else:
                    raise exceptions.Warning(
                        _("Sorry, The Refuse For The Direct Manager '%s' Only OR HR Manager!") % (manager.name))
            else:
                rec.refused()

    def depart_manager(self):
        self.sudo().employee_ids.chick_not_overtime()
        self.employee_ids.compute_Training_cost_emp()
        for rec in self:
            coach = rec.sudo().employee_id.coach_id
            hr_manager = rec.sudo().employee_id.user_id.company_id.hr_manager_id
            if coach:
                if coach.user_id.id == rec.env.uid or hr_manager.user_id.id == rec.env.uid:
                    rec.state = 'depart_manager'
                else:
                    raise exceptions.Warning(
                        _('Sorry, The Approval For The Department Manager %s Only OR HR Manager!') % (coach.name))
            else:
                rec.state = 'depart_manager'

    # Refuse For The Department Manager Only
    def dep_manager_refused(self):
        self.reset_emp_work_state()
        for rec in self:
            coach = rec.sudo().employee_id.coach_id
            hr_manager = rec.sudo().employee_id.user_id.company_id.hr_manager_id
            if coach:
                if coach.user_id.id == rec.env.uid or hr_manager.user_id.id == rec.env.uid:
                    rec.refused()
                else:
                    raise exceptions.Warning(
                        _('Sorry, The Refuse For The Department Manager %s Only OR HR Manager') % (coach.name))
            else:
                rec.refused()

    def hr_aaproval(self):
        # self.chick_employee_ids()
        lines_draft_status = any(self.employee_ids.filtered(lambda emp: emp.status in ('draft', 'direct_manager')))
        if lines_draft_status and self.mission_type.work_state == 'training':
            raise ValidationError(_("You must Approve all Employees Line First."))

        self.employee_ids.chick_not_overtime()
        self.employee_ids.compute_Training_cost_emp()
        self.state = "hr_aaproval"

    def get_ticket_cost(self, employee):
        for rec in self:
            class_id = employee.contract_id.ticket_class_id
            line = rec.destination.class_ids.filtered(lambda r: r.ticket_class_id == class_id)
            price = line.price if line else 0
            return price

    def approve(self):
        # check if there is dealing with financial
        self.employee_ids.chick_not_overtime()
        if self.employee_ids and self.mission_type.related_with_financial:
            # move amounts to journal entries
            if self.move_type == 'accounting':
                # if self.mission_type.account_id and self.mission_type.journal_id:
                if self.mission_type.related_with_financial == True:
                    for item in self.employee_ids:
                        emp_type = item.employee_id.employee_type_id
                        account_debit_id = self.mission_type.get_debit_mission_account_id(emp_type)
                        journal_id = self.mission_type.journal_id
                        analytic_account_id = self.mission_type.analytic_account_id
                        if not analytic_account_id:
                           analytic_account_id = item.employee_id.department_id.analytic_account_id
                 
                        if not journal_id:
                            raise exceptions.Warning(
                                _('You Must Enter The Journal Name Mission Type %s.') % self.mission_type.name)
                        if not account_debit_id:
                            raise exceptions.Warning(
                                _('Employee %s, The Mission %s Has No Account Setting Base On Employee Type.'
                                  ) % (item.employee_id.name, self.mission_type.name))
                        if item.amount > 0.0:
                            debit_line_vals = {
                                'name': item.employee_id.name + ' in official mission "%s" ' % self.mission_type.name,
                                'debit': item.amount,
                                # 'account_id': self.mission_type.account_id.id,
                                'account_id': account_debit_id.id,
                                'partner_id': item.employee_id.user_id.partner_id.id,
                                'analytic_account_id': analytic_account_id.id,
                            }
                            credit_line_vals = {
                                'name': item.employee_id.name + ' in official mission "%s" ' % self.mission_type.name,
                                'credit': item.amount,
                                'account_id': journal_id.default_account_id.id,
                                'partner_id': item.employee_id.user_id.partner_id.id
                            }
                            if not item.account_move_id:
                                move = self.env['account.move'].create({
                                    'state': 'draft',
                                    'journal_id': journal_id.id,
                                    'date': date.today(),
                                    'ref': 'Official mission for employee "%s" ' % item.employee_id.name,
                                    'line_ids': [(0, 0, debit_line_vals), (0, 0, credit_line_vals)],
                                    'res_model': 'hr.official.mission',
                                    'res_id': self.id
                                })
                                # fill account move for each employee
                                item.write({'account_move_id': move.id})
                # else:
                # raise exceptions.Warning(
                # _('You do not have account or journal in mission type "%s" ') % self.mission_type.name)

            # move amounts to advantages of employee in contract
            elif self.move_type == 'payroll':
                # get start and end date of the current month
                current_date = date.today()
                month_start = date(current_date.year, current_date.month, 1)
                month_end = date(current_date.year, current_date.month, calendar.mdays[current_date.month])
                for line in self.employee_ids:
                    if line.sudo().employee_id.contract_id:

                        advantage_arc = line.env['contract.advantage'].create({
                            'benefits_discounts': self.official_mission.id,
                            'date_from': month_start,
                            'date_to': month_end,
                            'amount': line.amount,
                            'official_mission_id': True,
                            'employee_id': line.employee_id.id,
                            'contract_advantage_id': line.sudo().employee_id.contract_id.id,
                            'out_rule': True,
                            'state': 'confirm',
                            'comments': self.mission_purpose})
                        line.advantage_id = advantage_arc.id
                    else:
                        raise exceptions.Warning(_(
                            'Employee "%s" has no contract Please create contract to add line to advantages')
                                                 % line.employee_id.name)

        for item in self:
            # create ticket request from all employee
            if item.issuing_ticket == 'yes':
                for emp in item.employee_ids:
                    ticket = self.env['hr.ticket.request'].create({
                        'employee_id': emp.employee_id.id,
                        'mission_request_id': item.id,
                        'mission_check': True,
                        'request_for': item.ticket_cash_request_for,
                        'request_type': item.ticket_cash_request_type.id,
                        'cost_of_tickets': item.get_ticket_cost(emp.employee_id),
                        'destination': item.destination.id,
                    })
                    item.write({'ticket_request_id': ticket.id})

            # move invoice  training cost our trining center
            if item.Training_cost > 0:
                invoice_line_vals = {
                    'name': 'Training Cost for Course Name %s Training Center %s' % (
                        item.course_name.name, item.partner_id.name),
                    'price_unit': item.Training_cost,
                    # 'account_id': self.mission_type.journal_id.default_credit_account_id.id,
                    'account_id': item.partner_id.property_account_payable_id.id,
                    # 'partner_id': item.employee_id.user_id.partner_id.id
                }
                invoice = self.env['account.move'].create({
                    'state': 'draft',
                    'move_type': 'in_invoice',
                    'journal_id': item.mission_type.journal_id.id,
                    'partner_id': item.partner_id.id,
                    'invoice_date': date.today(),
                    'ref': 'Training Cost for Course Name %s ' % item.course_name.name,
                    'invoice_line_ids': [(0, 0, invoice_line_vals)],
                    'res_model': 'hr.official.mission',
                    'res_id': self.id
                })
                item.write({'Tra_cost_invo_id': invoice.id})

        self.state = "approve"
        if self.mission_type.work_state and self.mission_type.duration_type == 'days':
            for emp in self.employee_ids:
                if emp.date_to >= fields.Date.today() >= emp.date_from:
                    emp.employee_id.write({'work_state': self.mission_type.work_state, 'active_mission_id': emp.id})
        self.call_cron_function()

    def refused(self):
        self.state = 'refused'
        self.reset_emp_work_state()

    def reset_emp_work_state(self):
        if self.mission_type.work_state and self.mission_type.duration_type == 'days':
            for miss in self.employee_ids:
                if miss.employee_id.active_mission_id.id == miss.id:
                    active_missions = miss.employee_id.get_employee_active_mission()
                    if active_missions and active_missions[0].id != miss.employee_id.active_mission_id.id:
                        status = active_missions[0].official_mission_id.mission_type.work_state
                        active_mission_id = active_missions[0].id
                    elif len(active_missions) > 1 and active_missions[0].id == miss.employee_id.active_mission_id.id:
                        status = active_missions[1].official_mission_id.mission_type.work_state
                        active_mission_id = active_missions[1].id
                    else:
                        status = 'work'
                        active_mission_id = False
                    miss.employee_id.write({'work_state': status, 'active_mission_id': active_mission_id})

    # Compute salary rules

    def compute_rule(self, rule, contract):
        localdict = dict(employee=contract.employee_id, contract=contract)

        if rule.amount_select == 'percentage':
            total_percent = 0
            if rule.related_benefits_discounts:
                for line in rule.related_benefits_discounts:
                    if line.amount_select == 'fix':
                        total_percent += self.compute_rule(line, contract)
                    elif line.amount_select == 'percentage':
                        total_percent += self.compute_rule(line, contract)
                    else:
                        total_percent += self.compute_rule(line, contract)
            if total_percent:
                if rule.salary_type == 'fixed':
                    try:
                        return float(total_percent * rule.amount_percentage / 100)
                    except:
                        raise UserError(
                            _('Wrong percentage base or quantity defined for salary rule %s (%s).') % (
                                rule.name, rule.code))
                elif rule.salary_type == 'related_levels':
                    levels_ids = rule.salary_amount_ids.filtered(
                        lambda item: item.salary_scale_level.id == contract.salary_level.id)
                    if levels_ids:
                        for l in levels_ids:
                            try:
                                return float(l.salary * total_percent / 100)
                            except:
                                raise UserError(
                                    _('Wrong quantity defined for salary rule %s (%s).') % (
                                        rule.name, rule.code))
                    else:
                        return 0
                elif rule.salary_type == 'related_groups':
                    groups_ids = rule.salary_amount_ids.filtered(
                        lambda item: item.salary_scale_group.id == contract.salary_group.id)
                    if groups_ids:
                        for g in groups_ids:
                            try:
                                return float(g.salary * total_percent / 100)
                            except:
                                raise UserError(
                                    _('Wrong quantity defined for salary rule %s (%s).') % (
                                        rule.name, rule.code))
                    else:
                        return 0
                elif rule.salary_type == 'related_degrees':
                    degrees_ids = rule.salary_amount_ids.filtered(
                        lambda item: item.salary_scale_degree.id == contract.salary_degree.id)
                    if degrees_ids:
                        for d in degrees_ids:
                            try:
                                return float(d.salary * total_percent / 100)
                            except:
                                raise UserError(
                                    _('Wrong quantity defined for salary rule %s (%s).') % (
                                        rule.name, rule.code))
                    else:
                        return 0
            else:
                try:
                    return 0
                except:
                    raise Warning(_('There is no total for rule : %s') % (rule.name))

        elif rule.amount_select == 'fix':
            return rule._compute_rule(localdict)[0]

        else:
            return rule._compute_rule(localdict)[0]

    def unlink(self):
        for i in self:
            if i.state != 'draft':
                raise exceptions.Warning(_('You can not delete record in state not in draft'))
            i.employee_ids.unlink()
        return super(HrOfficialMission, self).unlink()

    # chick holiday period employee

    @api.constrains('employee_ids', 'date_from', 'date_to')
    def chick_not_holiday(self):
        # TOOOO-DOOOO missons
        for rec in self:
            Module = self.env['ir.module.module'].sudo()
            modules_holidays = Module.search([('state', '=', 'installed'), ('name', '=', 'hr_holidays_public')])
            if modules_holidays:
                for emp in rec.employee_ids:
                    if emp.date_to and emp.date_from:
                        clause_1, clause_2, clause_3 = rec.get_domain(emp.date_from, emp.date_to)
                        clause_final = [('employee_id', '=', emp.employee_id.id), ('state', '!=', 'refuse'),
                                        ('type', '=', 'remove'),
                                        '|', '|'] + clause_1 + clause_2 + clause_3
                        holidays = self.env['hr.holidays'].search(clause_final)
                        if holidays:
                            for record in holidays:
                                if not record.holiday_status_id.mission_chick:
                                    raise exceptions.Warning(
                                        _('Sorry The Employee %s Actually On Holiday For this Period') % emp.employee_id.name)

    def get_domain(self, date_from, date_to):
        clause_1 = ['&', ('date_to', '<=', date_to), ('date_to', '>=', date_from)]
        clause_2 = ['&', ('date_from', '<=', date_to), ('date_from', '>=', date_from)]
        clause_3 = ['&', ('date_from', '<=', date_from), ('date_to', '>=', date_to)]
        return clause_1, clause_2, clause_3

    def convertTime(self, time):
        list = []
        for t in time:
            t = '{0:02.0f}:{1:02.0f}'.format(*divmod(float(t) * 60, 60))
            hour = datetime.strptime(str(t), "%H:%M").time()
            list.append(hour)
        return list


class OfficialMissionAttach(models.Model):
    _inherit = 'ir.attachment'

    mission_id = fields.Many2one(comodel_name='hr.official.mission')


class EmployeeCourseName(models.Model):
    _name = 'employee.course.name'
    _rec_name = 'name'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(translate=True)
    code = fields.Char()
    job_ids = fields.Many2many('hr.job', string='Jobs', readonly=False)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.user.company_id)

    def unlink(self):
        for i in self:
            training_id = self.env['hr.official.mission'].search([('course_name', '=', i.id)]).ids
            if training_id:
                raise exceptions.Warning(
                    _('You Can Not Delete Course Name, Because There is a Related Employee Training'))
        return super(EmployeeCourseName, self).unlink()


class MissionDestination(models.Model):
    _name = 'mission.destination'
    _rec_name = 'name'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(translate=True)
    code = fields.Char()
    class_ids = fields.One2many('mission.destination.line', 'destination_id', string="Ticket class")
    country_id = fields.Many2one('res.country', string='Country')
    destination_type = fields.Selection(selection=[('mission', _('Mission')),
                                                   ('training', _('Training')),
                                                   ('ticket', _('Ticket')),
                                                   ('all', _('All'))], string='Destination Type', default='all')

    def unlink(self):
        for i in self:
            mission_id = self.env['hr.official.mission'].search([('destination', '=', i.id)]).ids
            if mission_id:
                raise exceptions.Warning(
                    _('You Can Not Delete Destination Name, Because There is a Related Employee Missions'))
        return super(MissionDestination, self).unlink()


class TicketClass(models.Model):
    _name = "ticket.class"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string="Class ", required=True)

    def unlink(self):
        for i in self:
            ticket_ids = self.env['hr.contract'].search([('ticket_class_id', '=', i.id)]).ids
            if ticket_ids:
                raise exceptions.Warning(
                    _('You Can Not Delete Ticket Class, Because There is a Related Employee Contract'))
        return super(TicketClass, self).unlink()


class HrAppraisalGroup(models.Model):
    _inherit = "hr.group.employee.appraisal"

    mission_id = fields.Many2one('hr.official.mission', string="Training")

    @api.onchange('department_id', 'mission_id', 'appraisal_type')
    def employee_ids_domain(self):
        self.employee_ids = False
        if self.mission_id and self.appraisal_type in ['mission', 'training']:
            employee_list = self.mission_id.employee_ids.mapped('employee_id').ids
            return {'domain': {'employee_ids': [('id', 'in', employee_list)]}}
        else:
            res = super(HrAppraisalGroup, self).employee_ids_domain()
            return res

    @api.onchange('appraisal_type')
    def get_mission_domain(self):
        if self.appraisal_type == 'training':
            return {
                'domain': {'mission_id': [('process_type', "=", 'training')]}
            }
        else:
            return {
                'domain': {'mission_id': [('process_type', "=", 'mission')]}
            }


class HrAppraisal(models.Model):
    _inherit = "hr.employee.appraisal"

    def set_state_done(self):
        res = super(HrAppraisal, self).set_state_done()
        if self.appraisal_type == 'mission' and self.employee_appraisal.mission_id:
            mission = self.employee_appraisal.mission_id.employee_ids.sudo().filtered(
                lambda r: r.employee_id == self.employee_id)
            self.employee_appraisal.mission_id.appraisal_check = True
            if mission:
                mission.sudo().write({
                    'appraisal_id': self.id,
                    'appraisal_result': self.appraisal_result.id if self.appraisal_result else False
                })
        elif self.appraisal_type == 'training' and self.mission_id:
            mission = self.mission_id
            if mission:
                mission_employee = mission.employee_ids.sudo().filtered(
                    lambda r: r.employee_id == self.employee_id)
                mission.appraisal_check = True
                mission_employee.sudo().write({
                    'appraisal_id': self.id,
                    'appraisal_result': self.appraisal_result.id if self.appraisal_result else False
                })
        return res


class MissionDestinationLine(models.Model):
    _name = 'mission.destination.line'

    destination_id = fields.Many2one('mission.destination', string="Destination ")
    ticket_class_id = fields.Many2one('ticket.class', string="Ticket Class ", required=True)
    price = fields.Float(string="Price")


class HrOfficialMissionType(models.Model):
    _name = 'hr.official.mission.type'
    _rec_name = 'name'

    name = fields.Char(translate=True)
    mission_place = fields.Char()
    type_of_mission = fields.Selection(selection=[('internal', _('Internal')), ('external', _('External'))],
                                       default='internal')
    duration_type = fields.Selection(selection=[('days', _('Days')), ('hours', _('Hours'))], default='days')
    maximum_days = fields.Float()
    maximum_hours = fields.Float()
    related_with_financial = fields.Boolean()
    type_of_payment = fields.Selection(selection=[('fixed', _('Fixed amount')), ('allowance', _('Allowance'))],
                                       default='fixed')
    hour_price = fields.Float()
    day_price = fields.Float()

    total_months = fields.Integer('Total Periods in Months', required=True)
    max_request_number = fields.Integer('Maximum Requests', required=True)
    max_days_year = fields.Integer('Max Days Year')
    max_amount = fields.Float('Maximum Amount')

    # relational fields
    company_id = fields.Many2one('res.company', string="Company", default=lambda self: self.env.user.company_id)
    allowance_id = fields.Many2many('hr.salary.rule')
    journal_id = fields.Many2one('account.journal')
    account_id = fields.Many2one('account.account')
    analytic_account_id = fields.Many2one(comodel_name='account.analytic.account')
    work_state = fields.Selection([('work', _('In work')),
                                   ('Secondment', _('Secondment')),
                                   ('legation', _('Legation')),
                                   ('depute', _('Deputation')),
                                   ('consultation', _('Consultation')),
                                   ('emission', _('Emission')),
                                   # ('delegate', _('Delegation')),
                                   ('training', _('Training')),
                                   ('others', _('others'))], 'Work Status')
    special_hours = fields.Boolean(string='Special Hours', default=False)
    approve_by = fields.Selection([('direct_manager', 'Direct Manager'), ('depart_manager', 'HR Department')],
                                  default='direct_manager', required=True)

    transfer_by_emp_type = fields.Boolean('Transfer By Emp Type')
    account_ids = fields.One2many('hr.mission.type.account', 'mission_id')
    working_days = fields.Boolean(string='Working Days Only', default=False)

    absent_attendance = fields.Boolean(help='If there are no attendance, this day will be absent.')

    @api.onchange('duration_type')
    def _change_duration_type(self):
        for rec in self:
            if rec.duration_type == 'days':
                rec.hour_price = 0
            else:
                rec.day_price = 0

    def unlink(self):
        for i in self:
            mission_type = i.env['hr.official.mission'].search([('mission_type', '=', i.id)]).ids
            if mission_type:
                raise exceptions.Warning(_('You Can Not Delete Mission Type, Because There is a Related other record'))
        return super(HrOfficialMissionType, self).unlink()

    # get acoount IDs base on Mission Type account config
    def get_debit_mission_account_id(self, emp_type):
        if not self.transfer_by_emp_type:  return self.account_id
        account_mapping = self.account_ids.filtered(lambda a: a.emp_type_id.id == emp_type.id)
        return account_mapping[0].debit_account_id if account_mapping else False


class HrMissionTypeAccount(models.Model):
    _name = 'hr.mission.type.account'
    _description = 'Mission Type Account Mapping'

    mission_id = fields.Many2one('hr.official.mission.type', string="Mission Type", required=True, ondelete="cascade")
    emp_type_id = fields.Many2one('hr.contract.type', string="Employee Type", required=True)
    debit_account_id = fields.Many2one('account.account', string="Debit Account", required=True)


class HrOfficialMissionEmployee(models.Model):
    _name = 'hr.official.mission.employee'
    _rec_name = 'employee_id'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_from desc'

    date_from = fields.Date()
    date_to = fields.Date()
    days = fields.Integer()
    hour_from = fields.Float()
    hour_to = fields.Float()
    hours = fields.Float()
    day_price = fields.Float(readonly=True)
    hour_price = fields.Float(readonly=True)
    amount = fields.Float(readonly=True)
    fees_amount = fields.Float()

    # Relational fields
    official_mission_id = fields.Many2one('hr.official.mission', readonly=True)  # inverse field
    appraisal_id = fields.Many2one('hr.employee.appraisal')
    appraisal_result = fields.Many2one('appraisal.result')

    employee_id = fields.Many2one('hr.employee')
    account_move_id = fields.Many2one('account.move',
                                      readonly=True)  # to link with the account move line in journal entry
    state = fields.Selection(related='official_mission_id.state', default="draft", tracking=True,
                             readonly=True)
    process_type = fields.Selection(related='official_mission_id.process_type', readonly=True, store=True)
    advantage_id = fields.Many2one(comodel_name='contract.advantage', string='Allowance Employee')
    train_cost_emp = fields.Float(store=True, readonly=True, compute='compute_Training_cost_emp')
    total_hours = fields.Float()
    course_name = fields.Many2one(related='official_mission_id.course_name', readonly=True,
                                  store=True)
    attachment_count = fields.Integer(string="Attachments", compute="_compute_attachment_count")
    status = fields.Selection([('draft', _('Draft')),
                               ('direct_manager', _('Waiting Direct Manager')),
                               ('approved', _('Approved')),
                               ('done', _('Done')),
                               ('refused', _('Refused')),
                               ], default="draft", tracking=True)
    training_details = fields.Html('Training Details', related="official_mission_id.training_details")

    def approve(self):
        self.status = "approved"

    def refuse(self):
        self.status = "refused"

    def done(self):
        self.status = "done"

    def set_to_draft(self):
        self.status = "draft"

    def _compute_attachment_count(self):
        attachment_data = self.env['ir.attachment'].read_group(
            [('res_model', '=', 'hr.official.mission.employee'), ('res_id', 'in', self.ids)], ['res_id'], ['res_id'])
        attachment = dict((data['res_id'], data['res_id_count']) for data in attachment_data)
        for rec in self:
            rec.attachment_count = attachment.get(rec.id, 0)

    def action_get_attachment_view(self):
        self.ensure_one()
        res = self.env['ir.actions.act_window']._for_xml_id('base.action_attachment')
        res['domain'] = [('res_model', '=', 'hr.official.mission.employee'), ('res_id', 'in', self.ids)]
        res['context'] = {'default_res_model': 'hr.official.mission.employee', 'default_res_id': self.id}
        return res

    @api.constrains('date_from', 'date_to', 'hour_from', 'hour_to', 'employee_id')
    def check_dates(self):
        for rec in self:
            if rec.hour_from >= 24 or rec.hour_to >= 24:
                raise exceptions.ValidationError(_('Wrong Time Format.!'))
            date_from = datetime.strptime(str(rec.date_from), DEFAULT_SERVER_DATE_FORMAT).date()
            date_to = datetime.strptime(str(rec.date_to), DEFAULT_SERVER_DATE_FORMAT).date()
            delta = timedelta(days=1)
            while date_from <= date_to:
                missions_ids = rec.search([
                    ('id', '!=', rec.id), ('employee_id', '=', rec.employee_id.id),
                    ('state', '!=', 'refuse'), ('date_from', '<=', str(date_from)),
                    ('date_to', '>=', str(date_from)),
                    '|', '|',
                    '&', ('hour_from', '<=', rec.hour_from), ('hour_to', '>=', rec.hour_from),
                    '&', ('hour_from', '<=', rec.hour_to), ('hour_to', '>=', rec.hour_to),
                    '&', ('hour_from', '>=', rec.hour_from), ('hour_to', '<=', rec.hour_to),
                ])
                if missions_ids:
                    raise exceptions.ValidationError(_('Sorry The Employee %s Actually On %s For this Time') %
                                                     (rec.employee_id.name,
                                                      missions_ids.official_mission_id.mission_type.name))
                date_from += delta

    @api.constrains('employee_id', 'official_mission_id', 'date_from', 'date_to', 'hour_from', 'hour_to')
    def chick_period(self):
        for item in self:
            duplicated = self.env['hr.official.mission.employee'].search(
                [('employee_id', '=', item.employee_id.id), ('id', '!=', item.id),
                 ('official_mission_id.process_type', '=', 'training'),
                 ('official_mission_id.course_name.id', '=', item.official_mission_id.course_name.id)])
            if duplicated:
                raise exceptions.ValidationError(
                    _("Employee %s has already take this course.") % (item.employee_id.name))
            if item.official_mission_id and item.official_mission_id.mission_type.duration_type == 'days' \
                    and item.date_from and item.date_to:
                ### mission related_with_financial
                financial_missions = item.env['hr.official.mission.employee'].search(
                    [('official_mission_id.state', 'not in', ('draft', 'refuesd')),
                     ('employee_id', '=', item.employee_id.id),
                     ('official_mission_id.mission_type.related_with_financial', '=', True),
                     ('official_mission_id.mission_type.duration_type', '=', 'days'),
                     ('id', '!=', item.id)
                     ])
                days_per_year = item.official_mission_id.mission_type.max_days_year
                if days_per_year > 0.0:
                    if item.days > days_per_year:
                        raise exceptions.Warning(
                            _('Sorry The Employee %s Cannot Exceed %s Days, This Maximum Days Per year.') % (
                                item.employee_id.name, days_per_year))
                if financial_missions:
                    if days_per_year > 0:
                        number_days = item.days
                        for rec in financial_missions:
                            year_last_record = datetime.strptime(str(rec.date_from), '%Y-%m-%d').year
                            year_now_record = datetime.strptime(str(item.date_from), '%Y-%m-%d').year
                            if year_last_record == year_now_record:
                                number_days = number_days + rec.days
                                if number_days > days_per_year:
                                    raise exceptions.ValidationError(
                                        _("Sorry The Employee %s, The Number of Requests Cannot Exceed %s Maximum Days Per year.") % (
                                            rec.employee_id.name, days_per_year))
                ####

                prev_missions = item.env['hr.official.mission.employee'].search(
                    [('official_mission_id.state', '=', 'approve'),
                     ('employee_id', '=', item.employee_id.id),
                     ('official_mission_id.mission_type.id', '=', item.official_mission_id.mission_type.id),
                     ('official_mission_id.mission_type.duration_type', '=', 'days'),
                     ('id', '!=', item.id)
                     ])
                if prev_missions:
                    if item.official_mission_id.mission_type.max_request_number > 0 and \
                            len(prev_missions) > item.official_mission_id.mission_type.max_request_number:
                        raise exceptions.Warning(
                            _('Sorry the maximum allowed times for %s is %s and employee %s has already reached it.')
                            % (item.official_mission_id.mission_type.name,
                               item.official_mission_id.mission_type.max_request_number, item.employee_id.name))
                    if item.official_mission_id.mission_type.total_months > 0:
                        passed_days = 0
                        curr_days = 1 + (
                                fields.Date.from_string(item.date_to) - fields.Date.from_string(item.date_from)).days
                        for m in prev_missions:
                            if m.date_from and m.date_to:
                                passed_days += 1 + (
                                        fields.Date.from_string(m.date_to) - fields.Date.from_string(m.date_from)).days
                        if (passed_days + curr_days) > item.official_mission_id.mission_type.total_months * 30:
                            available = item.official_mission_id.mission_type.total_months * 30 - passed_days > 0 and \
                                        item.official_mission_id.mission_type.total_months * 30 - passed_days or 0
                            raise exceptions.Warning(
                                _('Sorry the total allowed Period for %s is %s months and employee %s can take up to %s '
                                  'days only '
                                  'while it currently requesting %s days.')
                                % (item.official_mission_id.mission_type.name,
                                   item.official_mission_id.mission_type.total_months, item.employee_id.name, available,
                                   curr_days))
                mx_amount = item.official_mission_id.mission_type.max_amount
                if mx_amount > 0:
                    if (item.amount - item.fees_amount) > mx_amount:
                        raise exceptions.Warning(
                            _('Sorry the maximum Amount allow for %s is %s and employee %s has Greater than '
                              'Maximum Amount.')
                            % (item.official_mission_id.mission_type.name,
                               item.official_mission_id.mission_type.max_amount,
                               item.employee_id.name))
                Module = self.env['ir.module.module'].sudo()
                modules_permission = Module.search([('state', '=', 'installed'), ('name', '=', 'employee_requests')])
                if modules_permission:
                    if item.date_from and item.date_to or item.hour_from and item.hour_to:
                        date_to = datetime.strptime(str(item.date_to), DEFAULT_SERVER_DATE_FORMAT)
                        date_from = datetime.strptime(str(item.date_from), DEFAULT_SERVER_DATE_FORMAT)
                        if date_to and date_from:
                            delta = timedelta(days=1)
                            while date_from <= date_to:
                                clause_1, clause_2, clause_3 = item.get_permission_domain(str(date_from),
                                                                                          str(date_from))
                                clause_final = [('employee_id', '=', item.employee_id.id), ('state', '!=', 'refused'),
                                                '|', '|'] + clause_1 + clause_2 + clause_3
                                permissions = self.env['hr.personal.permission'].search(clause_final)
                                if permissions:
                                    raise exceptions.Warning(
                                        _('Sorry The Employee %s Actually On Permission For this Period')
                                        % item.employee_id.name)
                                date_from += delta

    def get_permission_domain(self, date_from, date_to):
        time_min = datetime.min
        if self.hour_to < 3 or self.hour_from < 3:
            time_min = datetime(2000, 1, 1)
        hour_from = (time_min + timedelta(hours=self.hour_from) - timedelta(hours=3)).time()
        hour_to = (time_min + timedelta(hours=self.hour_to) - timedelta(hours=3)).time()

        date_from = str(
            datetime.combine(datetime.strptime(str(date_from), DEFAULT_SERVER_DATETIME_FORMAT).date(), hour_from))
        date_to = str(datetime.combine(datetime.strptime(str(date_to), DEFAULT_SERVER_DATETIME_FORMAT).date(), hour_to))
        clause_1 = ['&', ('date_from', '<=', date_from), ('date_to', '>=', date_from)]
        clause_2 = ['&', ('date_from', '<=', date_to), ('date_to', '>=', date_to)]
        clause_3 = ['&', ('date_from', '>=', date_from), ('date_to', '<=', date_to)]
        return clause_1, clause_2, clause_3

    # dynamic domain on employee_id
    @api.onchange('employee_id')
    def get_emplyee_id_domain(self):

        # reset all fields in employee_ids line
        # self.hour_from, self.hour_to, self.hour_price, self.hours, self.days, self.day_price = 0.0, 0.0, 0.0, 0.0, 0.0, 0.0
        # self.date_to, self.date_from = False, False
        # Check if employee selected once
        if self.official_mission_id.department_id:
            # for dep in self.official_mission_id.department_id:

            if self.official_mission_id.course_name and self.official_mission_id.course_name.job_ids:
                employee_id = self.env['hr.employee'].search(
                    [('department_id', 'in', self.official_mission_id.department_id.ids), ('state', '=', 'open'),
                     ('job_id', 'in', self.course_name.job_ids.ids)]).ids
            else:
                employee_id = self.env['hr.employee'].search(
                    [('department_id', 'in', self.official_mission_id.department_id.ids),
                     ('state', '=', 'open')]).ids
            if employee_id:
                for line in self.official_mission_id.employee_ids:
                    if line.employee_id:
                        if line.employee_id.id in employee_id:
                            employee_id.remove(line.employee_id.id)
                return {'domain': {'employee_id': [('id', 'in', employee_id)]}}
        else:
            if self.official_mission_id.course_name and self.official_mission_id.course_name.job_ids:
                employee_id = self.env['hr.employee'].search(
                    [('state', '=', 'open'), ('job_id', 'in', self.course_name.job_ids.ids)]).ids
            else:
                employee_id = self.env['hr.employee'].search([('state', '=', 'open')]).ids
            # if self.process_type == 'especially_hours':
            #   employee_id = self.env['hr.employee'].search([('state', '=', 'open'),('gender', '=', 'female'),('marital', '=', 'married')]).ids
            if employee_id:
                for line in self.official_mission_id.employee_ids:
                    if line.employee_id:
                        if line.employee_id.id in employee_id:
                            employee_id.remove(line.employee_id.id)
                return {'domain': {'employee_id': [('id', 'in', employee_id)]}}

    # Compute number of days and get date_from and date_to values
    @api.onchange('date_from', 'date_to', 'employee_id')
    def compute_number_of_days(self):
        for item in self:
            if item.employee_id:
                if not item.employee_id.first_hiring_date:
                    raise exceptions.Warning(
                        _('You can not Request Mission The Employee %s have Not First Hiring Date') % item.employee_id.name)
            if item.official_mission_id.date_to and item.official_mission_id.date_from:
                if item.date_to and item.date_from:
                    leave_to_1 = datetime.strptime(str(item.date_to), "%Y-%m-%d")
                    leave_from_1 = datetime.strptime(str(item.date_from), "%Y-%m-%d")
                    if leave_from_1 <= leave_to_1:
                        # item.days = (leave_to_1 - leave_from_1).days + 1
                        date_range = [leave_from_1.date() + timedelta(days=i)
                                      for i in range((leave_to_1 - leave_from_1).days + 1)]
                        if item.official_mission_id.mission_type and item.official_mission_id.mission_type.working_days:
                            calendar = item.official_mission_id.company_id.resource_calendar_id
                            if not calendar:
                                raise ValidationError(_('Company working calendar is not configured.'))

                            weekend_days = calendar.full_day_off or calendar.shift_day_off
                            weekend_names = [d.name.lower() for d in weekend_days]
                            date_range = [d for d in date_range if d.strftime('%A').lower() not in weekend_names]


                        if not item.official_mission_id.table_ids:

                            item.days = len(date_range)
                        else:

                            unique_dates = set(item.official_mission_id.table_ids.mapped('date'))
                            item.days = len(unique_dates)
                            print(item.days)
                        print(item.days)
                        # item.days = len(date_range)
                    else:
                        raise exceptions.Warning(_('Date Form Must Be Less than Date To'))
                else:
                    item.date_from = item.official_mission_id.date_from
                    item.date_to = item.official_mission_id.date_to
                    leave_to_1 = datetime.strptime(str(item.official_mission_id.date_to), "%Y-%m-%d")
                    leave_from_1 = datetime.strptime(str(item.official_mission_id.date_from), "%Y-%m-%d")
                    if leave_from_1 <= leave_to_1:
                        # item.days = (leave_to_1 - leave_from_1).days + 1
                        date_range = [leave_from_1.date() + timedelta(days=i)
                                      for i in range((leave_to_1 - leave_from_1).days + 1)]
                        if item.official_mission_id.mission_type and item.official_mission_id.mission_type.working_days:
                            calendar = item.official_mission_id.company_id.resource_calendar_id
                            if not calendar:
                                raise ValidationError(_('Company working calendar is not configured.'))

                            weekend_days = calendar.full_day_off or calendar.shift_day_off
                            weekend_names = [d.name.lower() for d in weekend_days]
                            date_range = [d for d in date_range if d.strftime('%A').lower() not in weekend_names]

                        print("pppppppp00")
                        print(date_range)
                        if not item.official_mission_id.table_ids:
                            print("55555555556")
                            item.days = len(date_range)
                        else:
                            print("kkkffld")
                            unique_dates = set(item.official_mission_id.table_ids.mapped('date'))
                            item.days = len(unique_dates)
                            print(item.days)
                        print(item.days)

                    else:
                        raise exceptions.Warning(_('Date Form Must Be Less than Date To'))

    # Compute number of hours and get hour_from and hour_to values
    @api.onchange('hour_from', 'hour_to', 'employee_id')
    def compute_number_of_hours(self):
        for item in self:
            if item.hour_from >= 24 or item.hour_to >= 24:
                raise exceptions.ValidationError(_('Wrong Time Format.!'))
            if item.official_mission_id.hour_to and item.official_mission_id.hour_from:
                if item.hour_from and item.hour_to:
                    if (item.hour_to - item.hour_from) < 0:
                        item.hours = (24 - item.hour_from) + item.hour_to
                        item.total_hours = item.hours * item.days
                        # raise exceptions.Warning(_('Number of hours to must be greater than hours from'))
                    else:
                        item.hours = (item.hour_to - item.hour_from)
                        item.total_hours = item.hours * item.days
                    print("22222222222")

                else:
                    item.hour_from = item.official_mission_id.hour_from
                    item.hour_to = item.official_mission_id.hour_to
                    if (item.hour_to - item.hour_from) < 0:
                        item.hours = (24 - item.hour_from) + item.hour_to
                        item.total_hours = item.hours * item.days
                        # raise exceptions.Warning(_('Number of hours to must be greater than hours from'))
                    else:
                        item.hours = (item.hour_to - item.hour_from)
                        item.total_hours = item.hours * item.days


                        # compute day_price , hour_price and amount

    @api.onchange('hour_from', 'hour_to', 'hours', 'date_from', 'date_to', 'days', 'employee_id', 'day_price',
                  'hour_price', 'official_mission_id', 'fees_amount')
    def compute_day_price(self):
        for item in self:
            mission_type = item.official_mission_id.mission_type
            if mission_type.related_with_financial is True:
                if mission_type.type_of_payment == 'fixed':
                    if mission_type.day_price:
                        if item.day_price and item.days and item.employee_id:
                            item.amount = item.day_price * item.days + item.fees_amount
                        else:
                            item.day_price = mission_type.day_price
                            item.amount = item.day_price * item.days + item.fees_amount
                    if mission_type.hour_price:
                        if item.hour_price and item.hours and item.employee_id:
                            item.amount = item.hour_price * item.hours + item.fees_amount
                        else:
                            item.hour_price = mission_type.hour_price
                            item.amount = item.hour_price * item.hours + item.fees_amount
                # dealing withF salary rules
                else:
                    if mission_type.duration_type == 'days':
                        if item.day_price and item.days and item.employee_id:
                            item.amount = item.day_price * item.days + item.fees_amount
                        else:
                            total = 0.0
                            for line in mission_type.allowance_id:
                                if item.employee_id:
                                    total += item.compute_rule(line, item.sudo().employee_id.contract_id)
                            if item.day_price:
                                item.amount = item.day_price * item.days + item.fees_amount
                            else:
                                item.day_price = total
                                item.amount = item.day_price * item.days + item.fees_amount

                    if mission_type.duration_type == 'hours':
                        if item.hour_price and item.hours and item.employee_id:
                            item.amount = item.hour_price * item.hours + item.fees_amount
                        else:
                            total = 0.0
                            for line in mission_type.allowance_id:
                                if item.employee_id:
                                    total += item.compute_rule(line, item.sudo().employee_id.contract_id)
                            if item.hour_price:
                                item.amount = item.hour_price * item.hours + item.fees_amount
                            else:
                                item.hour_price = total
                                item.amount = item.hour_price * item.hours + item.fees_amount

    # Compute salary rules

    def compute_rule(self, rule, contract):
        localdict = dict(employee=contract.employee_id, contract=contract)

        if rule.amount_select == 'percentage':
            total_percent = 0
            if rule.related_benefits_discounts:
                for line in rule.related_benefits_discounts:
                    if line.amount_select == 'fix':
                        total_percent += self.compute_rule(line, contract)
                    elif line.amount_select == 'percentage':
                        total_percent += self.compute_rule(line, contract)
                    else:
                        total_percent += self.compute_rule(line, contract)
            if total_percent:
                if rule.salary_type == 'fixed':
                    try:
                        return float(total_percent * rule.amount_percentage / 100)
                    except:
                        raise UserError(
                            _('Wrong percentage base or quantity defined for salary rule %s (%s).') % (
                                rule.name, rule.code))
                elif rule.salary_type == 'related_levels':
                    level_id = rule.salary_amount_ids.filtered(
                        lambda item: item.salary_scale_level.id == contract.salary_level.id)
                    if level_id:
                        try:
                            return float(level_id.salary * total_percent / 100)
                        except:
                            raise UserError(_('Wrong quantity defined for salary rule %s (%s).') % (
                                rule.name, rule.code))
                    else:
                        return 0
                elif rule.salary_type == 'related_groups':
                    group_id = rule.salary_amount_ids.filtered(
                        lambda item: item.salary_scale_group.id == contract.salary_group.id)
                    if group_id:
                        try:
                            return float(group_id.salary * total_percent / 100)
                        except:
                            raise UserError(_('Wrong quantity defined for salary rule %s (%s).') % (
                                rule.name, rule.code))
                    else:
                        return 0
                elif rule.salary_type == 'related_degrees':
                    degree_id = rule.salary_amount_ids.filtered(
                        lambda item: item.salary_scale_degree.id == contract.salary_degree.id)
                    if degree_id:
                        try:
                            return float(degree_id.salary * total_percent / 100)
                        except:
                            raise UserError(
                                _('Wrong quantity defined for salary rule %s (%s).') % (
                                    rule.name, rule.code))
                    else:
                        return 0
            else:
                try:
                    return 0
                except:
                    raise Warning(_('There is no total for rule : %s') % (rule.name))

        elif rule.amount_select == 'fix':
            return rule._compute_rule(localdict)[0]

        else:
            return rule._compute_rule(localdict)[0]

    # Compute Training cost per employee and chick employee number
    @api.depends('employee_id', 'official_mission_id')
    def compute_Training_cost_emp(self):
        for rec in self:
            if rec.official_mission_id.Training_cost > 0 or rec.official_mission_id.max_of_employee > 0 or rec.official_mission_id.min_of_employee > 0:
                number_emp = self.env['hr.official.mission.employee'].search(
                    [('official_mission_id', '=', rec.official_mission_id.id)])
                counter = 0
                for item in number_emp:
                    counter += 1
                    rec.train_cost_emp = rec.official_mission_id.Training_cost / len(number_emp)

                    if len(number_emp) > rec.official_mission_id.max_of_employee > 0:
                        raise exceptions.Warning(_('Sorry, The number of Employees Should Not Be exceeded: %s') % (
                            rec.official_mission_id.max_of_employee))
                    if len(number_emp) < rec.official_mission_id.min_of_employee and \
                            rec.official_mission_id.min_of_employee > 0:
                        raise exceptions.Warning(_('Sorry, The Number Of Employees Should Not Be Less Than: %s') % (
                            rec.official_mission_id.min_of_employee))

    @api.onchange('employee_id', 'date_from', 'date_to')
    def chick_not_overtime(self):
        for rec in self:
            Module = self.env['ir.module.module'].sudo()
            modules_req = Module.search([('state', '=', 'installed'), ('name', '=', 'employee_requests')])
            finacial = rec.official_mission_id.mission_type.related_with_financial
            delegation = rec.official_mission_id.mission_type.work_state
            if modules_req:
                # if delegation == 'legation' and finacial:
                if finacial == True:
                    if rec.date_to and rec.date_from:
                        clause_1 = ['&', ('employee_over_time_id.date_from', '<=', rec.date_from),
                                    ('employee_over_time_id.date_to', '>=', rec.date_from)]
                        clause_2 = ['&', ('employee_over_time_id.date_from', '<=', rec.date_to),
                                    ('employee_over_time_id.date_to', '>=', rec.date_to)]
                        clause_3 = ['&', ('employee_over_time_id.date_from', '>=', rec.date_from),
                                    ('employee_over_time_id.date_to', '<=', rec.date_to)]
                        overtim = self.env['line.ids.over.time'].search(
                            [('employee_id', '=', rec.employee_id.id), ('employee_over_time_id.state', '!=', 'refused'),
                             '|', '|'] + clause_1 + clause_2 + clause_3)
                        if overtim:
                            raise exceptions.Warning(
                                _('Sorry The Employee %s Actually Has Overtime Amount For this Period') % rec.employee_id.name)

    def unlink(self):
        for i in self:
            if i.state != 'draft':
                raise exceptions.Warning(_('You can not delete record in state not in draft'))
        return super(HrOfficialMissionEmployee, self).unlink()


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    training_count = fields.Integer(compute='get_employee_mission')
    mission_count = fields.Integer(compute='get_employee_mission')
    active_mission_id = fields.Many2one(comodel_name='hr.official.mission.employee', string='Active Mission')
    work_state = fields.Selection([('work', _('In work')),
                                   ('Secondment', _('Secondment')),
                                   ('legation', _('Legation')),
                                   ('depute', _('Deputation')),
                                   ('consultation', _('Consultation')),
                                   ('emission', _('Emission')),
                                   # ('delegate', _('Delegation')),
                                   ('training', _('Training')),
                                   ('others', _('others'))], 'Work Status', default='work')

    def get_employee_mission(self):
        for item in self:
            item.mission_count = 0
            item.training_count = 0
            training = item.env['hr.official.mission'].search(
                [('process_type', '=', 'training'), ('state', '=', 'approve')])
            mission = item.env['hr.official.mission'].search(
                [('process_type', '=', 'mission'), ('state', '=', 'approve')])
            for tra in training:
                for emp in tra.sudo().employee_ids:
                    if emp.sudo().employee_id.name == item.name:
                        item.training_count = len(tra)
                        return tra
            for mi in mission:
                for em in mi.sudo().employee_ids:
                    if em.sudo().employee_id.name == item.name:
                        item.mission_count = len(mi)

    def get_employee_active_mission(self):
        today = fields.Date.today()
        return self.env['hr.official.mission.employee'].search([('date_from', '<=', today),
                                                                ('date_to', '>=', today),
                                                                ('employee_id', '=', self.id),
                                                                ('official_mission_id.state', '=', 'approve'),
                                                                ('official_mission_id.mission_type.duration_type', '=',
                                                                 'days')
                                                                ], order='date_from desc')


# Hr_job
class HrJob(models.Model):
    _inherit = 'hr.job'

    course_ids = fields.Many2many('employee.course.name', string='Courses')


class HRTICKETCUSTOM(models.Model):
    _inherit = 'hr.ticket.request'

    # Relational fields
    mission_request_id = fields.Many2one('hr.official.mission')


class HrContract(models.Model):
    _inherit = 'hr.contract'

    ticket_class_id = fields.Many2one('ticket.class', string="Ticket Class ", ondelete='restrict')

    @api.model
    def contract_mail_reminder(self):
        super(HrContract, self).contract_mail_reminder()
        stateless_emps = self.env['hr.employee'].search([('state', '=', 'open'), ('work_state', '=', False)]).write(
            {'work_state': 'work'})
        today = fields.Date.today()
        tomorrow = fields.Date.from_string(today) + timedelta(days=1)
        yesterday = fields.Date.from_string(today) + timedelta(days=-1)
        emps = []
        mission = self.env['hr.official.mission.employee']
        to_start = mission.search([('date_from', '<=', today),
                                   ('date_to', '>=', today),
                                   ('official_mission_id.state', '=', 'approve'),
                                   ('official_mission_id.mission_type.duration_type', '=', 'days')])
        emps += to_start.mapped('employee_id').ids
        to_notify = mission.search([('date_to', '=', tomorrow),
                                    ('official_mission_id.state', '=', 'approve'),
                                    ('official_mission_id.mission_type.duration_type', '=', 'days')])
        emps += to_notify.mapped('employee_id').ids
        to_end = mission.search([('date_to', '=', yesterday),
                                 ('official_mission_id.state', '=', 'approve'),
                                 ('official_mission_id.mission_type.duration_type', '=', 'days')])
        emps += to_end.mapped('employee_id').ids

        for emp in list(set(emps)):
            if emp in to_start.mapped('employee_id').ids:
                emp_2start = to_start.filtered(lambda e: e.employee_id.id == emp).sorted(key='date_to')[0]
                emp_2start.employee_id.write({'work_state': emp_2start.official_mission_id.mission_type.work_state,
                                              'active_mission_id': emp_2start.id})

            if emp in to_notify.mapped('employee_id').ids:
                for rec in to_notify.filtered(lambda e: e.employee_id.id == emp):
                    work_state = _(dict(rec.official_mission_id.mission_type._fields['work_state'].selection).get(
                        rec.official_mission_id.mission_type.work_state))

                    mail_content = _("""<div>
                        <p>Dear %s,</p>
                        <br/>
                        <p>Greetings, we kindly inform you that the %s of the employee %s will end tomorrow.</p>
                        <br/>
                         <p>Best regards,</p>""") % (rec.employee_id.parent_id.name,
                                                     work_state,
                                                     rec.employee_id.name)
                    main_content = {
                        'subject': _('%s %s ending') % (rec.employee_id.name, work_state),
                        'author_id': self.env.user.company_id.partner_id.id,
                        'body_html': mail_content,
                        'email_to': rec.employee_id.parent_id.work_email,
                        'email_cc': '%s, %s' % (self.env.user.company_id.hr_email, rec.employee_id.work_email),
                        'model': self._name,
                    }
                    # self.env['mail.mail'].create(main_content).send()

            if emp in to_end.mapped('employee_id').ids:
                emp_to_end = to_end.filtered(lambda e: e.employee_id.id == emp)
                emp_rec = emp_to_end[0].employee_id
                active_missions = emp_rec.get_employee_active_mission()
                for rec in emp_to_end:
                    if rec.id == emp_rec.active_mission_id.id:
                        if active_missions and active_missions[0].id != emp_rec.active_mission_id.id:
                            status = active_missions[0].official_mission_id.mission_type.work_state
                            active_mission_id = active_missions[0].id
                        elif len(active_missions) > 1 and active_missions[0].id == emp_rec.active_mission_id.id:
                            status = active_missions[1].official_mission_id.mission_type.work_state
                            active_mission_id = active_missions[1].id
                        else:
                            status = 'work'
                            active_mission_id = False
                        emp_rec.write({'work_state': status, 'active_mission_id': active_mission_id})




class MissionTable(models.Model):
    _name = 'mission.table'
    _rec_name = 'description'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    description = fields.Char(translate=True,string='Description')

    date = fields.Date()

    hour_from = fields.Float()
    hour_to = fields.Float()
    trainer_id = fields.Many2one('res.partner', string="Trainer")
    destination_id = fields.Many2one('hr.official.mission', string="Destination ")

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        parent_id = self.env.context.get('default_destination_id')
        if parent_id:
            parent = self.env['hr.official.mission'].browse(parent_id)
            if parent and parent.hour_from:
                res['hour_from'] = parent.hour_from
                res['hour_to'] = parent.hour_to
        return res

    @api.constrains('date', 'destination_id')
    def _check_date_within_destination(self):
        for rec in self:
            if rec.destination_id and rec.date:
                date_from = rec.destination_id.date_from
                date_to = rec.destination_id.date_to
                if date_from and date_to:
                    if not (date_from <= rec.date <= date_to):
                        raise exceptions.ValidationError(
                            _("The mission date %(date)s must be between destination's date from %(date_from)s and date to %(date_to)s.",
                              date=rec.date, date_from=date_from, date_to=date_to)
                        )
