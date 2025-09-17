# -*- coding: utf-8 -*-

from odoo import models, fields, api, _, exceptions
from odoo.exceptions import ValidationError
from lxml import etree


class HRHolidays(models.Model):
    _inherit = 'hr.holidays'

    double_validation = fields.Boolean(related="holiday_status_id.double_validation", store=True)
    stage_id = fields.Many2one('workflow.stage', string="Stage", domain="[('id','in',stage_ids)]")
    workflow_ids = fields.Many2many('holiday.workflow', string="Workflow", )
    user_id = fields.Many2one('res.users', string='User', default=lambda self: self.env.user)
    show_button = fields.Boolean(string="Show Button", compute="show_button_workflow")
    btn_string = fields.Char(string="Button String")
    stage_ids = fields.Many2many('workflow.stage')

    @api.model
    def update_holiday_no_validation(self):
        holiday = self.env['hr.holidays'].sudo().search([('double_validation', '=', False)])
        for holi in holiday:
            holi.change_state()
            holi.stage_ids = self.env['workflow.stage'].search([('default', '=', True)]).ids

    def get_default_draft_stage(self):
        if self.holiday_status_id and self.type == 'remove':
            draft = self.workflow_ids.filtered(lambda r: r.stage_id.state == 'draft').mapped('stage_id')
            self.stage_id = draft.id if draft and len(draft) == 1 else False

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        res = super(HRHolidays, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar,
                                                      submenu=submenu)
        if 'params' in self._context:
            arch = etree.XML(res['arch'])
            if view_type == 'form':
                if 'id' in self._context['params'] and 'model' in self._context['params'] \
                        and self._context['params']['model'] == 'hr.holidays':
                    holiday = self.env['hr.holidays'].browse(self._context['params']['id'])
                    if holiday and holiday.type == 'remove':
                        path = arch.xpath("//button[@name='approved']")
                        for x in path:
                            if holiday.btn_string:
                                x.set('string', holiday.btn_string)
                            else:
                                if self._context['lang'] != 'ar_SY':
                                    x.set('string', 'Approve')
                                else:
                                    x.set('string', 'موافقة')
                        res['arch'] = etree.tostring(arch)
        return res

    @api.constrains('stage_id', 'state')
    def check_workflow_ids(self):
        if self.double_validation and self.type == 'remove' and not self.workflow_ids:
            raise ValidationError(_("Check workflow of this holiday"))

    @api.onchange('holiday_status_id')
    def get_workflow_data(self):
        self.stage_ids = False
        if not self.double_validation:
            self.stage_id = self.env.ref('hr_holidays_workflow.workflow_stage_draft').id
            self.stage_ids = self.env['workflow.stage'].search([('default', '=', True)]).ids
        elif self.type != 'add':
            if self.holiday_status_id and self.type == 'remove' and not self.holiday_status_id.workflow_ids and \
                    self.double_validation:
                raise ValidationError(_("Config workflow first"))
            if self.double_validation and self.holiday_status_id and self.type == 'remove' and \
                    self.holiday_status_id.workflow_ids:
                if self.workflow_ids:
                    self.workflow_ids = False
                list = []
                for rec in self.holiday_status_id.workflow_ids:
                    list.append((0, 0, {
                        'stage_id': rec.id,
                        'group_id': rec.group_id.id,
                        'sequence': rec.sequence,
                        'btn_string': rec.btn_string,
                    }))
                self.workflow_ids = list
                self.stage_ids = self.workflow_ids.mapped('stage_id')
                self.get_default_draft_stage()

    def show_button_workflow(self):
        for rec in self:
            show_button = False
            if not rec.check_state and rec.workflow_ids and rec.type == 'remove':
                approve = rec.workflow_ids.sudo().filtered(
                    lambda r: r.stage_id.state == 'approved' and not r.approved)
                if approve:
                    if approve[0].group_id.id in rec.env.user.groups_id.ids:
                        show_button = True
            rec.show_button = show_button

    def change_state(self):
        for rec in self:
            stage = False
            if rec.double_validation and self.type == 'remove':
                stage = rec.workflow_ids.filtered(lambda r: r.stage_id.state == rec.state).mapped('stage_id')
            else:
                workflow = self.env['workflow.stage'].search([('default', '=', True)])
                stage = workflow.filtered(lambda r: r.state == rec.state)
                index = workflow.ids.index(stage.id)
                stage = workflow[index]
            rec.sudo().write({'stage_id': stage[0].id})

    def draft_state(self):
        res = super(HRHolidays, self).draft_state()
        self.write({'state': 'draft'})
        self.change_state()
        if self.double_validation and self.type == 'remove':
            self.check_state = True
            for rec in self.workflow_ids:
                rec.sudo().write({
                    'approved': False,
                    'next': False})
        return res

    def confirm(self):
        res = super(HRHolidays, self).confirm()
        self.change_state()
        return res

    def hr_manager(self):
        if self.double_validation and self.type == 'remove':
            if not self.replace_by:
                raise exceptions.Warning(_(
                    'Select employee Replacement before confirm'))
            self.write({'state': 'validate'})
            self.change_state()
            self.check_state = False
            approve = self.workflow_ids.sudo().filtered(
                lambda r: r.stage_id.state == 'approved' and not r.approved)
            if approve:
                self.btn_string = approve[0].btn_string
                return {
                    'type': 'ir.actions.client',
                    'tag': 'reload',
                }
            else:
                self.check_state = True
        else:
            res = super(HRHolidays, self).hr_manager()
            if self.holiday_status_id.double_validation:
                self.check_state = False
            else:
                self.check_state = True
            self.change_state()
            return res

    def approved(self):
        if self.type == 'remove':
            approve = self.workflow_ids.sudo().filtered(
                lambda r: r.stage_id.state == 'approved' and not r.approved)
            if approve:
                approve[0].approved = True
                self.stage_id = approve[0].stage_id.id
            if len(approve) > 1:
                approve[1].next = True
                self.btn_string = approve[1].btn_string
                return {
                    'type': 'ir.actions.client',
                    'tag': 'reload',
                }
            if len(approve) == 1:
                self.write({'state': 'approved'})
                self.check_state = True
                self.btn_string = ""
        else:
            return super(HRHolidays, self).approved()

    def financial_manager(self):
        res = super(HRHolidays, self).financial_manager()
        self.change_state()
        return res

    def cancel(self):
        res = super(HRHolidays, self).cancel()
        self.change_state()
        return res

    def refuse(self):
        res = super(HRHolidays, self).refuse()
        self.change_state()
        return res
