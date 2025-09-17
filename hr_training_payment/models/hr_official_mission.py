# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions,_
from datetime import datetime, date, timedelta
from odoo.exceptions import ValidationError
import calendar


class HrOfficialMission(models.Model):
    _inherit = 'hr.official.mission'

    purchase_request_id = fields.Many2one(comodel_name='purchase.request', string="Purchase Request")

    def approve(self):
        # check if there is dealing with financial
        self.employee_ids.chick_not_overtime()
        if self.employee_ids and self.mission_type.related_with_financial:
            # move amounts to journal entries
            if self.move_type == 'accounting':
                if self.mission_type.account_id and self.mission_type.journal_id:
                    for item in self.employee_ids:
                        if item.amount > 0.0:
                            debit_line_vals = {
                                'name': item.employee_id.name + ' in official mission "%s" ' % self.mission_type.name,
                                'debit': item.amount,
                                'account_id': self.mission_type.account_id.id,
                                'partner_id': item.employee_id.user_id.partner_id.id
                            }
                            credit_line_vals = {
                                'name': item.employee_id.name + ' in official mission "%s" ' % self.mission_type.name,
                                'credit': item.amount,
                                'account_id': self.mission_type.journal_id.default_account_id.id,
                                'partner_id': item.employee_id.user_id.partner_id.id
                            }
                            if not item.account_move_id:
                               move = self.env['account.move'].create({
                                   'state': 'draft',
                                   'journal_id': self.mission_type.journal_id.id,
                                   'date': date.today(),
                                   'ref': 'Official mission for employee "%s" ' % item.employee_id.name,
                                   'line_ids': [(0, 0, debit_line_vals), (0, 0, credit_line_vals)],
                                   'res_model': 'hr.official.mission',
                                   'res_id': self.id
                               })
                               # fill account move for each employee
                               item.write({'account_move_id': move.id})
                else:
                    raise exceptions.Warning(
                        _('You do not have account or journal in mission type "%s" ') % self.mission_type.name)

            # move amounts to advantages of employee in contract
            elif self.move_type == 'payroll':
                # get start and end date of the current month
                current_date = date.today()
                month_start = date(current_date.year, current_date.month, 1)
                month_end = date(current_date.year, current_date.month, calendar.mdays[current_date.month])
                for line in self.employee_ids:
                    if line.sudo().employee_id.contract_id:

                        advantage_arc = line.env['contract.advantage'].create({
                            'benefits_discounts': self.official_mission.id,
                            'date_from': month_start,
                            'date_to': month_end,
                            'amount': line.amount,
                            'official_mission_id': True,
                            'employee_id': line.employee_id.id,
                            'contract_advantage_id': line.sudo().employee_id.contract_id.id,
                            'out_rule': True,
                            'state': 'confirm',
                            'comments': self.mission_purpose})
                        line.advantage_id = advantage_arc.id
                    else:
                        raise exceptions.Warning(_(
                            'Employee "%s" has no contract Please create contract to add line to advantages')
                                                 % line.employee_id.name)

        for item in self:
            # create ticket request from all employee
            if item.issuing_ticket == 'yes':
                for emp in item.employee_ids:
                    ticket = self.env['hr.ticket.request'].create({
                        'employee_id': emp.employee_id.id,
                        'mission_request_id': item.id,
                        'mission_check': True,
                        'request_for': item.ticket_cash_request_for,
                        'request_type': item.ticket_cash_request_type.id,
                        'cost_of_tickets': item.get_ticket_cost(emp.employee_id),
                        'destination': item.destination.id,
                    })
                    item.write({'ticket_request_id': ticket.id})

            # move invoice  training cost our trining center
            if item.Training_cost > 0:
                if not self.mission_type.pr_product_id.id:
                    raise ValidationError(_("You must Enter Purchase Product in Training Type Configuration"))

                product_line = {
                    'product_id': self.mission_type.pr_product_id.id,
                    'qty': 1,
                    'expected_price': self.Training_cost,
                }

                purchase_request = self.env['purchase.request'].create({
                    'state': 'draft',
                    'department_id': self.department_id2.id,
                    'date': date.today(),
                    'employee_id': self.employee_id.id,
                    'partner_id': self.partner_id.id,
                    'product_category_ids': [(4, self.mission_type.pr_product_id.categ_id.id)],
                    'purchase_purpose': self.training_details,
                    'line_ids': [(0, 0, product_line)]
                })

                self.purchase_request_id = purchase_request.id

        self.state = "approve"
        if self.mission_type.work_state and self.mission_type.duration_type == 'days':
            for emp in self.employee_ids:
                if emp.date_to >= fields.Date.today() >= emp.date_from:
                    emp.employee_id.write({'work_state': self.mission_type.work_state, 'active_mission_id': emp.id})
        self.call_cron_function()





    def draft_state(self):
        res = super(HrOfficialMission, self).draft_state()
        if self.purchase_request_id:
            self.purchase_request_id.sudo().unlink()

        return res



