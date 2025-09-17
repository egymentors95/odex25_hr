# -*- coding: utf-8 -*-
import math

from odoo import models, fields, _
from odoo.exceptions import ValidationError


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    degree_date = fields.Date('Degree Joining Date')
    group_date = fields.Date('Group Joining Date')

    def calculate_experience(self, emp_job=False, experience='general', promotion_date=None):
        experience_days = super(HrEmployee, self).calculate_experience(emp_job, experience) or 0
        if experience_days and experience_days > 0:
            promotion = self.env['employee.promotions']
            prom_src = self.env['hr.payroll.promotion.setting'].search([('active', '=', True)])
            if not prom_src:
                raise ValidationError(
                    _('Sorry promotion settings are missed kindly set them first.'))
            prom_setting = prom_src[0]
            if experience == 'general':
                date_from = self.date_of_employment and self.date_of_employment or self.first_hiring_date
                date_to = promotion_date

                emp_leaves = promotion.get_leave(self, date_from, date_to, prom_setting.excluded_leave_ids.ids)
                experience_days -= sum(emp_leaves.mapped('number_of_days_temp'))

                studying_leave_ids = self.env['hr.holidays.status'].search([('studying_leave', '=', True)]).ids
                experience_days -= sum(promotion.get_leave(self, date_from, date_to, studying_leave_ids).filtered(
                    lambda l: not l.successful_completion).mapped('number_of_days_temp'))

                emp_missions = promotion.get_mission(self, date_from, date_to, ['training', 'emission', 'Secondment'])
                experience_days -= sum(emp_missions.filtered(
                    lambda m: m.include_in_experience and not m.successfully_completed or not m.include_in_experience
                ).mapped('days'))

                emp_penalties = promotion.get_violation(
                    self, date_from, date_to, None, prom_setting.excluded_penalty_ids.ids)
                experience_days -= sum(emp_penalties.mapped('deduction_days'))

                experience_days -= len(self.get_absence(date_from, date_to).ids)
                experience_days -= math.ceil(len(self.get_absence(date_from, date_to, False).ids))

            elif experience == 'domain':
                today = fields.Date.from_string(fields.Date.today())
                job_archive = self.env['employee.department.jobs']
                for domain in emp_job.domain_ids:
                    domain_exp = 0
                    valid_domain = True
                    for djob in domain.job_ids:
                        job_days = 0
                        exp_df = exp_dt = False
                        job_history = job_archive.search([('employee_id', '=', self.id),
                                                          ('new_job_id', '=', djob.job_id.id),
                                                          ('state', '=', 'approved'),
                                                          ('promotion_type', '!=', 'department')])
                        if job_history:
                            for j in job_history:
                                date_to = j.job_date_to and fields.Date.from_string(j.job_date_to) or today
                                job_days += abs((date_to - fields.Date.from_string(j.date)).days)
                                exp_dt = fields.Date.to_string(date_to)
                                exp_df = j.date
                        else:
                            if self.job_id.id == djob.job_id.id:
                                date_to = self.joining_date and self.joining_date or self.first_hiring_date
                                job_days += abs((today - fields.Date.from_string(date_to)).days)
                                exp_dt = promotion_date
                                exp_df = date_to

                        if exp_df and exp_dt:
                            job_days -= sum(promotion.get_leave(
                                self, exp_df, exp_dt, prom_setting.excluded_leave_ids.ids).mapped(
                                'number_of_days_temp'))

                            studying_leave_ids = self.env['hr.holidays.status'].search(
                                [('studying_leave', '=', True)]).ids
                            job_days -= sum(
                                promotion.get_leave(self, exp_df, exp_dt, studying_leave_ids).filtered(
                                    lambda l: not l.successful_completion).mapped('number_of_days_temp'))

                            emp_missions = promotion.get_mission(self, exp_df, exp_dt,
                                                                 ['training', 'emission', 'Secondment'])
                            job_days -= sum(emp_missions.filtered(
                                lambda m: m.include_in_experience and not m.successfully_completed \
                                          or not m.include_in_experience).mapped('days'))

                            emp_penalties = promotion.get_violation(
                                self, exp_df, exp_dt, None, prom_setting.excluded_penalty_ids.ids)
                            job_days -= sum(emp_penalties.mapped('deduction_days'))

                            job_days -= len(self.get_absence(exp_df, exp_dt).ids)
                            job_days -= math.ceil(len(self.get_absence(exp_df, exp_dt, False).ids))
                        if djob.years > math.floor(job_days / 365):
                            valid_domain = False
                            break
                        domain_exp += job_days

                    if valid_domain:
                        return domain_exp
                return 0
        return experience_days

    def get_absence(self, date_from, date_to, is_full_day=True):
        domain = [('date', '<=', date_to),
                  ('date', '>=', date_from),
                  ('employee_id', '=', self.id),
                  ('calendar_id.is_full_day', '=', is_full_day),
                  ('is_absent', '=', True)
                  ]
        return self.env['hr.attendance.transaction'].search(domain)

    def get_group_periods(self, group_id, count_days=False, promotion_type='regular'):
        periods = []
        group_arch = self.env['employee.promotions'].search([('new_group', '=', group_id),
                                                             ('employee_id', '=', self.id),
                                                             ('type', '=', promotion_type),
                                                             ('state', '=', 'approved'),
                                                             ])
        for g in group_arch:
            # date_to = g.date_to and g.date_to or fields.Date.today()
            periods.append((g.date, g.date_to and g.date_to or fields.Date.today(), g))
        if not group_arch and self.salary_group.id == group_id:
            periods.append((self.first_hiring_date, fields.Date.today()))
        if count_days:
            group_days = 0
            for period in periods:
                group_days += abs((fields.Date.from_string(period[1]) - fields.Date.from_string(period[0])).days)
            return group_days
        return periods
