# -*- coding: utf-8 -*-

import datetime
from dateutil import relativedelta
from odoo import api, fields, models, _, exceptions


class ContractExtension(models.Model):
    _name = 'hr.contract.extension'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'employee_id'

    employee_id = fields.Many2one('hr.employee', string="Employee", required=True)
    employee_no = fields.Char(related='employee_id.emp_no', readonly=True,string='Employee Number', store=True)
    contract_id = fields.Many2one(related='employee_id.contract_id', store=True, string="Contract")
    department_id = fields.Many2one(related='employee_id.department_id', store=True, string="Department")
    type = fields.Selection(selection=[('extension', 'Extension'), ('end', 'Contract End'), ('confirm', 'Confirm')],
                            required=True, string="Type", tracking=True)
    state = fields.Selection(selection=[('draft', 'Draft'), ('confirm', 'wait Direct Manager'), 
                                        ('emp_confirm', 'wait Employee'),
                                        ('direct_manager', 'Wait HR Approve'), ('hr_approve', 'Approved'),
                                        ('refused', 'Refused')], required=True, string="State", default='draft',
                             tracking=True)
    date_from = fields.Date()
    date_to = fields.Date()
    old_date_from = fields.Date(compute='get_relation_field', store=True, string="Trial start")
    old_date_to = fields.Date(compute='get_relation_field', store=True, string="Trial end")
    contract_date_end = fields.Date(compute='get_relation_field', store=True, string="Contract Date end")
    end_date = fields.Date()
    comments = fields.Text(string="Comments")
    company_id = fields.Many2one(related='employee_id.company_id', string="Company")

    @api.onchange('employee_id')
    def get_relation_field(self):
        for rec in self:
            rec.old_date_from = rec.contract_id.trial_date_start
            rec.old_date_to = rec.contract_id.trial_date_end
            rec.contract_date_end = rec.contract_id.date_end
            rec.end_date = rec.contract_id.trial_date_end
            rec.date_from = False
            rec.date_to = False
            if rec.old_date_to:
                date_start = datetime.datetime.strptime(str(rec.old_date_to), '%Y-%m-%d')
                rec.date_from = rec.old_date_to
                rec.date_to = date_start + relativedelta.relativedelta(months=3)

    @api.constrains('employee_id')
    def once_request(self):
        for i in self:
            employee_id = self.env['hr.contract.extension'].search(
                [('id', '!=', i.id), ('employee_id', '=', i.employee_id.id),
                 ('state', 'not in', ('draft', 'refused'))])
            for rec in employee_id:
                if rec.type == 'extension' and i.type == 'extension':
                    raise exceptions.Warning(_('Sorry, Not possible to request Extension Form more than once'))

                if rec.type == 'confirm' and i.type == 'confirm':
                    raise exceptions.Warning(_('Sorry, Not possible to request Confirm Form more than once'))

                if rec.type == 'end' and i.type == 'end':
                    raise exceptions.Warning(_('Sorry, Not possible to request Termination Form more than once'))

                if rec.type == 'confirm' and (i.type == 'end' or i.type == 'extension'):
                    raise exceptions.Warning(_('Sorry, Not possible End Or Extension request After Confirm'))

                if rec.type == 'end' and (i.type == 'confirm' or i.type == 'extension'):
                    raise exceptions.Warning(_('Sorry, Not possible Confirm Or Extension request After End'))

            if not i.contract_id:
                raise exceptions.Warning(_('Sorry, Not possible to request Extension with Not Contract'))

    @api.constrains('date_from', 'date_to')
    def date_constrin(self):
        for item in self:
            if item.old_date_to and item.date_from:
                if item.old_date_to > item.date_from:
                    raise exceptions.Warning(_('Extension Date Form Must be Greater than Old Date To'))

            if item.date_to and item.date_from:
                if item.date_from >= item.date_to:
                    raise exceptions.Warning(_('Date Form Must be Less Than Date To'))

            date_start = datetime.datetime.strptime(str(item.date_from), '%Y-%m-%d').date()
            date_end = datetime.datetime.strptime(str(item.date_to), '%Y-%m-%d').date()
            trial_duration = relativedelta.relativedelta(date_end, date_start).months
            if trial_duration > 3:
                raise exceptions.Warning(_('The period of Extension trail duration must be not more than 3 months'))

    def confirm(self):
        for rec in self:
            rec.once_request()
            rec.state = 'confirm'

    def direct_manager(self):
        for rec in self:
            rec.once_request()
            if rec.type != 'extension':
                rec.state = 'direct_manager'
            else:
                rec.state = 'emp_confirm'

    def emp_confirm(self):
        for rec in self:
            rec.once_request()
            if rec.employee_id.user_id.id == rec.env.uid:
                rec.state = 'direct_manager'
            else:
                raise exceptions.Warning(_('Sorry, For Employee %s Confirm Only !') % (rec.employee_id.name))

    def hr_approve(self):
        for rec in self:
            rec.once_request()
            if rec.type == 'extension':
                rec.contract_id.sudo().write({
                    #'trial_date_start': rec.date_from,
                    'trial_date_end': rec.date_to
                })
            elif rec.type == 'end':
                rec.contract_id.sudo().write({
                    # 'state':'end_contract',
                    'date_end': rec.end_date
                })
            else:
                rec.contract_id.sudo().write({
                    'state': 'program_directory', })
            rec.state = 'hr_approve'

    def refused(self):
        for rec in self:
            if rec.type != 'extension' or rec.state != 'emp_confirm':
                rec.state = "refused"
            else:
                rec.state = 'confirm'

    def draft_state(self):
        for item in self:
            if item.type == 'extension':
                item.contract_id.sudo().write({
                    #'trial_date_start': item.old_date_from,
                    'trial_date_end': item.old_date_to
                })
            if item.type == 'end':
                item.contract_id.sudo().write({'date_end': item.contract_date_end})
            item.state = "draft"

    def unlink(self):
        for i in self:
            if i.state != 'draft':
                raise exceptions.Warning(_('You can not delete record in state not in draft'))
        return super(ContractExtension, self).unlink()
