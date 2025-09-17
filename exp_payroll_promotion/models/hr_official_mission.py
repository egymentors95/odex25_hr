# -*- coding: utf-8 -*-

from odoo import models, fields, api


class HrOfficialMission(models.Model):
    _inherit = 'hr.official.mission'

    include_in_experience = fields.Boolean('Include Period in Experience', default=False)

    @api.onchange('include_in_experience')
    def _onchange_include_in_experience(self):
        for rec in self:
            rec.employee_ids.write({'include_in_experience': rec.include_in_experience})

    def draft_state(self):
        super(HrOfficialMission, self).draft_state()
        if self.employee_ids:
            for emp in self.employee_ids:
                emp.successfully_completed = False


class HrOfficialMissionEmployee(models.Model):
    _inherit = 'hr.official.mission.employee'

    successfully_completed = fields.Boolean('Successfully Completed', default=False, store=True, readonly=True)
    include_in_experience = fields.Boolean('Include Period in Experience', default=False)

    def act_successful_complete(self):
        for rec in self:
            if rec.include_in_experience:
                rec.successfully_completed = True
