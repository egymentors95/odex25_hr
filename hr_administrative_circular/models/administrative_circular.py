# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class HrAdministrativeCircular(models.Model):
    _name = 'hr.administrative.circular'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Administrative Circulars And Decisions"
    _order = "date desc, name asc, id desc"

    name = fields.Char('Name', required=True)
    responsible_id = fields.Many2one('hr.employee', 'Responsible', required=True,
                                     default=lambda e: e.get_user_id(), domain=[('state', '=', 'open')])
    date = fields.Date('Date', default=lambda self: fields.Date.today(), required=True)
    type = fields.Selection(selection=[('internal', 'Internal'),
                                       ('external', 'External')
                                       ], string='Type', default='internal', required=True)

    employee_ids = fields.Many2many('hr.employee', 'admin_emp_rel', 'admin_id', 'emp_id', 'Employees',
                                    domain=[('state', '=', 'open')])
    partner_ids = fields.Many2many('res.partner', 'admin_partner_rel', 'admin_id', 'partner_id', 'Partners')

    term_template_id = fields.Many2one('hr.terms.conditions', 'Template', domain=[('active', '=', True)])
    terms = fields.Html('Terms And Conditions')

    state = fields.Selection([('draft', 'Draft'),
                              ('hr', 'Human Resource'),
                              ('officer', 'Executive Officer'),
                              ('manager', 'Executive Manager'),
                              ('approve', 'Approved'),
                              ('send', 'Sent'),
                              ('refuse', 'Refused')], 'State', default='draft')

    company_id = fields.Many2one('res.company', string='Company',default=lambda self: self.env.company)

    def get_user_id(self):
        return self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1) or False

    @api.onchange('term_template_id')
    def _onchange_term_template_id(self):
        self.terms = self.term_template_id and self.term_template_id.description or self.terms

    @api.onchange('type')
    def _onchange_type(self):
        if not self.type:
            self.partner_ids = [(5, 0, 0)]
            self.employee_ids = [(5, 0, 0)]
        elif self.type == 'internal':
            self.partner_ids = [(5, 0, 0)]
        elif self.type == 'external':
            self.employee_ids = [(5, 0, 0)]

    def get_partners(self):
        if self.partner_ids:
            return self.partner_ids
        elif self.employee_ids:
            return self.employee_ids.mapped('user_id.partner_id')

    @api.model
    def create(self, values):
        circular = super(HrAdministrativeCircular, self).create(values)
        partners = circular.get_partners()
        if circular.responsible_id:
            partners = partners and partners + circular.responsible_id.user_id.partner_id \
                       or circular.responsible_id.user_id.partner_id
        partners += circular.create_uid.partner_id
        if partners:
            circular.with_context(passed=True).message_subscribe(partners.ids)
        return circular

    def write(self, vals):
        if vals.get('responsible_id') or vals.get('partner_ids') or vals.get('employee_ids'):
            partner_ids = [self.create_uid.partner_id.id]
            if vals.get('responsible_id'):
                partner = self.env['hr.employee'].browse([vals.get('responsible_id')]).user_id.partner_id
                if partner:
                    partner_ids.append(partner.id)
            elif self.responsible_id.user_id.partner_id:
                partner = self.responsible_id.user_id.partner_id
                if partner:
                    partner_ids.append(partner.id)
            if vals.get('partner_ids'):
                partner_ids += vals['partner_ids'][0][2]
            elif self.partner_ids:
                partner_ids += self.partner_ids.ids
            if vals.get('employee_ids'):
                partner_ids += self.env['hr.employee'].browse(vals['employee_ids'][0][2]).mapped('user_id.partner_id'
                                                                                                 ).ids
            elif self.employee_ids:
                partner_ids += self.employee_ids.mapped('user_id.partner_id').ids

            if self.message_follower_ids:
                self.message_unsubscribe(self.message_follower_ids.mapped('partner_id').ids)
            if partner_ids:
                if not self.env.context.get('passed') and not self.env.context.get('stop'):
                    self.with_context(stop=True).message_subscribe(partner_ids=list(set(partner_ids)))
        return super(HrAdministrativeCircular, self).write(vals)

    @api.constrains('terms')
    def _check_terms(self):
        if self.terms == "<p><br></p>":
            raise UserError(_('Sorry no terms has been set, kindly set them to be able to send the E-mail.'))
        if not self.partner_ids and not self.employee_ids:
            raise UserError(_('Please set recipients for the circular.'))

    def act_submit(self):
        self.write({'state': 'hr'})

    def act_hr(self):
        self.write({'state': 'approve'})

    def act_officer(self):
        self.write({'state': 'manager'})

    def act_manager(self):
        self.write({'state': 'approve'})

    def act_send(self):
        self.env.cr.execute("""DELETE FROM email_template_attachment_rel""")
        attachment_ids = self.env['ir.attachment'].search([('res_id', '=', self.id),
                                                           ('res_model', '=', 'hr.administrative.circular')]).ids
        template = self.env.ref('hr_administrative_circular.mail_circulars', False)
        template.write({'email_to': self.responsible_id.work_email,
                        'email_cc': self.env.user.company_id.hr_email, })
        template.attachment_ids = [(4, id) for id in attachment_ids]
        template.send_mail(self.id, force_send=True, raise_exception=False)
        self.write({'state': 'send'})

    def act_reset(self):
        self.write({'state': 'draft'})

    def act_refuse(self):
        self.write({'state': 'refuse'})

    def unlink(self):
        for rec in self:
            if rec.state != 'draft':
                raise ValidationError(_('Sorry you cannot delete a document is not in draft state.'))
        return super(HrAdministrativeCircular, self).unlink()


class HrTermsConditions(models.Model):
    _name = 'hr.terms.conditions'

    name = fields.Char('Name')
    description = fields.Html('Description')
    active = fields.Boolean('Active', default=True)
