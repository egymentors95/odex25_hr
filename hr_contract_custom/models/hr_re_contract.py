# -*- coding: utf-8 -*-

from odoo import models, fields, _, exceptions, api
import datetime
from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT


class hr_extend(models.Model):
    _name = 'hr.re.contract'
    _rec_name = 'employee_id'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    state = fields.Selection(string='State', selection=[
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('direct_manager', 'Direct Manager'),
        ('hr_manager', 'HR Manager'),
        ('done', 'Re-Contract'),
        ('refuse', 'Refuse'),
    ], default='draft', tracking=True)

    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.user.company_id)
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True)
    date = fields.Date(default=fields.Date.context_today, string="Date Request")
    effective_date = fields.Date()
    job_id = fields.Many2one('hr.job', string='Job Position', compute='_get_employee_data', store=True)
    department_id = fields.Many2one('hr.department', string='Department', compute='_get_employee_data', store=True)

    hire_date = fields.Date(string='Hire Date', compute='_get_employee_data', store=True)
    contract_id = fields.Many2one('hr.contract', compute='_get_employee_data', store=True, string='Current Contract',
                                  help='Latest contract of the employee')

    new_salary = fields.Float()
    start_date = fields.Date(string='Current Contract Start Date', compute='_get_employee_data', store=True)
    new_contract_start_date = fields.Date()
    new_contract_end_date = fields.Date()
    eoc_date = fields.Date(string='Current Contract End Date', compute='_get_employee_data', store=True)
    increase_salary = fields.Selection([('no', 'NO'), ('yes', 'YES')], string='Increase Salary?', default='no')
    last_renewal = fields.Boolean(readonly=True, string='Last Renewal?', default=True)

    contract_type = fields.Selection([('temporary', _('Temporary')), ('permanent', _('Permanent'))],
                                     _('Contract Type'), default='temporary', tracking=True)

    iqama_end_date = fields.Date(related="employee_id.iqama_number.expiry_date",string='Identity End Date', readonly=True)

    # employee_type = fields.Selection(related='employee_id.contract_id.contract_description', store=True)

    def action_refuse(self):
        for item in self:
            if item.state == 'done':
                contracts = self.env['hr.contract'].search([('employee_id', '=', self.employee_id.id)],
                                                           order='id DESC')[:2]
                item.contract_id.write({
                    'salary': item.contract_id.salary_degree.base_salary,
                    'salary_scale': item.contract_id.salary_scale.id,
                    'salary_level': item.contract_id.salary_level.id,
                    'salary_group': item.contract_id.salary_group.id,
                    'salary_degree': item.contract_id.salary_degree.id, })
        self.state = "refuse"

    def action_submit(self):
        self._get_employee_data()
        self.state = 'submitted'

    def action_direct_manager(self):
        # if self.employee_id.parent_id and self._uid != self.employee_id.parent_id.user_id.id:
        #    raise exceptions.Warning(_('This is Not Your Role beacuse Your Direct Manager'))
        self._get_employee_data()
        self._check_contract()
        self.state = "direct_manager"

    def action_hr_manager(self):
        self._get_employee_data()
        self.state = "hr_manager"

    def action_done(self):
        self._check_contract()
        today = datetime.now().date()
        str_today = today.strftime('%Y-%m-%d')
        # if str_today != self.effective_date:
        # raise exceptions.Warning(_('You can not re-contract employee because effective date is not today'))
        last_record = self.env['hr.re.contract'].search(
            [('id', '!=', self.id), ('employee_id', '=', self.employee_id.id),
             ('state', '=', 'done'), ('last_renewal', '=', True)], order='id desc', limit=1)
        default = {
            'job_id': self.job_id.id,
            'employee_id': self.employee_id.id,
            'department_id': self.department_id.id,
            # 'date_start': self.new_contract_start_date,
            'date_end': self.new_contract_end_date,
            'name': 'Re-Contract' + self.employee_id.name,
            'state': 'program_directory',
        }
        if self.increase_salary == 'yes':

            default.update({'wage': self.new_salary_degree.base_salary,
                            'salary_scale': self.new_salary_scale.id,
                            'salary_level': self.new_salary_level.id,
                            # 'experience_year': self.experience_year,
                            'salary_group': self.new_salary_group.id,
                            'salary_degree': self.new_salary_degree.id,
                            })

        else:
            default.update({'wage': self.contract_id.salary_degree.base_salary,
                            'salary_scale': self.contract_id.salary_scale.id,
                            'salary_level': self.contract_id.salary_level.id,
                            'experience_year': self.contract_id.experience_year,
                            'salary_group': self.contract_id.salary_group.id,
                            'salary_degree': self.contract_id.salary_degree.id,
                            })

        c_id = self.contract_id.copy(default=default)

        for line in self.contract_id.employee_dependant:
            line.contract_id = c_id.id

        for line in self.contract_id.advantages:
            line.contract_advantage_id = c_id.id

        self.contract_id.write({'active': False})
        if last_record:
            last_record.last_renewal = False
        if self.contract_type == 'permanent':
            c_id.contract_description = 'permanent'
        # Employee back to service
        self.employee_id.state = 'open'
        self.contract_id.state = 'program_directory'

        self.state = "done"

    def unlink(self):
        for i in self:
            if i.state != 'draft':
                raise exceptions.Warning(_('You can not delete record in state not in draft'))
        return super(hr_extend, self).unlink()

    @api.onchange('employee_id', 'new_contract_start_date', 'contract_type')
    def onchange_new_contract_start_date(self):
        for rec in self:
            if rec.eoc_date:
                rec.new_contract_start_date = False
                rec.new_contract_end_date = False
                date_start = datetime.strptime(str(rec.eoc_date), '%Y-%m-%d')
                date_start += relativedelta(days=1)
                rec.new_contract_start_date = date_start
                # rec.new_contract_end_date = date_start + relativedelta(years=3)
            if not rec.eoc_date and rec.employee_id:
                raise exceptions.Warning(_('You can not renewal contract is open Date'))
            if rec.new_contract_start_date:
                start_date = datetime.strptime(str(rec.new_contract_start_date), DEFAULT_SERVER_DATE_FORMAT).date()
                end_date = start_date + relativedelta(years=1)
                end_date -= relativedelta(days=1)
                rec.new_contract_end_date = end_date
            if rec.contract_type == 'permanent':
                rec.new_contract_end_date = False

    def _check_contract(self):
        old_start_date = datetime.strptime(str(self.contract_id.date_start), DEFAULT_SERVER_DATE_FORMAT).date()
        # old_end_date = datetime.strptime(self.contract_id.date_end, DEFAULT_SERVER_DATE_FORMAT).date()
        new_start_date = datetime.strptime(str(self.new_contract_start_date), DEFAULT_SERVER_DATE_FORMAT).date()

        if self.contract_id.date_end:
            old_end_date = datetime.strptime(str(self.contract_id.date_end), DEFAULT_SERVER_DATE_FORMAT).date()
            if new_start_date <= old_end_date:
                raise exceptions.Warning(_('New Contract must have start date after the end date of old contract'))
            elif old_start_date <= new_start_date <= old_end_date:
                raise exceptions.Warning(_('New Contract must have start date after the end date of old contract'))

        if self.new_contract_end_date:
            new_end_date = datetime.strptime(str(self.new_contract_end_date), DEFAULT_SERVER_DATE_FORMAT).date()

            if new_start_date >= new_end_date:
                raise exceptions.Warning(_('New Contract start date must be before the end date'))

        return True

    def action_set_to_draft(self):
        if self.state == 'done':
            last_record = self.env['hr.re.contract'].search(
                [('id', '!=', self.id), ('employee_id', '=', self.employee_id.id),
                 ('state', '=', 'done'), ('last_renewal', '=', False)], order='id desc', limit=1)

            if self.last_renewal == False:
                raise exceptions.Warning(_('The record Cannot be Set To Draft Because It Is Not Last Renewal Record'))
            for line in self.employee_id.contract_id.advantages:
                line.contract_advantage_id = self.contract_id.id
            for line in self.employee_id.contract_id.employee_dependant:
                line.contract_id = self.contract_id.id
            contracts = self.env['hr.contract'].search([('employee_id', '=', self.employee_id.id)], order='id DESC')[:2]
            if self.contract_id:
                self.contract_id.write({'active': True})
                contracts.draft_state()
                contracts.unlink()
            if last_record:
                last_record.last_renewal = True
        self.state = "draft"
