# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class HrJob(models.Model):
    _inherit = 'hr.job'

    general_experience = fields.Integer(string='General Experience', default=1)
    domain_experience = fields.Integer(string='Specialized Experience')
    domain_ids = fields.One2many('hr.job.experience.domain', 'job_id', string='Specialized Domain Experience')

    parent_job_ids = fields.Many2many('hr.job', 'rel_job_path', column1='prev_job_id', column2='parent_job_id',
                                      string='Parent Jobs')
    job_preference_ids = fields.One2many('hr.job.preference', 'job_id', string='Jobs Preference')

    payroll_group_ids = fields.Many2many('hr.payroll.structure', 'rel_job_degree', string='Salary Group',
                                         domain=[('type', '=', 'group')])
    qualification_ids = fields.One2many('hr.job.qualification', 'job_id', string='Qualifications')
    certificate_ids = fields.Many2many('qualification.specification', string='Certificates',
                                       domain=[('type', '=', 'certificate')])

    @api.constrains('domain_experience', 'domain_ids')
    def check_domain_ids(self):
        if self.domain_experience > 0 and not self.domain_ids:
            raise ValidationError(
                _('Sorry no domains of experiences set for %s .Kindly set some.') % self.name)

    @api.onchange('domain_experience')
    def _onchange_domain_experience(self):
        # TODO: review the scenario
        if self.domain_experience < 1:
            self.domain_ids = [(5, 0, 0)]

    def write(self, vals):
        res = super(HrJob, self).write(vals)
        jobs = vals.get('parent_job_ids')
        if jobs:
            prf = self.env['hr.job.preference']
            job_ids = jobs[0][2]
            prf_job_ids = self.job_preference_ids.mapped('prf_job_id').ids
            if prf_job_ids:
                invl = list(set(prf_job_ids) - set(job_ids))
                prf.search([('job_id', '=', self.id), ('prf_job_id', 'in', invl)]).unlink()
                job_ids = list(set(job_ids) - set(prf_job_ids))
            if job_ids:
                for job in job_ids:
                    prf.create({'job_id': self.id, 'prf_job_id': job})
        return res


class HrJobExperienceDomain(models.Model):
    _name = 'hr.job.experience.domain'

    job_id = fields.Many2one(comodel_name='hr.job', string='Job')
    name = fields.Char('Domain')
    experience_years = fields.Integer(string='Years of Experience', default=1)
    job_ids = fields.One2many('hr.job.experience', 'domain_id', string='Job Experiences')

    @api.constrains('experience_years', 'job_ids')
    def check_experience_years(self):
        if self.experience_years > 0 and not self.job_ids:
            raise ValidationError(
                _('Sorry no job experiences set for %s .Kindly set some.') % self.name)
        if self.experience_years > self.job_id.domain_experience:
            raise ValidationError(
                _('Sorry the experience years for %s exceeds the required specialization years.') % self.name)
        if sum(self.job_ids.mapped('years')) > self.experience_years:
            raise ValidationError(
                _('Sorry the sum of years in all jobs related to %s exceeds its years of experiences.') % self.name)


class HrJobExperience(models.Model):
    _name = 'hr.job.experience'

    domain_id = fields.Many2one('hr.job.experience.domain', string='Domain', ondelete='cascade')
    job_id = fields.Many2one('hr.job', string='Experience', required=True)
    years = fields.Integer(string='Number of Years', default=1)


class HrJobQualification(models.Model):
    _name = 'hr.job.qualification'

    job_id = fields.Many2one('hr.job', string='Job', required=True)
    specialization_id = fields.Many2one('qualification.specification', string='Specialization', required=True,
                                        domain=[('type', '=', 'qualification')])
    qualification_id = fields.Many2one('hr.qualification.name', string='Qualification', required=True)


class HrJobPreference(models.Model):
    _name = 'hr.job.preference'

    job_id = fields.Many2one('hr.job', string='Job', required=True)
    prf_job_id = fields.Many2one('hr.job', string='Job Preference', required=True)
    preference = fields.Integer(string='Preference', default=1)
