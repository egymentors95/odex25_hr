# -*- coding: utf-8 -*-
from odoo import models, fields, _, exceptions


class eos_patch(models.Model):
    _name = "hr.termination.patch"
    _rec_name = 'name'
    _description = 'EOS Patch Termination'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char()
    date = fields.Date()
    last_work_date = fields.Date()
    state = fields.Selection(selection=[("draft", "Draft"),
                                        ("terminate", "Terminate")], default='draft', tracking=True)

    # Relational fields
    employee_ids = fields.Many2many('hr.employee')
    cause_type = fields.Many2one('hr.termination.type')
    calculation_method = fields.Many2many('hr.salary.rule')
    terminate_ids = fields.Many2many('hr.termination')

    # Create Termination of all employees in employee_ids

    def generate_termination(self):
        if self.employee_ids:
            termination_moves = []
            calculation_method = [item for item in self.calculation_method.ids]

            # print(self.calculation_method.ids)
            for line in self.employee_ids:
                termination_move_ids = self.env['hr.termination'].create({
                    'calculation_method': [(6, 0, calculation_method)],
                    'cause_type': self.cause_type.id,
                    'employee_id': line.id,
                    'last_work_date': self.last_work_date})
                termination_moves.append(termination_move_ids.id)
            self.terminate_ids = termination_moves
        self.state = 'terminate'

    def set_to_draft(self):
        for ids in self.terminate_ids:
            if ids.state == 'draft':
                ids.unlink()
            else:
                raise exceptions.Warning(_('You can set to draft when like termination in state not in draft'))
        self.state = 'draft'
