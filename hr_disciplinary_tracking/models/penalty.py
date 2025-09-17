# -*- coding:utf-8 -*-
from odoo import models, fields, api, _, exceptions


class penalty(models.Model):
    _name = "hr.penalty.ss"
    _rec_name = 'name'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(translate=True)
    have_penalty = fields.Boolean()
    code = fields.Char()
    penalty_name = fields.Many2one('hr.penalty.name')

    # relational fields
    first_time = fields.Many2many('hr.punishment', 'punishment_first_tim')
    second_time = fields.Many2many('hr.punishment', 'punishment_second_time')
    third_time = fields.Many2many('hr.punishment', 'punishment_third_time')
    fourth_time = fields.Many2many('hr.punishment', 'punishment_fourth_time')
    fifth_time = fields.Many2many('hr.punishment', 'punishment_fifth_time')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)

    @api.model
    def create(self, vals):
        seq = self.env['ir.sequence'].next_by_code('hr.penalty.ss') or '/'
        vals['code'] = seq
        return super(penalty, self).create(vals)

    def unlink(self):
        for item in self:
            records = self.env['hr.penalty.register'].search([('penalty_id', '=', item.id)])
            if records:
                raise exceptions.Warning(_
                      ('You Can Not Delete Record There is a related Penalty Employee Name %s') % records.employee_id.name)
        return super(penalty, self).unlink()


class penaltyName(models.Model):
    _name = "hr.penalty.name"

    name = fields.Char(translate=True)
