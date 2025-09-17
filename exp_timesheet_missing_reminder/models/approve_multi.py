# -*- coding: utf-8 -*-

from odoo import models, _
from odoo.exceptions import UserError


class ApproveMultiTimesheet(models.TransientModel):
    _name = "approve.multi.timesheet"
    _description = "Approve Multi Timesheet"

    def validate_timesheet(self):
        context = dict(self._context or {})
        moves = self.env['hr_timesheet.sheet'].browse(context.get('active_ids'))
        move_to_post = self.env['hr_timesheet.sheet']
        for move in moves:
            if move.state == 'approve':
                move_to_post += move
        if not move_to_post:
            raise UserError(_('There is No Timesheet in Confirm state to Approve.'))
        move_to_post.action_timesheet_done()
        return {'type': 'ir.actions.act_window_close'}
        