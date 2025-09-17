# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class ContractExtension(models.Model):
    _inherit = 'hr.contract.extension'

    appraisal_id = fields.Many2one('hr.employee.appraisal', string="Appraisal Extension")

    @api.onchange('employee_id')
    def _get_appraisal_id_related(self):
        self.appraisal_id = False
        for item in self:
            appraisal_ids = self.env['hr.employee.appraisal'].search(
                [('employee_id', '=', item.employee_id.id), ('appraisal_type', '=', 'trial')]).ids
            if appraisal_ids:
                return {'domain': {'appraisal_id': [('id', 'in', appraisal_ids)]}}
            else:
                return {'domain': {'appraisal_id': [('id', 'in', [])]}}
