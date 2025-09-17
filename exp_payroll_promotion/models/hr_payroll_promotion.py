# -*- coding: utf-8 -*-

from datetime import date, datetime, timedelta

from dateutil.relativedelta import relativedelta

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class EmployeePromotions(models.Model):
    _inherit = 'employee.promotions'

    promotion_scale_id = fields.Many2one('hr.payroll.structure', string='Promotion Scale',
                                         domain=[('type', '=', 'scale')])
    current_job_id = fields.Many2one('hr.job', string='Current Job')
    promotion_job_id = fields.Many2one('hr.job', string='Promotion Job')

    date_promotion = fields.Date('Consideration Date', default=lambda self: fields.Date.today(), required=True)
    type = fields.Selection(selection=[('regular', 'Regular'),
                                       ('exceptional', 'Exceptional')
                                       ], string='Promotion Type', default='regular', required=True)

    eligible = fields.Boolean(string='Eligible', default=False)
    unmet_condition = fields.Text(string='Unmet Conditions')
    permit = fields.Boolean(string='Permit Promotion')
    foreign_scale = fields.Boolean(string='Foreign Scale/ Level')

    date_to = fields.Date('Date To')
    changed_job_id = fields.Many2one('employee.department.jobs', string='Changed Job', ondelete='set null')

    promotion_seniority = fields.Integer('Promotion Seniority', default=0)

    last_promotion = fields.Boolean(string='Last Promotion', default=True, readonly=True)
    old_promotion_date = fields.Date(string='Old Promotion Date', readonly=True)

    service_year = fields.Integer(compute='_compute_duration')
    service_month = fields.Integer(compute='_compute_duration')
    service_day = fields.Integer(compute='_compute_duration')

    current_salary = fields.Float(store=True, force_save=True)
    new_salary = fields.Float(store=True, force_save=True)

    old_basic_salary = fields.Float(store=True, force_save=True)

    new_basic_salary = fields.Float()

    @api.onchange('employee_id')
    def store_level_group_and_degree_values(self):
        super(EmployeePromotions, self).store_level_group_and_degree_values()
        self.current_job_id = self.employee_id.job_id.id
        self.promotion_scale_id = self.old_scale
        self.old_promotion_date = self.employee_id.group_date
        self.current_salary = self.employee_id.contract_id.total_allowance
        self.old_basic_salary = self.employee_id.contract_id.salary

    @api.onchange('new_degree')
    def _new_basic_salary(self):
        for rec in self:
            if rec.new_degree:
               rec.new_basic_salary = rec.sudo().new_degree.base_salary

    @api.constrains('new_basic_salary')
    def check_new_basic_salary(self):
        if self.new_basic_salary < 0:
            raise ValidationError(_('Sorry, The Amount Of Basic Salary It Must be Greater than Zero'))

    @api.depends('date', 'old_promotion_date')
    def _compute_duration(self):
        self.service_year = False
        self.service_month = False
        self.service_day = False
        if self.old_promotion_date and self.date:
            date_start = datetime.strptime(str(self.old_promotion_date), '%Y-%m-%d').date()
            date_end = datetime.strptime(str(self.date), '%Y-%m-%d').date()
            self.service_year = relativedelta(date_end, date_start).years
            self.service_month = relativedelta(date_end, date_start).months
            self.service_day = relativedelta(date_end, date_start).days
        elif self.employee_id.first_hiring_date and self.date:
            date_start = datetime.strptime(str(self.employee_id.first_hiring_date), '%Y-%m-%d').date()
            date_end = datetime.strptime(str(self.date), '%Y-%m-%d').date()
            self.service_year = relativedelta(date_end, date_start).years
            self.service_month = relativedelta(date_end, date_start).months
            self.service_day = relativedelta(date_end, date_start).days

    @api.onchange('new_level', 'employee_id')
    def _get_new_level_and_new_group_domain(self):
        if not self.foreign_scale and \
                (self.promotion_scale_id and self.old_scale and self.new_level and self.old_level_2) and \
                (self.promotion_scale_id != self.old_scale or self.new_level != self.old_level_2):
            raise ValidationError(
                _('To promote employee to a different level please check foreign Scale/ Level box.'))
        return super(EmployeePromotions, self)._get_new_level_and_new_group_domain()

    @api.onchange('promotion_scale_id')
    def _onchange_promotion_scale(self):
        for rec in self:
            if not rec.foreign_scale and \
                    (rec.promotion_scale_id and rec.old_scale) and (rec.promotion_scale_id != rec.old_scale):
                raise ValidationError(
                    _('To promote employee to a different scale please check foreign Scale/ Level box.'))
            if rec.promotion_scale_id:
                rec.new_level = False
                return {'domain': {'new_level':
                                       [('salary_scale_id', '=', rec.promotion_scale_id.id), ('type', '=', 'level')]}}
            else:
                return {'domain': {'new_level': [('id', 'in', [])]}}

    @api.onchange('employee_id', 'promotion_scale_id', 'new_level', 'new_group', 'new_degree',
                  'type', 'promotion_job_id', 'date_promotion')
    def _onchange_check_eligibility(self):
        for rec in self:
            if not rec.employee_id or not rec.promotion_scale_id or not rec.date_promotion or not rec.type \
                    or not rec.current_job_id or not rec.new_level or not rec.new_group or not rec.new_degree \
                    or not rec.old_scale or not rec.old_level_2 or not rec.old_group_2 or not rec.old_degree_2:
                return
            deterrent_conditions = self.check_deterrents()

            emp_job = rec.promotion_job_id or rec.employee_id.job_id
            unmet_condition = rec.employee_id.check_job_eligibility(
                job=emp_job, group=rec.new_group, prom_date=rec.date_promotion)

            constrained_group = ''
            current_group_years = rec.employee_id.get_group_periods(rec.employee_id.salary_group.id, True) / 365
            current_group = self.env['hr.promotion.current.group'].search(
                [('group_id', '=', rec.employee_id.salary_group.id)])
            if current_group:
                if current_group_years < current_group[0].active_years:
                    constrained_group += 'Insufficient years in the current group' + '\n'
            prv_group = self.env['hr.promotion.previous.group'].search([('group_id', '=', rec.new_group.id)])
            if prv_group:
                prv_groups = self.env['hr.payroll.structure'].search([
                    ('salary_scale_level_id', '=', self.new_level.id),
                    ('salary_scale_id', '=', rec.promotion_scale_id.id),
                    ('sequence', '<', rec.new_group.sequence),
                    ('type', '=', 'group')], order='sequence desc', limit=prv_group[0].prv_group_no)
                all_group_days = 0
                for grp in prv_groups:
                    g_days = rec.employee_id.get_group_periods(grp.id, True)
                    if prv_group[0].total_years:
                        all_group_days += g_days
                    elif not prv_group[0].total_years and (g_days / 365) < prv_group[0].years:
                        constrained_group += 'Insufficient years in the previous group' + '\n'
                        break
                if prv_group[0].total_years and (all_group_days / 365) < prv_group[0].years:
                    constrained_group += 'Insufficient years in the previous group' + '\n'

            if rec.type == 'exceptional':
                prom_src = self.env['hr.payroll.promotion.setting'].search([('active', '=', True)])
                if not prom_src:
                    raise ValidationError(
                        _('Sorry promotion settings are missed kindly set them first.'))
                prom_setting = prom_src[0]
                if prom_setting.max_age and ((fields.Date.from_string(rec.date_promotion) -
                                              fields.Date.from_string(
                                                  rec.employee_id.birthday)).days / 365) > prom_setting.max_age:
                    constrained_group += 'Exceeds Maximum age for Exceptional promotion' + '\n'
                if prom_setting.last_evaluation_id:
                    emp_evaluation = self.get_evaluation(
                        rec.employee_id, fields.Date.from_string(rec.date_promotion) - relativedelta(years=1),
                        rec.date_promotion)
                    if emp_evaluation and emp_evaluation.appraisal_result.id not in \
                            self.env['appraisal.result'].search(
                                [('result_from', '>=', prom_setting.deterrent_evaluation_id.result_from)]).ids:
                        constrained_group += 'Unmet Evaluation for exceptional promotion' + '\n'
                if prom_setting.current_group_years and current_group_years < prom_setting.current_group_years:
                    constrained_group += 'Insufficient years in the previous group for exceptional promotion' + '\n'
                if prom_setting.max_exceptional_nomination:
                    exceptional_proms = rec.employee_id.get_group_periods(rec.employee_id.salary_group.id, False,
                                                                          'exceptional')
                    exceptional_prom_list = []
                    for xp in exceptional_proms:
                        if len(xp) == 3 and xp[2] not in exceptional_prom_list: exceptional_prom_list.append(xp[2])
                    if len(exceptional_prom_list) >= prom_setting.max_exceptional_nomination:
                        constrained_group += 'Reached the maximum number of exceptional promotions for employee' + '\n'
                if prom_setting.max_nominees_no and rec.date:
                    df = date(fields.Date.from_string(rec.date).year, 1, 1)
                    dt = date(date.today().year, 12, 31)
                    exp_promotions = self.search([('employee_id', '!=', rec.employee_id.id),
                                                  ('date', '<=', dt),
                                                  ('date', '>=', df),
                                                  ('state', '=', 'approved'),
                                                  ('type', '=', 'exceptional')
                                                  ])
                    if exp_promotions and prom_setting.max_nominees_no >= len(exp_promotions.ids):
                        constrained_group += 'Reached the maximum number for exceptional promotions nominees ' + '\n'
            rec.unmet_condition = deterrent_conditions + unmet_condition['unmet_condition'] + constrained_group
            if deterrent_conditions or unmet_condition['unmet_condition'] or constrained_group:
                rec.eligible = False
            else:
                rec.eligible = True

    def check_deterrents(self):
        prom_src = self.env['hr.payroll.promotion.setting'].search([('active', '=', True)])
        if not prom_src:
            raise ValidationError(
                _('Sorry promotion settings are missed kindly set them first.'))
        prom_setting = prom_src[0]
        unmet_condition = ''
        for rec in self:
            emp_missions = self.get_mission(
                rec.employee_id, rec.date_promotion, rec.date_promotion, ['training', 'emission'])
            for mission in emp_missions:
                if mission.days / 30 >= prom_setting.deterrent_delegation_period:
                    unmet_condition += 'Active Deterrent Emission/ Training' + '\n'
                    break

            emp_leaves = self.get_leave(
                rec.employee_id, rec.date_promotion, rec.date_promotion, prom_setting.deterrent_leave_ids.ids)
            if emp_leaves:
                unmet_condition += 'Active Deterrent Leave' + '\n'

            emp_violations = self.get_violation(
                rec.employee_id, rec.date_promotion, rec.date_promotion, prom_setting.deterrent_violation_ids.ids)
            if emp_violations:
                unmet_condition += 'Active Deterrent Violation' + '\n'

            penalty_dt = fields.Date.from_string(rec.date_promotion) - relativedelta(days=1)
            for pn in prom_setting.deterrent_penalty_ids:
                penalty_df = penalty_dt - relativedelta(years=pn.active_years)
                emp_penalties = self.get_violation(
                    rec.employee_id, fields.Date.to_string(penalty_df), fields.Date.to_string(penalty_dt), None,
                    [pn.penalty_id.id])
                days = sum(emp_penalties.mapped('deduction_days'))
                if days >= pn.days:
                    unmet_condition += 'Deterrent Penalty' + '\n'
                    break

            emp_evaluation = self.get_evaluation(rec.employee_id, penalty_dt - relativedelta(years=1), penalty_dt)
            if emp_evaluation and emp_evaluation.appraisal_result.id not in self.env['appraisal.result'].search(
                    [('result_from', '>=', prom_setting.deterrent_evaluation_id.result_from)]).ids:
                unmet_condition += 'Deterrent Evaluation' + '\n'
        return unmet_condition

    def get_mission(self, emp, date_from, date_to, work_state=None):
        domain = [('date_from', '<=', date_to),
                  ('date_to', '>=', date_from),
                  ('employee_id', '=', emp.id),
                  ('official_mission_id.state', '=', 'approve'),
                  ('official_mission_id.mission_type.duration_type', '=', 'days')
                  ]
        if work_state:
            domain += [('official_mission_id.mission_type.work_state', 'in', work_state)]
        return self.env['hr.official.mission.employee'].search(domain)

    def get_leave(self, emp, date_from, date_to, leave_ids=None):
        domain = [('date_from', '<=', date_to),
                  ('date_to', '>=', date_from),
                  ('employee_id', '=', emp.id),
                  ('state', '=', 'validate1'),
                  ('type', '=', 'remove')
                  ]
        if leave_ids:
            domain += [('holiday_status_id', 'in', leave_ids)]
        return self.env['hr.holidays'].search(domain)

    def get_violation(self, emp, date_from, date_to, violation_ids=None, punishment_ids=None):
        domain = [('start_date', '<=', date_to),
                  ('end_date', '>=', date_from),
                  ('employee_id', '=', emp.id),
                  ('state', '=', 'done'),
                  ]
        if violation_ids:
            domain += [('penalty_id', 'in', violation_ids)]
        emp_violations = self.env['hr.penalty.register'].search(domain)
        if punishment_ids:
            vio = self.env['hr.penalty.register']
            for p in punishment_ids:
                vio += emp_violations.filtered(lambda v: p in v.punishment_id.ids)
            return vio
        return emp_violations

    def get_evaluation(self, emp, date_from, date_to):
        domain = [('appraisal_date', '<=', date_to),
                  ('appraisal_date', '>=', date_from),
                  ('employee_id', '=', emp.id),
                  ('appraisal_type', '=', 'performance'),
                  ('state', '=', 'closed'),
                  ('is_manager', '=', False)
                  ]
        return self.env['hr.employee.appraisal'].search(domain, order="appraisal_date desc", limit=1)

    @api.constrains('promotion_scale_id', 'new_level', 'new_group')
    def check_validity(self):
        for rec in self:
            if not rec.old_scale or not rec.old_level_2 or not rec.old_group_2 or not rec.old_degree_2:
                raise ValidationError(_('Please make sure current scale details are complete.'))

            if not rec.foreign_scale and rec.promotion_scale_id != rec.old_scale:
                raise ValidationError(
                    _('To promote employee to a different scale please check foreign Scale/ Level box.'))

            if not rec.foreign_scale and self.new_level != self.old_level_2:
                raise ValidationError(
                    _('To promote employee to a different level please check foreign Scale/ Level box.'))

            if not rec.current_job_id:
                raise ValidationError(_('Please make sure employee has a current job.'))

            if not rec.foreign_scale:
                if rec.new_group.sequence <= rec.old_group_2.sequence:
                    raise ValidationError(_('Sorry you can promote employee to the higher group only.'))
                if rec.type == 'regular' and rec.new_group.sequence > rec.old_group_2.sequence + 1:
                    raise ValidationError(_('Sorry you can not promote employee more than one group with a regular'
                                            ' promotion, please choose exceptional promotion to do so.'))

    @api.constrains('state', 'date')
    def check_permission(self):
        prom_src = self.env['hr.payroll.promotion.setting'].search([('active', '=', True)])
        if not prom_src:
            raise ValidationError(
                _('Sorry promotion settings are missed kindly set them first.'))
        prom_setting = prom_src[0]
        for rec in self:
            if rec.state != 'draft' and not rec.eligible and not rec.permit:
                raise ValidationError(_('Sorry employee %s is not eligible, that you can not proceed with '
                                        'approval without granting him a permission to be nominated.')
                                      % rec.employee_id.name)
            if prom_setting.regular_timeframe or prom_setting.exceptional_timeframe:
                emp_xcp_prom = self.search([('employee_id', '=', rec.employee_id.id),
                                            ('state', '=', 'approved'),
                                            ('type', '=', 'exceptional'),
                                            ('id', '!=', rec.id),
                                            ], order='date desc', limit=1)
                if emp_xcp_prom:
                    gab = relativedelta(
                        fields.Date.from_string(rec.date), fields.Date.from_string(emp_xcp_prom.date)).years
                    if prom_setting.regular_timeframe and prom_setting.regular_timeframe > gab:
                        raise ValidationError(
                            _('Sorry employee %s last exceptional promotion was in %s you can not promote '
                              'him before %s years.')
                            % (rec.employee_id.name, emp_xcp_prom.date, prom_setting.regular_timeframe))
                    if prom_setting.exceptional_timeframe and prom_setting.exceptional_timeframe > gab:
                        raise ValidationError(_('Sorry employee %s last exceptional promotion was in %s you can not'
                                                ' promote him another exceptional promotion before %s years.') %
                                              (rec.employee_id.name, emp_xcp_prom.date,
                                               prom_setting.exceptional_timeframe))
            emp_last_prom = self.search([('employee_id', '=', rec.employee_id.id),
                                         ('state', '=', 'approved'),
                                         ('id', '!=', rec.id),
                                         ], order='date desc', limit=1)
            if emp_last_prom and not self.env.context.get('pass_constraint', False) and \
                    fields.Date.from_string(rec.date).year == fields.Date.from_string(emp_last_prom.date).year:
                raise ValidationError(_('Sorry you can not promote employee more than once within the same year.'))

    def approved(self):
        for rec in self:
            basic_salary=0.0
            if rec.new_basic_salary > 0:
               basic_salary = rec.new_basic_salary
            else:
               basic_salary = rec.new_degree.base_salary

            rec.employee_id.contract_id.write({
                'salary_scale': rec.promotion_scale_id.id,
                'salary_level': rec.new_level.id,
                'salary_group': rec.new_group.id,
                'salary_degree': rec.new_degree.id,
                #'salary': rec.new_degree.base_salary,
                #'salary_insurnce': rec.new_degree.base_salary,
                'salary': basic_salary,
                'salary_insurnce': basic_salary,

            })
            rec.employee_id.write({
                'group_date': rec.date,
                'degree_date': rec.date,
            })
            if rec.promotion_job_id:
                job_arc = self.env['employee.department.jobs'].create({'employee_id': rec.employee_id.id,
                                                                       'promotion_type': 'job',
                                                                       'new_job_id': rec.promotion_job_id.id,
                                                                       'date': rec.date})
                job_arc.store_level_group_and_degree_values()
                job_arc.onchange_check_eligibility()
                if not job_arc.eligible:
                    job_arc.permit = True
                job_arc.confirm()
                #job_arc.hr_officer()
                job_arc.approved()
                rec.changed_job_id = job_arc.id

            prv_promotion = self.search([('employee_id', '=', rec.employee_id.id),
                                         ('date', '<', rec.date),
                                         ('id', '!=', rec.id),
                                         ('state', '=', 'approved'),
                                         ], order='date desc', limit=1)
            if prv_promotion:
                prv_promotion.date_to = fields.Date.to_string(fields.Date.from_string(rec.date) - timedelta(days=1))
                prv_promotion.last_promotion = False
            rec.state = 'approved'
            #TOOODOOO  new_salary to be Calculate in function
            rec.new_salary = self.employee_id.contract_id.total_allowance

    def re_draft(self):
        for rec in self:
            if rec.last_promotion == False:
                raise ValidationError(_('Sorry you can not set to Draft this Not last Promotion'))
            rec.employee_id.contract_id.write({
                'salary_scale': rec.old_scale.id,
                'salary_level': rec.old_level_2.id,
                'salary_group': rec.old_group_2.id,
                'salary_degree': rec.old_degree_2.id,
                #'salary': rec.old_degree_2.base_salary,
                #'salary_insurnce': rec.old_degree_2.base_salary,
                'salary': rec.old_basic_salary,
                'salary_insurnce': rec.old_basic_salary,
            })
            promotion_date = False
            prv_promotion = self.search([('employee_id', '=', rec.employee_id.id),
                                         ('id', '!=', rec.id),
                                         ('promotion_scale_id', '=', rec.old_scale.id),
                                         # ('new_level', '=', rec.old_level_2.id),
                                         # ('new_group', '=', rec.old_group_2.id),
                                         # ('new_degree', '=', rec.old_degree_2.id),
                                         ('state', '=', 'approved'),
                                         ], order='date desc', limit=1)
            if prv_promotion:
                prv_promotion.date_to = False
                promotion_date = prv_promotion.date
                prv_promotion.last_promotion = True
            rec.employee_id.write({
                'group_date': promotion_date,
                'degree_date': promotion_date,
            })
            if rec.changed_job_id:
                rec.changed_job_id.draft()
                rec.changed_job_id.unlink()
            rec.with_context(pass_constraint=True).state = 'draft'

    def unlink(self):
        # for rec in self:
        #   if rec.state == 'draft' and rec.nomination_id and not self.env.context.get('permit_dlt', False):
        # raise ValidationError(_('Sorry you can not delete nomination record'))
        return super(EmployeePromotions, self).unlink()

    def write(self, vals):
        res = super(EmployeePromotions, self).write(vals)
        if 'state' in vals:
            for rec in self:
                if rec.nomination_id: rec.nomination_id.change_promotion_nomination_state()

    '''# dynamic domain to get new level and new group domain
    
    @api.onchange('promotion_scale_id')
    def _get_new_level_and_new_group_domain(self):
        for item in self:
            if item.promotion_scale_id:
                #item.new_group = False
                #item.new_degree = False
                level_ids = self.env['hr.payroll.structure'].search(
                    [('salary_scale_id', '=', item.promotion_scale_id.id), ('type', '=', 'level')])
                group_ids = self.env['hr.payroll.structure'].search(
                    [('salary_scale_id', '=', item.promotion_scale_id.id), ('type', '=', 'group')])
                degree_ids = self.env['hr.payroll.structure'].search(
                    [('salary_scale_id', '=', item.promotion_scale_id.id), ('type', '=', 'degree')])
                domain = {'new_level': [('id', 'in', level_ids.ids)],
                          'new_group': [('id', 'in', group_ids.ids)],
                          'new_degree': [('id', 'in', degree_ids.ids)]}
                return {'domain': domain}
            else:
                domain = {'new_level': [('id', 'in', [])],
                          'new_group': [('id', 'in', [])],
                          'new_degree': [('id', 'in', [])]}
                return {'domain': domain}

    # filter depend on salary_level
    
    @api.onchange('new_level')
    def onchange_salary_level(self):
        for item in self:
            if item.new_level:
                group_ids = self.env['hr.payroll.structure'].search(
                    [('salary_scale_level_id', '=', item.new_level.id), ('type', '=', 'group')])
                return {'domain': {'new_group': [('id', 'in', group_ids.ids)],
                                   'new_degree': [('id', 'in', [])]}}
            else:
                return {'domain': {'new_group': [('id', 'in', [])],
                                   'new_degree': [('id', 'in', [])]}}

    # dynamic domain to get new degree domain
    
    @api.onchange('new_group')
    def _get_new_degree_domain(self):
        for item in self:
            if item.new_group:
                #item.new_degree = False
                degree_ids = self.env['hr.payroll.structure'].search(
                    [('salary_scale_group_id', '=', item.new_group.id), ('type', '=', 'degree')])
                domain = {'new_degree': [('id', 'in', degree_ids.ids)]}
                return {'domain': domain}
            else:
                domain = {'new_degree': [('id', 'in', [])]}
                return {'domain': domain}'''
