# -*- coding: utf-8 -*-

from odoo import models, fields, api, _, exceptions


class punishment(models.Model):
    _name = 'hr.punishment'
    _rec_name = 'name'
    _description = 'Punishment'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(translate=True)
    type = fields.Selection(selection=[('warning', _('Warning')),
                                       ('penalty', _('Penalty')),
                                       ('termination', _('Termination')),
                                       ('deprivation', _('Deprivation of promotion and promotion')),
                                       ], default='warning')
    punishment_type = fields.Selection(selection=[('fixed_amount', _('Fixed amount')),
                                                  ('depend_on_salary', _('Depend on salary'))])
    amount = fields.Float()
    punishment_type_amount = fields.Selection(selection=[('duration', _('Duration')),
                                                         ('percentage', _('Percentage'))])
    with_or_not_reward = fields.Selection(selection=[('with_reward', _('With reward')),
                                                     ('without_reward', _('without_reward'))])
    duration = fields.Float()
    percentage = fields.Float()

    # relational fields
    allowance = fields.Many2many('hr.salary.rule')
    termination_type = fields.Many2one('hr.termination.type')

    days_deduction = fields.Boolean('Days Deduction')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)

    @api.onchange('duration')
    def onchange_method(self):
        if self.duration > 30:
            raise exceptions.Warning(_('Please Enter duration less than 30 '))

    def unlink(self):
        for item in self:
            records1 = self.env['hr.penalty.ss'].search([(('first_time'), '=', item.id)], limit=1)
            records2 = self.env['hr.penalty.ss'].search([(('second_time'), '=', item.id)], limit=1)
            records3 = self.env['hr.penalty.ss'].search([(('third_time'), '=', item.id)], limit=1)
            records4 = self.env['hr.penalty.ss'].search([(('fourth_time'), '=', item.id)], limit=1)
            records5 = self.env['hr.penalty.ss'].search([(('fifth_time'), '=', item.id)], limit=1)

            if records1:
                raise exceptions.Warning(
                    _('You can not delete record There is a related other Penalty record %s') % records1.name)
            elif records2:
                raise exceptions.Warning(
                    _('You can not delete record There is a related other Penalty record %s') % records2.name)
            elif records3:
                raise exceptions.Warning(
                    _('You can not delete record There is a related other Penalty record %s') % records3.name)
            elif records4:
                raise exceptions.Warning(
                    _('You can not delete record There is a related other Penalty record %s') % records4.name)
            elif records5:
                raise exceptions.Warning(
                    _('You can not delete record There is a related other Penalty record %s') % records5.name)

        return super(punishment, self).unlink()
