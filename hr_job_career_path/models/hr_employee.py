# -*- coding: utf-8 -*-

import math

from odoo import models, fields, _


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    def check_job_eligibility(self, job, department=None, group=None, prom_date=None):
        if not department:
            department = self.department_id
        if not group:
            group = self.salary_group
        unmet_condition = ''
        eligible = False
        today = fields.Date.from_string(fields.Date.today())
        if job.expected_employees < 0:
            unmet_condition += _('no available vacancies') + '\n'
        if job.general_experience > 0:
            if not self.date_of_employment and not self.first_hiring_date:
                unmet_condition += _('no employment date to calculate general experience years') + '\n'
            elif job.general_experience > math.floor(self.calculate_experience(promotion_date=prom_date) / 365):
                unmet_condition += _('insufficient general experience years') + '\n'

            if job.domain_experience > math.floor(
                    self.calculate_experience(emp_job=job, experience='domain', promotion_date=prom_date) / 365):
                unmet_condition += _('insufficient domain experience') + '\n'
        if job.payroll_group_ids and group.id not in job.payroll_group_ids.ids:
            unmet_condition += _('employee degree dose not match')
        if job.department_ids and department.id not in job.department_ids.ids:
            unmet_condition += _('job not available for employee current department') + '\n'
        if job.qualification_ids:
            valid_qual = False
            for q in job.qualification_ids:
                if self.qualifiction_id.filtered(
                        lambda l: l.qualification_id == q.qualification_id and
                                  l.qualification_specification_id == q.specialization_id):
                    valid_qual = True
                    break
            if not valid_qual:
                unmet_condition += _('unmet qualification') + '\n'
        if job.certificate_ids and \
                not set(job.certificate_ids.ids).issubset(
                    self.certification_id.mapped('certification_specification_id').ids):
            unmet_condition += _('unmet certificates') + '\n'
        if job.course_ids:
            if not set(job.course_ids.ids).issubset(self.env['hr.official.mission.employee'].search([
                ('employee_id', '=', self.id),
                ('official_mission_id.state', '=', 'approve'),
                ('official_mission_id.process_type', '=', 'training')
            ]).mapped('official_mission_id.course_name').ids):
                unmet_condition += _('unmet courses') + '\n'
        if unmet_condition == '':
            eligible = True

        return {'eligible': eligible, 'unmet_condition': unmet_condition}

    def calculate_experience(self, emp_job=False, experience='general', promotion_date=None):
        today = fields.Date.from_string(fields.Date.today())
        for rec in self:
            if experience == 'general':
                employment_date = rec.date_of_employment and rec.date_of_employment or rec.first_hiring_date
                return (today - fields.Date.from_string(employment_date)).days
            elif experience == 'domain':
                if emp_job.domain_experience > 0:
                    # valid_exp = False
                    job_archive = self.env['employee.department.jobs']
                    for domain in emp_job.domain_ids:
                        domain_exp = 0
                        valid_domain = True
                        for djob in domain.job_ids:
                            job_days = 0
                            job_history = job_archive.search([('employee_id', '=', self.id),
                                                              ('new_job_id', '=', djob.job_id.id),
                                                              ('state', '=', 'approved'),
                                                              ('promotion_type', '!=', 'department')])
                            if job_history:
                                for j in job_history:
                                    date_to = j.job_date_to and fields.Date.from_string(j.job_date_to) or today
                                    job_days += abs((date_to - fields.Date.from_string(j.date)).days)
                            else:
                                if self.job_id.id == djob.job_id.id:
                                    date_to = self.joining_date and self.joining_date or self.first_hiring_date
                                    job_days += abs((today - fields.Date.from_string(date_to)).days)
                            if djob.years > math.floor(job_days / 365):
                                valid_domain = False
                                break
                            domain_exp += job_days
                        if valid_domain:
                            # valid_exp = True
                            # domain_experience = math.floor(domain_exp / 365)
                           
                            return domain_exp
                    return 0
