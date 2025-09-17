from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import date, timedelta


class AuthorityDelegationLine(models.Model):
    _name = 'authority.delegation.line'

    delegation_id = fields.Many2one('authority.delegation')

    model_configuration_id = fields.Many2one('model.configuration',
                                             string="Model Configuration")
    action_id = fields.Many2one('ir.actions.act_window', string="Action")
    res_model = fields.Char('Model', related="model_configuration_id.model_id.model")


class AuthorityDelegation(models.Model):
    _name = 'authority.delegation'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Authority Delegation'

    date_from = fields.Date(default=lambda self: fields.Date.today(), string="Date From", required=True, )
    date_to = fields.Date(string="Date To", required=True, )
    state = fields.Selection(selection=[("draft", _("Draft")),
                                        ("delegator_review", _("Delegator Review")),
                                        ("direct_manager", _("Direct Manager")),
                                        ('delegate_review', _('Delegate Review')),
                                        ('hr_review', _('HR Review')),
                                        ("approved", _("Approved")),
                                        ("refused", _("Refused"))], default='draft', tracking=True)
    delegator_id = fields.Many2one(
        comodel_name='hr.employee', string='Delegator', required=True, tracking=True)
    department_delegator = fields.Many2one(related='delegator_id.department_id', readonly=True, string="Delegator Department", store=True)

    delegate_id = fields.Many2one(
        comodel_name='hr.employee', string='Delegate', required=True, tracking=True)
    department_delegate = fields.Many2one(related='delegate_id.department_id', readonly=True,string="Delegate Department", store=True)

    group_ids = fields.Many2many('res.groups', 'res_groups_delegation_rel',
                                 'delegate_id', 'group_id')
    user_group_ids = fields.Many2many('res.groups', 'res_group_delegate_rel',
                                      'delegate_id', 'group_id')
    delegation_line_ids = fields.One2many('authority.delegation.line', 'delegation_id',
                                          string="Delegation Line")
    is_delegator = fields.Boolean(compute="_compute_delegation_users" , store=True)
    is_delegate = fields.Boolean(compute="_compute_delegation_users" ,store=True)
    delegate_name = fields.Char('Delegator', compute="_compute_delegation_users")
    delegator_name = fields.Char('Delegator', compute="_compute_delegation_users")
    disallowed = fields.Boolean('Disallowed')

    comments = fields.Char(string='Comments')

    @api.depends('delegate_id', 'delegator_id')
    def _compute_delegation_users(self):
        for item in self:
            if item.delegator_id and item.delegator_id.user_id.id == item.env.user.id:
                item.is_delegator = True
            if item.delegate_id and item.delegate_id.user_id.id == item.env.user.id:
                item.is_delegate = True
            item.delegate_name = item.sudo().delegate_id.name
            item.delegator_name = item.sudo().delegator_id.name

    '''def unlink(self):
        for rec in self:
            if rec.state != 'draft':
                raise ValidationError(_('You can not delete record in state not in draft'))
        return super(AuthorityDelegation, self).unlink()'''


    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        if self.date_from > self.date_to:
            raise ValidationError(
                _('Date From must be less than or equals to Date To.'))

    @api.onchange('delegator_id', 'delegate_id')
    def onchange_delegation(self):
        self.group_ids = False
        # self.model_configuration_ids = False
        if self.delegator_id and self.delegator_id.user_id and \
                self.delegate_id and self.delegate_id.user_id:
            delegator_group_ids = self.delegator_id.user_id.groups_id.ids
            delegate_group_ids = self.delegate_id.user_id.groups_id.ids
            groups_to_assign = list(set(delegator_group_ids) - set(delegate_group_ids))
            return {'domain': {'group_ids': [('id', 'in', groups_to_assign)]}}


    def name_get(self):
        res = []
        for rec in self:
            delegate_id = rec.sudo().delegate_id.name or ''
            date_from = rec.date_from or ''
            date_to = rec.date_to or ''
            name = '%s %s => %s' % (delegate_id, date_from, date_to)
            res.append((rec.id, name))
        return res

    def assign_groups(self):
        today = date.today()
        yesterday = date.today() - timedelta(days=1)
        delegation_assign_ids = self.search([
            ('state', '=', 'approved'),
            ('date_from', '<=', today),
            ('date_to', '>=', today),
        ])
        delegation_disallow_ids = self.search([
            ('state', '=', 'approved'),
            ('date_to', '>=', yesterday),
            ('disallowed', '=', False),
        ])
        for authority_id in delegation_assign_ids:
            authority_id.write({
                'user_group_ids': [(6, 0, authority_id.delegate_id.user_id.groups_id.ids)]
            })
            authority_id.delegate_id.user_id.write({
                'groups_id': [(4, group_id.id) for group_id in authority_id.group_ids]
            })
        for authority_id in delegation_disallow_ids:
            authority_id.write({'disallowed': True})
            authority_id.delegate_id.user_id.write({
                'groups_id': [(6, 0, authority_id.user_group_ids.ids)]
            })


    def submit(self):
        self.state = "delegator_review"


    def delegator_approve(self):
        self.state = "direct_manager"


    def refuse(self):
        self.state = "refused"


    def direct_manager_approve(self):
        self.state = "delegate_review"


    def delegate_approve(self):
        self.state = "hr_review"

    def approve(self):
        self.state = "approved"
        self.assign_groups()

    def reset_to_draft(self):
        if self.state == 'approved' and self.group_ids:
            self.delegate_id.user_id.write({
                'groups_id': [(6, 0, self.user_group_ids.ids)]
            })
        self.write({'state': 'draft'})
