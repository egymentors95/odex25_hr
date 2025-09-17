# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class HrPromotionPromotionSetting(models.Model):
    _name = 'hr.payroll.promotion.setting'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Sets governor for promoting employee"
    _order = "date_from desc, name asc, id desc"

    name = fields.Char('Name', required=True)
    date_from = fields.Date('Date From', default=lambda self: fields.Date.today(), required=True)
    date_to = fields.Date('Date To')
    active = fields.Boolean('Active', default=True)

    excluded_leave_ids = fields.Many2many('hr.holidays.status', 'setting_xcl_hol_rel', 'set_id', 'hol_id',
                                          'Excluded Leaves')
    excluded_penalty_ids = fields.Many2many('hr.punishment', 'setting_xcl_pnl_rel', 'set_id', 'hol_id',
                                            'Excluded Penalties')

    deterrent_leave_ids = fields.Many2many('hr.holidays.status', 'setting_dtr_hol_rel', 'set_id', 'hol_id',
                                           'Deterrent Leaves')
    deterrent_violation_ids = fields.Many2many('hr.penalty.ss', 'setting_dtr_vio_rel', 'set_id', 'hol_id',
                                               'Deterrent Violations')
    deterrent_evaluation_id = fields.Many2one('appraisal.result', 'Minimum Evaluation')
    deterrent_delegation_period = fields.Integer('Deterrent Delegation Period in Months')
    deterrent_penalty_ids = fields.One2many('hr.promotion.deterrent.penalty', 'setting_id',
                                            string='Deterrent Penalties')

    current_group_ids = fields.One2many('hr.promotion.current.group', 'setting_id', string='Years In The Current Group')
    previous_group_ids = fields.One2many('hr.promotion.previous.group', 'setting_id',
                                         string='Years In The Previous Groups')

    max_age = fields.Integer('Maximum Age')
    max_nominees_no = fields.Integer('Maximum Nominees')
    max_exceptional_nomination = fields.Integer('Maximum Exceptional Nominations')
    current_group_years = fields.Integer('Current Group Years')
    last_evaluation_id = fields.Many2one('appraisal.result', 'Last Evaluation Result')

    exceptional_timeframe = fields.Integer('Years Between Two Exceptional Promotions')
    regular_timeframe = fields.Integer('Years Between Exceptional And Regular Promotion')

    @api.constrains('active', 'date_from', 'date_to')
    def check_active(self):
        for rec in self:
            if self.search([('active', '=', True), ('id', '!=', rec.id)]):
                raise ValidationError(_('Sorry you cannot have more than one active setting simultaneously.'))


class HrPromotionDeterrentPenalty(models.Model):
    _name = 'hr.promotion.deterrent.penalty'

    setting_id = fields.Many2one('hr.payroll.promotion.setting', 'Setting')
    penalty_id = fields.Many2one('hr.punishment', 'Penalty', required=True)
    days = fields.Integer('Penalty Deterrent Days', required=True)
    active_years = fields.Integer('Active Years', required=True)


class HrPromotionCurrentGroup(models.Model):
    _name = 'hr.promotion.current.group'

    setting_id = fields.Many2one('hr.payroll.promotion.setting', 'Setting')
    group_id = fields.Many2one('hr.payroll.structure', 'Promotion Group', domain=[('type', '=', 'group')],
                               required=True)
    active_years = fields.Integer('Current Group Years', required=True)


class HrPromotionPreviousGroup(models.Model):
    _name = 'hr.promotion.previous.group'

    setting_id = fields.Many2one('hr.payroll.promotion.setting', 'Setting')
    group_id = fields.Many2one('hr.payroll.structure', 'Promotion Group', domain=[('type', '=', 'group')],
                               required=True)
    prv_group_no = fields.Integer('Number of Previous Groups', required=True)
    years = fields.Integer('Years Of Experience', required=True)
    total_years = fields.Boolean('Totaled Years?')
