# -*- coding: utf-8 -*-
from odoo import models, fields, api,_
from odoo.exceptions import ValidationError


class WorkFlowStage(models.Model):
    _name = 'workflow.stage'
    _description = 'Workflow Stage'
    _order = 'sequence'

    name = fields.Char(string="Stage Name", required=True)
    state = fields.Selection([('draft', _('Draft')),
                              ('confirm', _('confirm')),
                              ('validate', _('HR Manager')),
                              ('approved', _('WorkFlow')),
                              ('validate1', _('Done')),
                              ('refuse', _('Refused')),
                              ('cancel', _('Cancel'))], default="draft", required=True)
    holiday_status_id = fields.Many2one('hr.holidays.status')
    sequence = fields.Integer(default=1)
    group_id = fields.Many2one('res.groups', string="Users Group")
    btn_string = fields.Char(string="Button String")
    default = fields.Boolean(string="Default")

    def unlink(self):
        for rec in self:
            holiday = rec.env['hr.holidays'].sudo().search([
                ('holiday_status_id', '=', rec.holiday_status_id.id),
                ('stage_id', '=', rec.id), ('type', '=', 'remove')])
            if holiday:
                raise ValidationError(_("You can not stop Workflow or edit"))
            else:
                return super(WorkFlowStage, self).unlink()

    @api.constrains('state')
    def stop_change_used_state(self):
        for rec in self:
            holiday = rec.env['hr.holidays'].sudo().search([
                ('holiday_status_id', '=', rec.holiday_status_id.id),
                ('stage_id', '=', rec.id), ('type', '=', 'remove')])
            if holiday:
                raise ValidationError(_("You can not change used state in Workflow "))


class HolidayWorkFlow(models.Model):
    _name = 'holiday.workflow'
    _description = 'holiday Workflow '
    _rec_name = 'stage_id'
    _order = 'sequence'

    stage_id = fields.Many2one('workflow.stage', string="Stage")
    state = fields.Selection(related="stage_id.state", store=True, string="State")
    group_id = fields.Many2one('res.groups', string="Users Group")
    holiday_id = fields.Many2one('hr.holidays', string="Holiday")
    holiday_status_id = fields.Many2one('hr.holidays.status')
    approved = fields.Boolean(string="Approved")
    next = fields.Boolean(string="Next")
    sequence = fields.Integer(default=1)
    btn_string = fields.Char(string="Button String")
