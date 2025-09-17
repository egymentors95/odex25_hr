# -*- coding: utf-8 -*-

from dateutil.relativedelta import relativedelta

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class HrPromotionNomination(models.Model):
    _name = 'hr.payroll.nomination'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Nominate employee for annual raises and promotions"
    _order = "date desc, name asc, id desc"

    name = fields.Char('Name', required=True)
    date = fields.Date('Date', default=lambda self: fields.Date.today(), required=True)
    process = fields.Selection(selection=[('raise', 'Annual Raise'),
                                          ('promotion', 'Promotion')
                                          ], string='Process', required=True)
    approval = fields.Selection(selection=[('individual', 'Individual'),
                                           ('congregational', 'Congregational')
                                           ], string='Approval Mode', required=True)

    scale_ids = fields.Many2many('hr.payroll.structure', 'nomination_scale_rel', 'nom_id', 'scl_id', 'Scales',
                                 domain=[('type', '=', 'scale')])
    level_ids = fields.Many2many('hr.payroll.structure', 'nomination_level_rel', 'nom_id', 'lvl_id', 'Levels',
                                 domain=[('type', '=', 'level')])
    group_ids = fields.Many2many('hr.payroll.structure', 'nomination_group_rel', 'nom_id', 'grp_id', 'Groups',
                                 domain=[('type', '=', 'group')])
    degree_ids = fields.Many2many('hr.payroll.structure', 'nomination_degree_rel', 'nom_id', 'dgr_id', 'Degrees',
                                  domain=[('type', '=', 'degree')])

    raise_nominee_ids = fields.One2many('hr.payroll.raise', 'nomination_id', string='Nominees')
    margin = fields.Integer('Raise Time Margin')

    promotion_nominee_ids = fields.One2many('employee.promotions', 'nomination_id', string='Nominees')
    promotion_date = fields.Date('Promotion Consideration Date', required=False)

    state = fields.Selection([('draft', 'Draft'),
                              ('nominate', 'Nominated'),
                              ('approve', 'Approved'),
                              ('refuse', 'Refused')], 'State', default='draft')

    @api.onchange('process')
    def _onchange_process(self):
        if not self.process:
            self.with_context(permit_dlt=True).raise_nominee_ids = [(5, 0, 0)]
        elif self.process == 'promotion':
            self.with_context(permit_dlt=True).raise_nominee_ids = [(5, 0, 0)]

    def check_raise_nominee(self):
        for rec in self:
            if rec.approval == 'congregational': continue
            approve = True
            count_refuse = 0
            for nominee in rec.raise_nominee_ids:
                if nominee.state == 'refuse':
                    count_refuse += 1
                if nominee.state not in ('approve', 'refuse'):
                    approve = False
                    break
            if approve and count_refuse == len(rec.raise_nominee_ids.ids):
                rec.state = 'refuse'
            elif approve:
                rec.state = 'approve'
            else:
                rec.state = 'nominate'

    def change_promotion_nomination_state(self):
        for rec in self:
            if rec.approval == 'congregational': continue
            approve = True
            for nominee in rec.promotion_nominee_ids:
                if nominee.state != 'approved':
                    approve = False
                    break
            if approve:
                rec.state = 'approve'
            else:
                rec.state = 'nominate'

    def act_nominate(self):
        domain = [('state', '=', 'open')]
        if self.scale_ids:
            domain += [('salary_scale', 'in', self.scale_ids.ids)]
        if self.level_ids:
            domain += [('salary_level', 'in', self.level_ids.ids)]
        if self.group_ids:
            domain += [('salary_group', 'in', self.group_ids.ids)]
        if self.degree_ids:
            domain += [('salary_degree', 'in', self.degree_ids.ids)]
        emps = self.env['hr.employee'].search(domain)
        if self.process == 'raise':
            self.raise_nomination(emps)
        elif self.process == 'promotion':
            self.promotion_nomination(emps)

        self.state = 'nominate'

    def raise_nomination(self, emps):
        if self.raise_nominee_ids:
            self.with_context(permit_dlt=True).raise_nominee_ids = [(5, 0, 0)]
        degrees = emps.mapped('salary_degree')
        structure = self.env['hr.payroll.structure']
        nominees_list = []
        for d in degrees:
            nxt_degree = structure.search(
                [('salary_scale_level_id', '=', d.salary_scale_level_id.id),
                 ('salary_scale_group_id', '=', d.salary_scale_group_id.id),
                 ('salary_scale_id', '=', d.salary_scale_id.id),
                 ('sequence', '>', d.sequence),
                 ], order="sequence", limit=1)
            if not nxt_degree: continue
            deg_emps = emps.filtered(lambda e: e.salary_degree.id == d.id)
            for emp in deg_emps:
                if not (emp.salary_scale and emp.salary_level and emp.salary_group and emp.salary_degree): continue
                raise_dt = emp.degree_date and emp.degree_date or emp.first_hiring_date
                if raise_dt and emp.degree_date:
                    ndate = fields.Date.from_string(raise_dt) + relativedelta(
                        days=emp.salary_degree.time_margin) or False
                    # self.next_raise_date = ndate
                    nominees_list.append((0, 0, {'employee_id': emp.id,
                                                 'scale_id': emp.salary_scale.id,
                                                 'level_id': emp.salary_level.id,
                                                 'group_id': emp.salary_group.id,
                                                 'degree_id': emp.salary_degree.id,
                                                 'application_date': self.date,
                                                 'margin': self.margin,
                                                 'raise_type': 'annual',
                                                 'last_raise_date': emp.degree_date and emp.degree_date or False,
                                                 'next_raise_date': ndate,
                                                 'nominated_degree_id': nxt_degree.id,
                                                 }))
        self.write({'raise_nominee_ids': nominees_list})
        for nominee in self.raise_nominee_ids:
            if nominee.deviation + self.margin < 0:
                self.write({'raise_nominee_ids': [(2, nominee.id)]})

    def promotion_nomination(self, emps):
        structure = self.env['hr.payroll.structure']
        promotion = self.env['employee.promotions']
        groups = emps.mapped('salary_group')
        # print('############groups#########',groups)
        for rec in self:
            dt = fields.Date.from_string(rec.date) - relativedelta(days=1)
            df = dt - relativedelta(years=1)

            rec.with_context(permit_dlt=True).promotion_nominee_ids = [(5, 0, 0)]
            for group in groups:
                promoted_group = []
                promotion_group = structure.search([('salary_scale_level_id', '=', group.salary_scale_level_id.id),
                                                    ('salary_scale_id', '=', group.salary_scale_id.id),
                                                    ('type', '=', 'group'),
                                                    ('sequence', '>', group.sequence),
                                                    ], order="sequence", limit=1)
                if not promotion_group: continue
                promotion_degree = structure.search(
                    [('salary_scale_level_id', '=', promotion_group.salary_scale_level_id.id),
                     ('salary_scale_group_id', '=', promotion_group.id),
                     ('salary_scale_id', '=', promotion_group.salary_scale_id.id),
                     ('type', '=', 'degree'),
                     ], order="sequence", limit=1)
                if not promotion_degree: continue
                group_emps = emps.filtered(lambda e: e.salary_group.id == group.id)
                for emp in group_emps:
                    if emp.job_id.parent_job_ids:
                        promotion_job = emp.job_id.job_preference_ids.sorted(key='preference')[0].prf_job_id.id
                    else:
                        promotion_job = False
                    try:
                        emp_promotion = promotion.create({
                            'employee_id': emp.id,
                            'date': rec.date,
                            'date_promotion': rec.promotion_date,
                            'promotion_scale_id': promotion_group.salary_scale_id.id,
                            'new_level': promotion_group.salary_scale_level_id.id,
                            'new_group': promotion_group.id,
                            'new_degree': promotion_degree.id,
                            'promotion_job_id': promotion_job,
                            'type': 'regular',
                            'old_scale': emp.salary_scale.id,
                            'old_level_2': emp.salary_level.id,
                            'old_group_2': emp.salary_group.id,
                            'old_degree_2': emp.salary_degree.id,
                            'current_job_id': emp.job_id.id,
                            'nomination_id': rec.id,
                        })
                        emp_promotion._onchange_check_eligibility()
                        if not emp_promotion.eligible:
                            emp_promotion.promotion_job_id = emp.job_id.id
                            emp_promotion._onchange_check_eligibility()
                            if emp_promotion.eligible:
                                emp_promotion.promotion_job_id = False
                                promoted_group.append(emp_promotion)
                            else:
                                emp_promotion.with_context(permit_dlt=True).unlink()
                        else:
                            promoted_group.append(emp_promotion)
                    except:
                        dlt = promotion.search([('nomination_id', '=', rec.id), ('employee_id', '=', emp.id)])
                        if dlt in promoted_group:
                            promoted_group.remove(dlt)
                        dlt.with_context(permit_dlt=True).unlink()

                prometed_emp_ids = [p.employee_id.id for p in promoted_group] or [0]
                # print('##########prometed_emp_ids###########',prometed_emp_ids,promoted_group)
                # Todo: make sure one appraisal line per emp
                self.env.cr.execute("""
                    SELECT 
                      hr_employee.id, 
                      hr_employee_appraisal.level_achieved_percentage, 
                      hr_employee.first_hiring_date, 
                      hr_employee_appraisal.state
                    FROM 
                      public.hr_employee LEFT JOIN
                      public.hr_employee_appraisal
                    ON 
                      hr_employee_appraisal.employee_id = hr_employee.id
                    WHERE
                      hr_employee_appraisal.state = 'closed' AND
                      hr_employee_appraisal.appraisal_type = 'performance' AND
                      hr_employee_appraisal.appraisal_date >= %s AND
                      hr_employee_appraisal.appraisal_date <= %s AND
                      hr_employee.id IN %s
                    ORDER BY  hr_employee_appraisal.level_achieved desc, hr_employee.first_hiring_date asc
                        """, (df, dt, tuple(prometed_emp_ids)))
                appraisals = self.env.cr.dictfetchall()
                counter = 0
                seniorized_emps = []
                if appraisals:
                    for apr in appraisals:
                        counter += 1
                        for l in promoted_group:
                            if l.employee_id.id == apr['id']:
                                seniorized_emps.append(apr['id'])
                                l.promotion_seniority = counter
                promoted_emps = self.env['employee.promotions']
                for pr in promoted_group:
                    promoted_emps += pr
                if seniorized_emps:
                    for ns in promoted_emps:
                        if ns.employee_id.id in seniorized_emps:
                            promoted_emps -= ns
                if promoted_emps:
                    for emp in promoted_emps.mapped('employee_id').sorted(key='first_hiring_date'):
                        counter += 1
                        promoted_emps.filtered(lambda p: p.employee_id.id == emp.id).promotion_seniority = counter

    def act_approve(self):
        for rec in self:
            if rec.process == 'raise':
                for nominee in rec.raise_nominee_ids:
                    nominee.act_approve()
            else:
                for nominee in rec.promotion_nominee_ids:
                    nominee.approved()
            rec.state = 'approve'

    def act_refuse(self):
        for rec in self:
            if rec.approval == 'individual':
                if rec.process == 'raise':
                    if rec.raise_nominee_ids.filtered(lambda n: n.state not in ('draft', 'refuse')):
                        raise ValidationError(_('You can not refuse this record some of the nominees gone under approval.'))
                    else:
                        for nominee in rec.raise_nominee_ids:
                            nominee.act_refuse()
                        rec.state = 'refuse'
                else:
                    if rec.promotion_nominee_ids.filtered(lambda n: n.state not in ('draft', 'refuse')):
                        raise ValidationError(
                            _('You can not refuse this record some of the nominees gone under approval.'))
                    else:
                        for nominee in rec.promotion_nominee_ids:
                            nominee.act_refuse()
                        rec.state = 'refuse'
            else:
                if rec.process == 'raise':
                    for nominee in rec.raise_nominee_ids:
                        nominee.act_refuse()
                    rec.state = 'refuse'
                else:
                    for nominee in rec.promotion_nominee_ids:
                        nominee.act_refuse()
                    rec.state = 'refuse'

    def act_reset(self):
        for rec in self:
            if rec.process == 'raise':
                if rec.raise_nominee_ids.filtered(lambda n: n.state not in ('draft', 'refuse')):
                    raise ValidationError(_('You can not Set Draft this record some of the nominees Not in Draft.'))

                else:
                    for nominee in rec.raise_nominee_ids:
                        nominee.act_reset()
                        nominee.unlink()

            else:
                if rec.promotion_nominee_ids.filtered(lambda n: n.state not in ('draft', 'refuse')):
                    raise ValidationError(_('You can not Set Draft this record some of the nominees Not in Draft.'))

                else:
                    for nominee in rec.promotion_nominee_ids:
                        nominee.re_draft()
                        nominee.unlink()
        rec.state = 'draft'

    def unlink(self):
        for rec in self:
            if rec.state != 'draft':
                raise UserError(_('Sorry you can not delete a record that is not in draft state'))
            if rec.approval != 'congregational' and rec.promotion_nominee_ids.filtered(lambda n: n.state != 'draft'):
                raise ValidationError(
                    _('You can not delete this record some of the nominees are under approval.'))
        return super(HrPromotionNomination, self).unlink()


class HrPayrollRaise(models.Model):
    _inherit = 'hr.payroll.raise'

    nomination_id = fields.Many2one('hr.payroll.nomination', 'Nomination', ondelete='cascade')


class EmployeePromotions(models.Model):
    _inherit = 'employee.promotions'

    nomination_id = fields.Many2one('hr.payroll.nomination', 'Nomination', ondelete='cascade')
