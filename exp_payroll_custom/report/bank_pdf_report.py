# -*- coding: utf-8 -*-

from odoo import models, api, _
from odoo.exceptions import UserError


class PayslipBankReport(models.AbstractModel):
    _name = 'report.exp_payroll_custom.report_payroll_bank_pdf'

    @api.model
    def _get_report_values(self, docids, data=None):
        if not data.get('form'):
            raise UserError(_("Form content is missing, this report cannot be printed."))
        emp_ids = data['employees']
        bank_ids = data['banks']
        salary_ids = data['salary']
        date_from = data['date_from']
        date_to = data['date_to']
        employees = self.sudo().env['hr.employee'].browse(emp_ids)
        salary = self.sudo().env['hr.payroll.structure'].browse(salary_ids)
        banks = self.sudo().env['res.bank'].browse(bank_ids)
        no_details = data['no_details']
        report_type = data['report_type']
        entry_type = data['entry_type']
        bank_type = data['bank_type']
        all_bank = self.sudo().env['res.bank'].search([])
        Module = self.env['ir.module.module'].sudo()
        branch = Module.search([('state', '=', 'installed'), ('name', '=', 'bi_odoo_multi_branch_hr')])


        data = []
        if not no_details:
            for bank in banks:
                docs = []
                if report_type == 'salary':
                    if entry_type == 'all':
                        if employees:
                            payslips = self.sudo().env['hr.payslip'].search(
                                ['&', ('date_from', '>=', date_from), ('date_to', '<=', date_to),
                                 ('state', '=', 'transfered'), ('employee_id', 'in', employees.ids),
                                 ('employee_id.bank_account_id.bank_id', '=', bank.id)
                                 ])

                        elif salary:
                            payslips = self.sudo().env['hr.payslip'].search(
                                ['&', ('date_from', '>=', date_from), ('date_to', '<=', date_to),
                                 ('state', '=', 'transfered'), ('struct_id', 'in', salary_ids),
                                 ('employee_id.bank_account_id.bank_id', '=', bank.id)])
                        elif salary and employees:
                            payslips = self.sudo().env['hr.payslip'].search(
                                ['&', ('date_from', '>=', date_from), ('date_to', '<=', date_to),
                                 ('state', '=', 'transfered'), ('employee_id', 'in', employees.ids),
                                 ('struct_id', 'in', salary.ids),
                                 ('employee_id.bank_account_id.bank_id', '=', bank.id)])
                        else:
                            payslips = self.sudo().env['hr.payslip'].search(
                                ['&', ('date_from', '>=', date_from), ('date_to', '<=', date_to),
                                 ('state', '=', 'transfered'), ('employee_id.bank_account_id.bank_id', '=', bank.id)])
                    elif entry_type == 'posted':
                        if employees:
                            payslips = self.sudo().env['hr.payslip'].search(
                                [('date_from', '>=', date_from), ('date_to', '<=', date_to),
                                 ('state', '=', 'transfered'), ('employee_id', 'in', employees.ids),
                                 ('employee_id.bank_account_id.bank_id', '=', bank.id), '|',
                                 ('move_id.state', '=', 'posted'), ('payslip_run_id.move_id.state', '=', 'posted')])

                        elif salary:
                            payslips = self.sudo().env['hr.payslip'].search(
                                ['&', ('date_from', '>=', date_from), ('date_to', '<=', date_to),
                                 ('state', '=', 'transfered'),
                                 ('struct_id', 'in', salary_ids), ('employee_id.bank_account_id.bank_id', '=', bank.id),
                                 '|'
                                    , ('move_id.state', '=', 'posted'), ('payslip_run_id.move_id.state', '=', 'posted')
                                 ])
                        elif salary and employees:
                            payslips = self.sudo().env['hr.payslip'].search(
                                ['&', ('date_from', '>=', date_from), ('date_to', '<=', date_to),
                                 ('state', '=', 'transfered'), ('employee_id', 'in', employees.ids),
                                 ('struct_id', 'in', salary.ids),
                                 ('employee_id.bank_account_id.bank_id', '=', bank.id), '|',
                                 ('move_id.state', '=', 'posted'), ('payslip_run_id.move_id.state', '=', 'posted')])
                        else:
                            payslips = self.sudo().env['hr.payslip'].search(
                                ['&', ('date_from', '>=', date_from), ('date_to', '<=', date_to),
                                 ('state', '=', 'transfered'), ('employee_id.bank_account_id.bank_id', '=', bank.id),
                                 '|',
                                 ('move_id.state', '=', 'posted'), ('payslip_run_id.move_id.state', '=', 'posted')])

                    elif entry_type == 'unposted':
                        if employees:
                            payslips = self.sudo().env['hr.payslip'].search(
                                ['&', ('date_from', '>=', date_from), ('date_to', '<=', date_to),
                                 ('state', '=', 'transfered'), ('employee_id', 'in', employees.ids),
                                 ('employee_id.bank_account_id.bank_id', '=', bank.id), '|',
                                 ('move_id.state', '=', 'draft'), ('payslip_run_id.move_id.state', '=', 'draft'),
                                 ])

                        elif salary:
                            payslips = self.sudo().env['hr.payslip'].search(
                                ['&', ('date_from', '>=', date_from), ('date_to', '<=', date_to),
                                 ('state', '=', 'transfered'), ('employee_id.bank_account_id.bank_id', '=', bank.id),
                                 ('struct_id', 'in', salary_ids), '|',
                                 ('move_id.state', '=', 'draft'), ('payslip_run_id.move_id.state', '=', 'draft'),
                                 ])
                        elif salary and employees:
                            payslips = self.sudo().env['hr.payslip'].search(
                                ['&', ('date_from', '>=', date_from), ('date_to', '<=', date_to),
                                 ('state', '=', 'transfered'), ('employee_id', 'in', employees.ids),
                                 ('struct_id', 'in', salary.ids),
                                 ('employee_id.bank_account_id.bank_id', '=', bank.id), '|',
                                 ('move_id.state', '=', 'draft'), ('payslip_run_id.move_id.state', '=', 'draft')])
                        else:
                            payslips = self.sudo().env['hr.payslip'].search(
                                ['&', ('date_from', '>=', date_from), ('date_to', '<=', date_to),
                                 ('state', '=', 'transfered'), ('employee_id.bank_account_id.bank_id', '=', bank.id),
                                 '|',
                                 ('move_id.state', '=', 'draft'), ('payslip_run_id.move_id.state', '=', 'draft')])

                    for payslip in payslips:
                        tot_basic = 0.0
                        tot_housing = 0.0
                        tot_other = 0.0
                        tot_net = 0.0
                        tot_ded = 0.0

                        net = 0.0
                        basic = 0.0
                        housing = 0.0
                        other = 0.0
                        total = 0.0

                        salary_rules = self.sudo().env['hr.salary.rule'].search([]).sorted(
                            key=lambda v: v.sequence).ids
                        payslip_line_obj = self.sudo().env['hr.payslip.line']
                        payslip_lines_ids = payslip_line_obj.sudo().search([('slip_id', '=', payslip.id)])
                        if not payslip_lines_ids:
                            continue

                        for payslip_line_rec in payslip_lines_ids:
                            if payslip_line_rec.salary_rule_id.id in salary_rules:
                                if payslip_line_rec.salary_rule_id.rules_type == 'salary':
                                    basic += payslip_line_rec.total
                                elif payslip_line_rec.salary_rule_id.rules_type == 'house':
                                    housing += payslip_line_rec.total
                            other = payslip.total_allowances - basic - housing
                            deduction = total - net
                            tot_net += net
                            tot_basic += basic
                            tot_housing += housing
                            tot_other += other
                            tot_ded += deduction

                        docs.append({
                            'ID': payslip.employee_id.emp_no,
                            'Name': payslip.employee_id.name,
                            'Account #': payslip.employee_id.bank_account_id.acc_number,
                            'Bank': payslip.employee_id.bank_account_id.bank_id.bic,
                            'Salary': payslip.total_sum,
                            'National': payslip.employee_id.saudi_number.saudi_id if payslip.employee_id.check_nationality == True else
                            payslip.employee_id.iqama_number.iqama_id,
                            'Basic': basic,
                            'Housing': housing,
                            'Other': round(other, 2),
                            'Deduction': round((payslip.total_deductions + payslip.total_loans), 2),
                            'Address': payslip.employee_id.branch_id.name if branch else payslip.employee_id.working_location.name,
                            'Pay Description': report_type,
                            'currency': payslip.employee_id.company_id.currency_id.name
                        })
                elif report_type == 'allowance':
                    allowances = self.sudo().env['hr.employee.reward'].search(
                        ['&', ('date', '>=', date_from), ('date', '<=', date_to), ('state', '=', 'done')
                         ])
                    for allowance in allowances:
                        reward_line_obj = self.sudo().env['lines.ids.reward']
                        if entry_type == 'all':
                            if employees:
                                reward_lines_ids = reward_line_obj.sudo().search(
                                    [('employee_reward_id', '=', allowance.id),
                                     ('employee_id.bank_account_id.bank_id', '=', bank.id),
                                     ('employee_id', 'in', employees.ids)])
                            else:
                                reward_lines_ids = reward_line_obj.sudo().search(
                                    [('employee_reward_id', '=', allowance.id),
                                     ('employee_id.bank_account_id.bank_id', '=', bank.id)])
                        elif entry_type == 'posted':
                            if employees:
                                reward_lines_ids = reward_line_obj.sudo().search(
                                    [('employee_reward_id', '=', allowance.id),
                                     ('employee_id.bank_account_id.bank_id', '=', bank.id),
                                     ('employee_id', 'in', employees.ids), ('move_id.state', '=', 'posted')])
                            else:
                                reward_lines_ids = reward_line_obj.sudo().search(
                                    [('employee_reward_id', '=', allowance.id), ('move_id.state', '=', 'posted'),
                                     ('employee_id.bank_account_id.bank_id', '=', bank.id)])

                        elif entry_type == 'unposted':
                            if employees:
                                reward_lines_ids = reward_line_obj.sudo().search(
                                    [('employee_reward_id', '=', allowance.id),
                                     ('employee_id.bank_account_id.bank_id', '=', bank.id),
                                     ('move_id.state', '=', 'draft'),
                                     ('employee_id', 'in', employees.ids)])
                            else:
                                reward_lines_ids = reward_line_obj.sudo().search(
                                    [('employee_reward_id', '=', allowance.id), ('move_id.state', '=', 'draft'),
                                     ('employee_id.bank_account_id.bank_id', '=', bank.id)])

                        if not reward_lines_ids:
                            continue

                        for reward in reward_lines_ids:
                            docs.append({
                                'ID': reward.employee_id.emp_no,
                                'Name': reward.employee_id.name,
                                'Account #': reward.employee_id.bank_account_id.acc_number,
                                'Bank': reward.employee_id.bank_account_id.bank_id.bic,
                                'Salary': reward.amount,
                                'National': reward.employee_id.saudi_number.saudi_id if reward.employee_id.check_nationality == True else
                                reward.employee_id.iqama_number.iqama_id,
                                'Basic': 0.0,
                                'Housing': 0.0,
                                'Other': 0.0,
                                'Deduction': 0.0,
                                'Address': reward.employee_id.branch_id.name if branch else reward.employee_id.working_location.name,
                                'Pay Description': report_type,
                                'currency': reward.employee_id.company_id.currency_id.name
                            })
                elif report_type == 'overtime':
                    overtime = self.sudo().env['employee.overtime.request'].search(
                        ['&', ('date_from', '>=', date_from), ('date_to', '<=', date_to),
                         ('transfer_type', '=', 'accounting'), ('state', '=', 'validated')
                         ])
                    for over in overtime:
                        reward_line_obj = self.sudo().env['line.ids.over.time']
                        if entry_type == 'all':
                            if employees:
                                overtime_lines_ids = reward_line_obj.sudo().search(
                                    [('employee_over_time_id', '=', over.id),
                                     ('employee_id.bank_account_id.bank_id', '=', bank.id),
                                     ('employee_id', 'in', employees.ids)])
                            else:
                                overtime_lines_ids = reward_line_obj.sudo().search(
                                    [('employee_over_time_id', '=', over.id),
                                     ('employee_id.bank_account_id.bank_id', '=', bank.id)])
                        elif entry_type == 'posted':
                            if employees:
                                overtime_lines_ids = reward_line_obj.sudo().search(
                                    [('employee_over_time_id', '=', over.id), ('move_id.state', '=', 'posted'),
                                     ('employee_id.bank_account_id.bank_id', '=', bank.id),
                                     ('employee_id', 'in', employees.ids)])
                            else:
                                overtime_lines_ids = reward_line_obj.sudo().search(
                                    [('employee_over_time_id', '=', over.id), ('move_id.state', '=', 'posted'),
                                     ('employee_id.bank_account_id.bank_id', '=', bank.id)])

                        elif entry_type == 'unposted':
                            if employees:
                                overtime_lines_ids = reward_line_obj.sudo().search(
                                    [('employee_over_time_id', '=', over.id), ('move_id.state', '=', 'draft'),
                                     ('employee_id.bank_account_id.bank_id', '=', bank.id),
                                     ('employee_id', 'in', employees.ids)])
                            else:
                                overtime_lines_ids = reward_line_obj.sudo().search(
                                    [('employee_over_time_id', '=', over.id), ('move_id.state', '=', 'draft'),
                                     ('employee_id.bank_account_id.bank_id', '=', bank.id)])

                        if not overtime_lines_ids:
                            continue

                        for ove in overtime_lines_ids:
                            docs.append({
                                'ID': ove.employee_id.emp_no,
                                'Name': ove.employee_id.name,
                                'Account #': ove.employee_id.bank_account_id.acc_number,
                                'Bank': ove.employee_id.bank_account_id.bank_id.bic,
                                'Salary': ove.price_hour,
                                'National': ove.employee_id.saudi_number.saudi_id if ove.employee_id.check_nationality == True else
                                ove.employee_id.iqama_number.iqama_id,
                                'Basic': 0.0,
                                'Housing': 0.0,
                                'Other': 0.0,
                                'Deduction': 0.0,
                                'Address': ove.employee_id.branch_id.name if branch else ove.employee_id.working_location.name,
                                'Pay Description': report_type,
                                'currency':  ove.employee_id.company_id.currency_id.name
                            })
                elif report_type == 'mission':
                    missions = self.sudo().env['hr.official.mission'].search(
                        ['&', ('date_from', '>=', date_from), ('date_to', '<=', date_to),
                         ('process_type', '=', 'mission'), ('state', '=', 'approve')
                         ])
                    for mission in missions:
                        mission_line_obj = self.sudo().env['hr.official.mission.employee']
                        if entry_type == 'all':
                            if employees:
                                mission_lines_ids = mission_line_obj.sudo().search(
                                    [('official_mission_id', '=', mission.id),
                                     ('employee_id.bank_account_id.bank_id', '=', bank.id),
                                     ('employee_id', 'in', employees.ids)])
                            else:
                                mission_lines_ids = mission_line_obj.sudo().search(
                                    [('official_mission_id', '=', mission.id),
                                     ('employee_id.bank_account_id.bank_id', '=', bank.id)])
                        elif entry_type == 'posted':
                            if employees:
                                mission_lines_ids = mission_line_obj.sudo().search(
                                    [('official_mission_id', '=', mission.id),
                                     ('employee_id.bank_account_id.bank_id', '=', bank.id),
                                     ('employee_id', 'in', employees.ids), ('account_move_id.state', '=', 'posted')])
                            else:
                                mission_lines_ids = mission_line_obj.sudo().search(
                                    [('official_mission_id', '=', mission.id), ('account_move_id.state', '=', 'posted'),
                                     ('employee_id.bank_account_id.bank_id', '=', bank.id)])
                        elif entry_type == 'unposted':
                            if employees:
                                mission_lines_ids = mission_line_obj.sudo().search(
                                    [('official_mission_id', '=', mission.id), ('account_move_id.state', '=', 'draft'),
                                     ('employee_id.bank_account_id.bank_id', '=', bank.id),
                                     ('employee_id', 'in', employees.ids)])
                            else:
                                mission_lines_ids = mission_line_obj.sudo().search(
                                    [('official_mission_id', '=', mission.id), ('account_move_id.state', '=', 'draft'),
                                     ('employee_id.bank_account_id.bank_id', '=', bank.id)])

                        if not mission_lines_ids:
                            continue

                        for miss in mission_lines_ids:
                            docs.append({
                                'ID': miss.employee_id.emp_no,
                                'Name': miss.employee_id.name,
                                'Account #': miss.employee_id.bank_account_id.acc_number,
                                'Bank': miss.employee_id.bank_account_id.bank_id.bic,
                                'Salary': miss.amount,
                                'National': miss.employee_id.saudi_number.saudi_id if miss.employee_id.check_nationality == True else
                                miss.employee_id.iqama_number.iqama_id,
                                'Basic': 0.0,
                                'Housing': 0.0,
                                'Other': 0.0,
                                'Deduction': 0.0,
                                'Address': miss.employee_id.branch_id.name if branch else miss.employee_id.working_location.name,
                                'Pay Description': report_type,
                                'currency':  miss.employee_id.company_id.currency_id.name
                            })
                elif report_type == 'training':
                    trainings = self.sudo().env['hr.official.mission'].search(
                        ['&', ('date_from', '>=', date_from), ('date_to', '<=', date_to),
                         ('process_type', '=', 'training'), ('state', '=', 'approve')
                         ])
                    for training in trainings:
                        training_line_obj = self.sudo().env['hr.official.mission.employee']
                        if entry_type == 'all':
                            if employees:
                                training_lines_ids = training_line_obj.sudo().search(
                                    [('official_mission_id', '=', training.id),
                                     ('employee_id.bank_account_id.bank_id', '=', bank.id),
                                     ('employee_id', 'in', employees.ids)])
                            else:
                                training_lines_ids = training_line_obj.sudo().search(
                                    [('official_mission_id', '=', training.id),
                                     ('employee_id.bank_account_id.bank_id', '=', bank.id)])
                        elif entry_type == 'posted':
                            if employees:
                                training_lines_ids = training_line_obj.sudo().search(
                                    [('official_mission_id', '=', training.id),
                                     ('employee_id.bank_account_id.bank_id', '=', bank.id),
                                     ('employee_id', 'in', employees.ids), ('account_move_id.state', '=', 'posted')])
                            else:
                                training_lines_ids = training_line_obj.sudo().search(
                                    [('official_mission_id', '=', training.id),
                                     ('employee_id.bank_account_id.bank_id', '=', bank.id),
                                     ('account_move_id.state', '=', 'posted')])
                        elif entry_type == 'unposted':
                            if employees:
                                training_lines_ids = training_line_obj.sudo().search(
                                    [('official_mission_id', '=', training.id), ('account_move_id.state', '=', 'draft'),
                                     ('employee_id.bank_account_id.bank_id', '=', bank.id),
                                     ('employee_id', 'in', employees.ids)])
                            else:
                                training_lines_ids = training_line_obj.sudo().search(
                                    [('official_mission_id', '=', training.id), ('account_move_id.state', '=', 'draft'),
                                     ('employee_id.bank_account_id.bank_id', '=', bank.id)])

                        if not training_lines_ids:
                            continue

                        for train in training_lines_ids:
                            docs.append({
                                'ID': train.employee_id.emp_no,
                                'Name': train.employee_id.name,
                                'Account #': train.employee_id.bank_account_id.acc_number,
                                'Bank': train.employee_id.bank_account_id.bank_id.bic,
                                'Salary': train.amount,
                                'National': train.employee_id.saudi_number.saudi_id if train.employee_id.check_nationality == True else
                                train.employee_id.iqama_number.iqama_id,
                                'Basic': 0.0,
                                'Housing': 0.0,
                                'Other': 0.0,
                                'Deduction': 0.0,
                                'Address': train.employee_id.branch_id.name if branch else train.employee_id.working_location.name,
                                'Pay Description': report_type,
                                'currency': train.employee_id.company_id.currency_id.name
                            })

                data.append({
                    'docs': docs,
                    'bank': bank.name,
                    'report_type': report_type,
                    'no_details': no_details,
                    'bank_type': bank_type
                })

        else:
            docs = []
            if report_type == 'salary':
                if entry_type == 'all':
                    if employees:
                        payslips = self.sudo().env['hr.payslip'].search(
                            ['&', ('date_from', '>=', date_from), ('date_to', '<=', date_to),
                             ('state', '=', 'transfered'),
                             ('employee_id', 'in', employees.ids),
                             ('employee_id.bank_account_id.bank_id', 'in', all_bank.ids)])

                    elif salary:
                        payslips = self.sudo().env['hr.payslip'].search(
                            ['&', ('date_from', '>=', date_from), ('date_to', '<=', date_to),
                             ('state', '=', 'transfered'),
                             ('struct_id', 'in', salary_ids),
                             ('employee_id.bank_account_id.bank_id', 'in', all_bank.ids)])
                    elif salary and employees:
                        payslips = self.sudo().env['hr.payslip'].search(
                            ['&', ('date_from', '>=', date_from), ('date_to', '<=', date_to),
                             ('state', '=', 'transfered'),
                             ('employee_id', 'in', employees.ids), ('struct_id', 'in', salary.ids),
                             ('employee_id.bank_account_id.bank_id', 'in', all_bank.ids)])
                    else:
                        payslips = self.sudo().env['hr.payslip'].search(
                            ['&', ('date_from', '>=', date_from), ('date_to', '<=', date_to),
                             ('state', '=', 'transfered'),
                             ('employee_id.bank_account_id.bank_id', 'in', all_bank.ids)])
                elif entry_type == 'posted':
                    if employees:
                        payslips = self.sudo().env['hr.payslip'].search(
                            ['&', ('date_from', '>=', date_from), ('date_to', '<=', date_to),
                             ('state', '=', 'transfered'),
                             ('employee_id', 'in', employees.ids),
                             ('employee_id.bank_account_id.bank_id', 'in', all_bank.ids)
                                , '|',
                             ('move_id.state', '=', 'posted'), ('payslip_run_id.move_id.state', '=', 'posted')
                             ])

                    elif salary:
                        payslips = self.sudo().env['hr.payslip'].search(
                            ['&', ('date_from', '>=', date_from), ('date_to', '<=', date_to),
                             ('state', '=', 'transfered'), ('struct_id', 'in', salary_ids),
                             ('employee_id.bank_account_id.bank_id', 'in', all_bank.ids), '|',
                             ('move_id.state', '=', 'posted'), ('payslip_run_id.move_id.state', '=', 'posted')])
                    elif salary and employees:
                        payslips = self.sudo().env['hr.payslip'].search(
                            ['&', ('date_from', '>=', date_from), ('date_to', '<=', date_to),
                             ('state', '=', 'transfered'), ('employee_id', 'in', employees.ids),
                             ('struct_id', 'in', salary.ids),
                             ('employee_id.bank_account_id.bank_id', 'in', all_bank.ids), '|',
                             ('move_id.state', '=', 'posted'), ('payslip_run_id.move_id.state', '=', 'posted')])
                    else:
                        payslips = self.sudo().env['hr.payslip'].search(
                            ['&', ('date_from', '>=', date_from), ('date_to', '<=', date_to),
                             ('state', '=', 'transfered'),
                             ('employee_id.bank_account_id.bank_id', 'in', all_bank.ids)
                                , '|',
                             ('move_id.state', '=', 'posted'), ('payslip_run_id.move_id.state', '=', 'posted')
                             ])
                elif entry_type == 'unposted':
                    if employees:
                        payslips = self.sudo().env['hr.payslip'].search(
                            ['&', ('date_from', '>=', date_from), ('date_to', '<=', date_to),
                             ('state', '=', 'transfered'),
                             ('employee_id', 'in', employees.ids),
                             ('employee_id.bank_account_id.bank_id', 'in', all_bank.ids)
                                , '|',
                             ('move_id.state', '=', 'draft'), ('payslip_run_id.move_id.state', '=', 'draft')
                             ])

                    elif salary:
                        payslips = self.sudo().env['hr.payslip'].search(
                            ['&', ('date_from', '>=', date_from), ('date_to', '<=', date_to),
                             ('state', '=', 'transfered'),
                             ('struct_id', 'in', salary_ids),
                             ('employee_id.bank_account_id.bank_id', 'in', all_bank.ids)
                                , '|',
                             ('move_id.state', '=', 'draft'), ('payslip_run_id.move_id.state', '=', 'draft')
                             ])
                    elif salary and employees:
                        payslips = self.sudo().env['hr.payslip'].search(
                            ['&', ('date_from', '>=', date_from), ('date_to', '<=', date_to),
                             ('state', '=', 'transfered'),
                             ('employee_id', 'in', employees.ids), ('struct_id', 'in', salary.ids),
                             ('employee_id.bank_account_id.bank_id', 'in', all_bank.ids)
                                , '|',
                             ('move_id.state', '=', 'draft'), ('payslip_run_id.move_id.state', '=', 'draft')
                             ])
                    else:
                        payslips = self.sudo().env['hr.payslip'].search(
                            ['&', ('date_from', '>=', date_from), ('date_to', '<=', date_to),
                             ('state', '=', 'transfered'),
                             ('employee_id.bank_account_id.bank_id', 'in', all_bank.ids)
                                , '|',
                             ('move_id.state', '=', 'draft'), ('payslip_run_id.move_id.state', '=', 'draft')
                             ])

                for payslip in payslips:
                    tot_basic = 0.0
                    tot_housing = 0.0
                    tot_other = 0.0
                    tot_net = 0.0
                    tot_ded = 0.0
                    net = 0.0
                    basic = 0.0
                    housing = 0.0
                    other = 0.0
                    total = 0.0
                    salary_rules = self.sudo().env['hr.salary.rule'].search([]).sorted(
                        key=lambda v: v.sequence).ids
                    payslip_line_obj = self.sudo().env['hr.payslip.line']
                    payslip_lines_ids = payslip_line_obj.sudo().search([('slip_id', '=', payslip.id)])
                    if not payslip_lines_ids:
                        continue

                    for payslip_line_rec in payslip_lines_ids:
                        if payslip_line_rec.salary_rule_id.id in salary_rules:
                            if payslip_line_rec.salary_rule_id.rules_type == 'salary':
                                basic += payslip_line_rec.total
                            elif payslip_line_rec.salary_rule_id.rules_type == 'house':
                                housing += payslip_line_rec.total
                        other = payslip.total_allowances - basic - housing
                        deduction = total - net
                        tot_net += net
                        tot_basic += basic
                        tot_housing += housing
                        tot_other += other
                        tot_ded += deduction
                    docs.append({
                        'ID': payslip.employee_id.emp_no,
                        'Name': payslip.employee_id.name,
                        'Account #': payslip.employee_id.bank_account_id.acc_number,
                        'Bank': payslip.employee_id.bank_account_id.bank_id.bic,
                        'Salary': payslip.total_sum,
                        'National': payslip.employee_id.saudi_number.saudi_id if payslip.employee_id.check_nationality == True else
                        payslip.employee_id.iqama_number.iqama_id,
                        'Basic': basic,
                        'Housing': housing,
                        'Other': round(other, 2),
                        'Deduction': round((payslip.total_deductions + payslip.total_loans), 2),
                        'Address': payslip.employee_id.branch_id.name if branch else payslip.employee_id.working_location.name,
                        'Pay Description': report_type,
                        'currency':  payslip.employee_id.company_id.currency_id.name
                    })
            elif report_type == 'allowance':
                allowances = self.sudo().env['hr.employee.reward'].search(
                    ['&', ('date', '>=', date_from), ('date', '<=', date_to), ('state', '=', 'done')
                     ])
                for allowance in allowances:
                    reward_line_obj = self.sudo().env['lines.ids.reward']
                    if entry_type == 'all':
                        if employees:
                            reward_lines_ids = reward_line_obj.sudo().search(
                                [('employee_reward_id', '=', allowance.id),
                                 ('employee_id.bank_account_id.bank_id', 'in', all_bank.ids),
                                 ('employee_id', 'in', employees.ids)])
                        else:
                            reward_lines_ids = reward_line_obj.sudo().search(
                                [('employee_reward_id', '=', allowance.id),
                                 ('employee_id.bank_account_id.bank_id', 'in', all_bank.ids)])
                    elif entry_type == 'posted':
                        if employees:
                            reward_lines_ids = reward_line_obj.sudo().search(
                                [('employee_reward_id', '=', allowance.id),
                                 ('employee_id.bank_account_id.bank_id', 'in', all_bank.ids),
                                 ('employee_id', 'in', employees.ids), ('move_id.state', '=', 'posted')])
                        else:
                            reward_lines_ids = reward_line_obj.sudo().search(
                                [('employee_reward_id', '=', allowance.id), ('move_id.state', '=', 'posted'),
                                 ('employee_id.bank_account_id.bank_id', 'in', all_bank.ids)])
                    elif entry_type == 'unposted':
                        if employees:
                            reward_lines_ids = reward_line_obj.sudo().search(
                                [('employee_reward_id', '=', allowance.id), ('move_id.state', '=', 'draft'),
                                 ('employee_id.bank_account_id.bank_id', 'in', all_bank.ids),
                                 ('employee_id', 'in', employees.ids)])
                        else:
                            reward_lines_ids = reward_line_obj.sudo().search(
                                [('employee_reward_id', '=', allowance.id), ('move_id.state', '=', 'draft'),
                                 ('employee_id.bank_account_id.bank_id', 'in', all_bank.ids)])

                    if not reward_lines_ids:
                        continue

                    for reward in reward_lines_ids:
                        docs.append({
                            'ID': reward.employee_id.emp_no,
                            'Name': reward.employee_id.name,
                            'Account #': reward.employee_id.bank_account_id.acc_number,
                            'Bank': reward.employee_id.bank_account_id.bank_id.bic,
                            'Salary': reward.amount,
                            'National': reward.employee_id.saudi_number.saudi_id if reward.employee_id.check_nationality == True else
                            reward.employee_id.iqama_number.iqama_id,
                            'Basic': 0.0,
                            'Housing': 0.0,
                            'Other': 0.0,
                            'Deduction': 0.0,
                            'Address': reward.employee_id.branch_id.name if branch else reward.employee_id.working_location.name,
                            'Pay Description': report_type,
                            'currency': reward.employee_id.company_id.currency_id.name
                        })
            elif report_type == 'overtime':
                overtime = self.sudo().env['employee.overtime.request'].search(
                    ['&', ('date_from', '>=', date_from), ('date_to', '<=', date_to),
                     ('transfer_type', '=', 'accounting'), ('state', '=', 'validated')
                     ])
                for over in overtime:
                    reward_line_obj = self.sudo().env['line.ids.over.time']
                    if entry_type == 'all':
                        if employees:
                            overtime_lines_ids = reward_line_obj.sudo().search(
                                [('employee_over_time_id', '=', over.id),
                                 ('employee_id.bank_account_id.bank_id', 'in', all_bank.ids),
                                 ('employee_id', 'in', employees.ids)])
                        else:
                            overtime_lines_ids = reward_line_obj.sudo().search(
                                [('employee_over_time_id', '=', over.id),
                                 ('employee_id.bank_account_id.bank_id', 'in', all_bank.ids)])
                    elif entry_type == 'posted':
                        if employees:
                            overtime_lines_ids = reward_line_obj.sudo().search(
                                [('employee_over_time_id', '=', over.id),
                                 ('employee_id.bank_account_id.bank_id', 'in', all_bank.ids),
                                 ('employee_id', 'in', employees.ids), ('move_id.state', '=', 'posted')])
                        else:
                            overtime_lines_ids = reward_line_obj.sudo().search(
                                [('employee_over_time_id', '=', over.id), ('move_id.state', '=', 'posted'),
                                 ('employee_id.bank_account_id.bank_id', 'in', all_bank.ids)])
                    elif entry_type == 'unposted':
                        if employees:
                            overtime_lines_ids = reward_line_obj.sudo().search(
                                [('employee_over_time_id', '=', over.id),
                                 ('employee_id.bank_account_id.bank_id', 'in', all_bank.ids),
                                 ('employee_id', 'in', employees.ids), ('move_id.state', '=', 'draft')])
                        else:
                            overtime_lines_ids = reward_line_obj.sudo().search(
                                [('employee_over_time_id', '=', over.id), ('move_id.state', '=', 'draft'),
                                 ('employee_id.bank_account_id.bank_id', 'in', all_bank.ids)])

                    if not overtime_lines_ids:
                        continue

                    for ove in overtime_lines_ids:
                        docs.append({
                            'ID': ove.employee_id.emp_no,
                            'Name': ove.employee_id.name,
                            'Account #': ove.employee_id.bank_account_id.acc_number,
                            'Bank': ove.employee_id.bank_account_id.bank_id.bic,
                            'Salary': ove.price_hour,
                            'National': ove.employee_id.saudi_number.saudi_id if ove.employee_id.check_nationality == True else
                            ove.employee_id.iqama_number.iqama_id,
                            'Basic': 0.0,
                            'Housing': 0.0,
                            'Other': 0.0,
                            'Deduction': 0.0,
                            'Address': ove.employee_id.branch_id.name if branch else ove.employee_id.working_location.name,
                            'Pay Description': report_type,
                            'currency':ove.employee_id.company_id.currency_id.name
                        })
            elif report_type == 'mission':
                missions = self.sudo().env['hr.official.mission'].search(
                    ['&', ('date_from', '>=', date_from), ('date_to', '<=', date_to), ('process_type', '=', 'mission'),
                     ('state', '=', 'approve')
                     ])
                for mission in missions:
                    mission_line_obj = self.sudo().env['hr.official.mission.employee']
                    if entry_type == 'all':
                        if employees:
                            mission_lines_ids = mission_line_obj.sudo().search(
                                [('official_mission_id', '=', mission.id),
                                 ('employee_id.bank_account_id.bank_id', 'in', all_bank.ids),
                                 ('employee_id', 'in', employees.ids)])
                        else:
                            mission_lines_ids = mission_line_obj.sudo().search(
                                [('official_mission_id', '=', mission.id),
                                 ('employee_id.bank_account_id.bank_id', 'in', all_bank.ids)])
                    elif entry_type == 'posted':
                        if employees:
                            mission_lines_ids = mission_line_obj.sudo().search(
                                [('official_mission_id', '=', mission.id),
                                 ('employee_id.bank_account_id.bank_id', 'in', all_bank.ids),
                                 ('employee_id', 'in', employees.ids), ('account_move_id.state', '=', 'posted')])
                        else:
                            mission_lines_ids = mission_line_obj.sudo().search(
                                [('official_mission_id', '=', mission.id), ('account_move_id.state', '=', 'posted'),
                                 ('employee_id.bank_account_id.bank_id', 'in', all_bank.ids)])
                    elif entry_type == 'unposted':
                        if employees:
                            mission_lines_ids = mission_line_obj.sudo().search(
                                [('official_mission_id', '=', mission.id), ('account_move_id.state', '=', 'draft'),
                                 ('employee_id.bank_account_id.bank_id', 'in', all_bank.ids),
                                 ('employee_id', 'in', employees.ids)])
                        else:
                            mission_lines_ids = mission_line_obj.sudo().search(
                                [('official_mission_id', '=', mission.id), ('account_move_id.state', '=', 'draft'),
                                 ('employee_id.bank_account_id.bank_id', 'in', all_bank.ids)])

                    if not mission_lines_ids:
                        continue

                    for miss in mission_lines_ids:
                        docs.append({
                            'ID': miss.employee_id.emp_no,
                            'Name': miss.employee_id.name,
                            'Account #': miss.employee_id.bank_account_id.acc_number,
                            'Bank': miss.employee_id.bank_account_id.bank_id.bic,
                            'Salary': miss.amount,
                            'National': miss.employee_id.saudi_number.saudi_id if miss.employee_id.check_nationality == True else
                            miss.employee_id.iqama_number.iqama_id,
                            'Basic': 0.0,
                            'Housing': 0.0,
                            'Other': 0.0,
                            'Deduction': 0.0,
                            'Address': miss.employee_id.branch_id.name if branch else miss.employee_id.working_location.name,
                            'Pay Description': report_type,
                            'currency': miss.employee_id.company_id.currency_id.name
                        })
            elif report_type == 'training':
                trainings = self.sudo().env['hr.official.mission'].search(
                    ['&', ('date_from', '>=', date_from), ('date_to', '<=', date_to),
                     ('process_type', '=', 'training'), ('state', '=', 'approve')
                     ])
                for training in trainings:
                    training_line_obj = self.sudo().env['hr.official.mission.employee']
                    if entry_type == 'all':
                        if employees:
                            training_lines_ids = training_line_obj.sudo().search(
                                [('official_mission_id', '=', training.id),
                                 ('employee_id.bank_account_id.bank_id', 'in', all_bank.ids),
                                 ('employee_id', 'in', employees.ids)])
                        else:
                            training_lines_ids = training_line_obj.sudo().search(
                                [('official_mission_id', '=', training.id),
                                 ('employee_id.bank_account_id.bank_id', 'in', all_bank.ids)])
                    elif entry_type == 'posted':
                        if employees:
                            training_lines_ids = training_line_obj.sudo().search(
                                [('official_mission_id', '=', training.id),
                                 ('employee_id.bank_account_id.bank_id', 'in', all_bank.ids),
                                 ('employee_id', 'in', employees.ids), ('account_move_id.state', '=', 'posted')])
                        else:
                            training_lines_ids = training_line_obj.sudo().search(
                                [('official_mission_id', '=', training.id),
                                 ('employee_id.bank_account_id.bank_id', 'in', all_bank.ids),
                                 ('account_move_id.state', '=', 'posted')])
                    elif entry_type == 'unposted':
                        if employees:
                            training_lines_ids = training_line_obj.sudo().search(
                                [('official_mission_id', '=', training.id),
                                 ('employee_id.bank_account_id.bank_id', 'in', all_bank.ids),
                                 ('employee_id', 'in', employees.ids), ('account_move_id.state', '=', 'draft')])
                        else:
                            training_lines_ids = training_line_obj.sudo().search(
                                [('official_mission_id', '=', training.id),
                                 ('employee_id.bank_account_id.bank_id', 'in', all_bank.ids),
                                 ('account_move_id.state', '=', 'draft')])

                    if not training_lines_ids:
                        continue

                    for train in training_lines_ids:
                        docs.append({
                            'ID': train.employee_id.emp_no,
                            'Name': train.employee_id.name,
                            'Account #': train.employee_id.bank_account_id.acc_number,
                            'Bank': train.employee_id.bank_account_id.bank_id.bic,
                            'Salary': train.amount,
                            'National': train.employee_id.saudi_number.saudi_id if train.employee_id.check_nationality == True else
                            train.employee_id.iqama_number.iqama_id,
                            'Basic': 0.0,
                            'Housing': 0.0,
                            'Other': 0.0,
                            'Deduction': 0.0,
                            'Address': train.employee_id.branch_id.name if branch else train.employee_id.working_location.name,
                            'Pay Description': report_type,
                            'currency': train.employee_id.company_id.currency_id.name
                        })

            data.append({
                'docs': docs,
                'bank': '',
                'report_type': report_type,
                'no_details': no_details
            })
        return {
            'banks': banks,
            'data': data,
            'date_from': date_from,
            'date_to': date_to,
        }

class PayslipBankReport(models.AbstractModel):
    _name = 'report.exp_payroll_custom.report_payroll_bank_pdf_docx'

    @api.model
    def _get_report_values(self, docids, data=None):
        total_docs_count = 0
        total_amount_salary = 0
        number_of_records = 0
        if not data.get('form'):
            raise UserError(_("Form content is missing, this report cannot be printed."))
        emp_ids = data['employees']
        bank_ids = data['banks']
        salary_ids = data['salary']
        date_from = data['date_from']
        date_to = data['date_to']
        company_id = data['company_id']
        employees = self.sudo().env['hr.employee'].browse(emp_ids)
        salary = self.sudo().env['hr.payroll.structure'].browse(salary_ids)
        banks = self.sudo().env['res.bank'].browse(bank_ids)
        no_details = data['no_details']
        report_type = data['report_type']
        entry_type = data['entry_type']
        bank_type = data['bank_type']
        all_bank = self.sudo().env['res.bank'].search([])
        Module = self.env['ir.module.module'].sudo()
        branch = Module.search([('state', '=', 'installed'), ('name', '=', 'bi_odoo_multi_branch_hr')])


        data = []
        if not no_details:
            for bank in banks:
                docs = []
                if report_type == 'salary':
                    if entry_type == 'all':
                        if employees:
                            payslips = self.sudo().env['hr.payslip'].search(
                                ['&', ('date_from', '>=', date_from), ('date_to', '<=', date_to),
                                 ('state', '=', 'transfered'), ('employee_id', 'in', employees.ids),
                                 ('employee_id.bank_account_id.bank_id', '=', bank.id)
                                 ])

                        elif salary:
                            payslips = self.sudo().env['hr.payslip'].search(
                                ['&', ('date_from', '>=', date_from), ('date_to', '<=', date_to),
                                 ('state', '=', 'transfered'), ('struct_id', 'in', salary_ids),
                                 ('employee_id.bank_account_id.bank_id', '=', bank.id)])
                        elif salary and employees:
                            payslips = self.sudo().env['hr.payslip'].search(
                                ['&', ('date_from', '>=', date_from), ('date_to', '<=', date_to),
                                 ('state', '=', 'transfered'), ('employee_id', 'in', employees.ids),
                                 ('struct_id', 'in', salary.ids),
                                 ('employee_id.bank_account_id.bank_id', '=', bank.id)])
                        else:
                            payslips = self.sudo().env['hr.payslip'].search(
                                ['&', ('date_from', '>=', date_from), ('date_to', '<=', date_to),
                                 ('state', '=', 'transfered'), ('employee_id.bank_account_id.bank_id', '=', bank.id)])
                    elif entry_type == 'posted':
                        if employees:
                            payslips = self.sudo().env['hr.payslip'].search(
                                [('date_from', '>=', date_from), ('date_to', '<=', date_to),
                                 ('state', '=', 'transfered'), ('employee_id', 'in', employees.ids),
                                 ('employee_id.bank_account_id.bank_id', '=', bank.id), '|',
                                 ('move_id.state', '=', 'posted'), ('payslip_run_id.move_id.state', '=', 'posted')])

                        elif salary:
                            payslips = self.sudo().env['hr.payslip'].search(
                                ['&', ('date_from', '>=', date_from), ('date_to', '<=', date_to),
                                 ('state', '=', 'transfered'),
                                 ('struct_id', 'in', salary_ids), ('employee_id.bank_account_id.bank_id', '=', bank.id),
                                 '|'
                                    , ('move_id.state', '=', 'posted'), ('payslip_run_id.move_id.state', '=', 'posted')
                                 ])
                        elif salary and employees:
                            payslips = self.sudo().env['hr.payslip'].search(
                                ['&', ('date_from', '>=', date_from), ('date_to', '<=', date_to),
                                 ('state', '=', 'transfered'), ('employee_id', 'in', employees.ids),
                                 ('struct_id', 'in', salary.ids),
                                 ('employee_id.bank_account_id.bank_id', '=', bank.id), '|',
                                 ('move_id.state', '=', 'posted'), ('payslip_run_id.move_id.state', '=', 'posted')])
                        else:
                            payslips = self.sudo().env['hr.payslip'].search(
                                ['&', ('date_from', '>=', date_from), ('date_to', '<=', date_to),
                                 ('state', '=', 'transfered'), ('employee_id.bank_account_id.bank_id', '=', bank.id),
                                 '|',
                                 ('move_id.state', '=', 'posted'), ('payslip_run_id.move_id.state', '=', 'posted')])

                    elif entry_type == 'unposted':
                        if employees:
                            payslips = self.sudo().env['hr.payslip'].search(
                                ['&', ('date_from', '>=', date_from), ('date_to', '<=', date_to),
                                 ('state', '=', 'transfered'), ('employee_id', 'in', employees.ids),
                                 ('employee_id.bank_account_id.bank_id', '=', bank.id), '|',
                                 ('move_id.state', '=', 'draft'), ('payslip_run_id.move_id.state', '=', 'draft'),
                                 ])

                        elif salary:
                            payslips = self.sudo().env['hr.payslip'].search(
                                ['&', ('date_from', '>=', date_from), ('date_to', '<=', date_to),
                                 ('state', '=', 'transfered'), ('employee_id.bank_account_id.bank_id', '=', bank.id),
                                 ('struct_id', 'in', salary_ids), '|',
                                 ('move_id.state', '=', 'draft'), ('payslip_run_id.move_id.state', '=', 'draft'),
                                 ])
                        elif salary and employees:
                            payslips = self.sudo().env['hr.payslip'].search(
                                ['&', ('date_from', '>=', date_from), ('date_to', '<=', date_to),
                                 ('state', '=', 'transfered'), ('employee_id', 'in', employees.ids),
                                 ('struct_id', 'in', salary.ids),
                                 ('employee_id.bank_account_id.bank_id', '=', bank.id), '|',
                                 ('move_id.state', '=', 'draft'), ('payslip_run_id.move_id.state', '=', 'draft')])
                        else:
                            payslips = self.sudo().env['hr.payslip'].search(
                                ['&', ('date_from', '>=', date_from), ('date_to', '<=', date_to),
                                 ('state', '=', 'transfered'), ('employee_id.bank_account_id.bank_id', '=', bank.id),
                                 '|',
                                 ('move_id.state', '=', 'draft'), ('payslip_run_id.move_id.state', '=', 'draft')])

                    for payslip in payslips:
                        tot_basic = 0.0
                        tot_housing = 0.0
                        tot_other = 0.0
                        tot_net = 0.0
                        tot_ded = 0.0

                        net = 0.0
                        basic = 0.0
                        housing = 0.0
                        other = 0.0
                        total = 0.0
                        Deduction_postive = 0.0
                        salary_rules = self.sudo().env['hr.salary.rule'].search([]).sorted(
                            key=lambda v: v.sequence).ids
                        payslip_line_obj = self.sudo().env['hr.payslip.line']
                        payslip_lines_ids = payslip_line_obj.sudo().search([('slip_id', '=', payslip.id)])
                        if not payslip_lines_ids:
                            continue

                        for payslip_line_rec in payslip_lines_ids:
                            if payslip_line_rec.salary_rule_id.id in salary_rules:
                                if payslip_line_rec.salary_rule_id.rules_type == 'salary':
                                    basic += payslip_line_rec.total
                                elif payslip_line_rec.salary_rule_id.rules_type == 'house':
                                    housing += payslip_line_rec.total
                            other = payslip.total_allowances - basic - housing
                            deduction = total - net
                            tot_net += net
                            tot_basic += basic
                            tot_housing += housing
                            tot_other += other
                            tot_ded += deduction

                            Deduction_postive = round(payslip.total_deductions + payslip.total_loans,2)
                            if Deduction_postive < 0.0:
                               Deduction_postive = -round(payslip.total_deductions + payslip.total_loans,2)

                        docs.append({
                            'ID': payslip.employee_id.emp_no,
                            'Name': payslip.employee_id.english_name,
                            'Account #': payslip.employee_id.bank_account_id.acc_number,
                            'Bank': payslip.employee_id.bank_account_id.bank_id.bic,
                            'Salary': payslip.total_sum,
                            'National': payslip.employee_id.saudi_number.saudi_id if payslip.employee_id.check_nationality == True else
                            payslip.employee_id.iqama_number.iqama_id,
                            'Basic': basic,
                            'Housing': housing,
                            'Other': round(other, 2),
                            #'Deduction': round(-(payslip.total_deductions + payslip.total_loans), 2),
                            'Deduction': Deduction_postive,
                            'Address': payslip.employee_id.branch_id.name if branch else payslip.employee_id.working_location.name,
                            'Pay Description': report_type,
                            'currency': payslip.employee_id.company_id.currency_id.name
                        })
                elif report_type == 'allowance':
                    allowances = self.sudo().env['hr.employee.reward'].search(
                        ['&', ('date', '>=', date_from), ('date', '<=', date_to), ('state', '=', 'done')
                         ])
                    for allowance in allowances:
                        reward_line_obj = self.sudo().env['lines.ids.reward']
                        if entry_type == 'all':
                            if employees:
                                reward_lines_ids = reward_line_obj.sudo().search(
                                    [('employee_reward_id', '=', allowance.id),
                                     ('employee_id.bank_account_id.bank_id', '=', bank.id),
                                     ('employee_id', 'in', employees.ids)])
                            else:
                                reward_lines_ids = reward_line_obj.sudo().search(
                                    [('employee_reward_id', '=', allowance.id),
                                     ('employee_id.bank_account_id.bank_id', '=', bank.id)])
                        elif entry_type == 'posted':
                            if employees:
                                reward_lines_ids = reward_line_obj.sudo().search(
                                    [('employee_reward_id', '=', allowance.id),
                                     ('employee_id.bank_account_id.bank_id', '=', bank.id),
                                     ('employee_id', 'in', employees.ids), ('move_id.state', '=', 'posted')])
                            else:
                                reward_lines_ids = reward_line_obj.sudo().search(
                                    [('employee_reward_id', '=', allowance.id), ('move_id.state', '=', 'posted'),
                                     ('employee_id.bank_account_id.bank_id', '=', bank.id)])

                        elif entry_type == 'unposted':
                            if employees:
                                reward_lines_ids = reward_line_obj.sudo().search(
                                    [('employee_reward_id', '=', allowance.id),
                                     ('employee_id.bank_account_id.bank_id', '=', bank.id),
                                     ('move_id.state', '=', 'draft'),
                                     ('employee_id', 'in', employees.ids)])
                            else:
                                reward_lines_ids = reward_line_obj.sudo().search(
                                    [('employee_reward_id', '=', allowance.id), ('move_id.state', '=', 'draft'),
                                     ('employee_id.bank_account_id.bank_id', '=', bank.id)])

                        if not reward_lines_ids:
                            continue

                        for reward in reward_lines_ids:
                            docs.append({
                                'ID': reward.employee_id.emp_no,
                                'Name': reward.employee_id.english_name,
                                'Account #': reward.employee_id.bank_account_id.acc_number,
                                'Bank': reward.employee_id.bank_account_id.bank_id.bic,
                                'Salary': reward.amount,
                                'National': reward.employee_id.saudi_number.saudi_id if reward.employee_id.check_nationality == True else
                                reward.employee_id.iqama_number.iqama_id,
                                'Basic': 0.0,
                                'Housing': 0.0,
                                'Other': 0.0,
                                'Deduction': 0.0,
                                'Address': reward.employee_id.branch_id.name if branch else reward.employee_id.working_location.name,
                                'Pay Description': report_type,
                                'currency': reward.employee_id.company_id.currency_id.name
                            })
                elif report_type == 'overtime':
                    overtime = self.sudo().env['employee.overtime.request'].search(
                        ['&', ('date_from', '>=', date_from), ('date_to', '<=', date_to),
                         ('transfer_type', '=', 'accounting'), ('state', '=', 'validated')
                         ])
                    for over in overtime:
                        reward_line_obj = self.sudo().env['line.ids.over.time']
                        if entry_type == 'all':
                            if employees:
                                overtime_lines_ids = reward_line_obj.sudo().search(
                                    [('employee_over_time_id', '=', over.id),
                                     ('employee_id.bank_account_id.bank_id', '=', bank.id),
                                     ('employee_id', 'in', employees.ids)])
                            else:
                                overtime_lines_ids = reward_line_obj.sudo().search(
                                    [('employee_over_time_id', '=', over.id),
                                     ('employee_id.bank_account_id.bank_id', '=', bank.id)])
                        elif entry_type == 'posted':
                            if employees:
                                overtime_lines_ids = reward_line_obj.sudo().search(
                                    [('employee_over_time_id', '=', over.id), ('move_id.state', '=', 'posted'),
                                     ('employee_id.bank_account_id.bank_id', '=', bank.id),
                                     ('employee_id', 'in', employees.ids)])
                            else:
                                overtime_lines_ids = reward_line_obj.sudo().search(
                                    [('employee_over_time_id', '=', over.id), ('move_id.state', '=', 'posted'),
                                     ('employee_id.bank_account_id.bank_id', '=', bank.id)])

                        elif entry_type == 'unposted':
                            if employees:
                                overtime_lines_ids = reward_line_obj.sudo().search(
                                    [('employee_over_time_id', '=', over.id), ('move_id.state', '=', 'draft'),
                                     ('employee_id.bank_account_id.bank_id', '=', bank.id),
                                     ('employee_id', 'in', employees.ids)])
                            else:
                                overtime_lines_ids = reward_line_obj.sudo().search(
                                    [('employee_over_time_id', '=', over.id), ('move_id.state', '=', 'draft'),
                                     ('employee_id.bank_account_id.bank_id', '=', bank.id)])

                        if not overtime_lines_ids:
                            continue

                        for ove in overtime_lines_ids:
                            docs.append({
                                'ID': ove.employee_id.emp_no,
                                'Name': ove.employee_id.english_name,
                                'Account #': ove.employee_id.bank_account_id.acc_number,
                                'Bank': ove.employee_id.bank_account_id.bank_id.bic,
                                'Salary': ove.price_hour,
                                'National': ove.employee_id.saudi_number.saudi_id if ove.employee_id.check_nationality == True else
                                ove.employee_id.iqama_number.iqama_id,
                                'Basic': 0.0,
                                'Housing': 0.0,
                                'Other': 0.0,
                                'Deduction': 0.0,
                                'Address': ove.employee_id.branch_id.name if branch else ove.employee_id.working_location.name,
                                'Pay Description': report_type,
                                'currency':  ove.employee_id.company_id.currency_id.name
                            })
                elif report_type == 'mission':
                    missions = self.sudo().env['hr.official.mission'].search(
                        ['&', ('date_from', '>=', date_from), ('date_to', '<=', date_to),
                         ('process_type', '=', 'mission'), ('state', '=', 'approve')
                         ])
                    for mission in missions:
                        mission_line_obj = self.sudo().env['hr.official.mission.employee']
                        if entry_type == 'all':
                            if employees:
                                mission_lines_ids = mission_line_obj.sudo().search(
                                    [('official_mission_id', '=', mission.id),
                                     ('employee_id.bank_account_id.bank_id', '=', bank.id),
                                     ('employee_id', 'in', employees.ids)])
                            else:
                                mission_lines_ids = mission_line_obj.sudo().search(
                                    [('official_mission_id', '=', mission.id),
                                     ('employee_id.bank_account_id.bank_id', '=', bank.id)])
                        elif entry_type == 'posted':
                            if employees:
                                mission_lines_ids = mission_line_obj.sudo().search(
                                    [('official_mission_id', '=', mission.id),
                                     ('employee_id.bank_account_id.bank_id', '=', bank.id),
                                     ('employee_id', 'in', employees.ids), ('account_move_id.state', '=', 'posted')])
                            else:
                                mission_lines_ids = mission_line_obj.sudo().search(
                                    [('official_mission_id', '=', mission.id), ('account_move_id.state', '=', 'posted'),
                                     ('employee_id.bank_account_id.bank_id', '=', bank.id)])
                        elif entry_type == 'unposted':
                            if employees:
                                mission_lines_ids = mission_line_obj.sudo().search(
                                    [('official_mission_id', '=', mission.id), ('account_move_id.state', '=', 'draft'),
                                     ('employee_id.bank_account_id.bank_id', '=', bank.id),
                                     ('employee_id', 'in', employees.ids)])
                            else:
                                mission_lines_ids = mission_line_obj.sudo().search(
                                    [('official_mission_id', '=', mission.id), ('account_move_id.state', '=', 'draft'),
                                     ('employee_id.bank_account_id.bank_id', '=', bank.id)])

                        if not mission_lines_ids:
                            continue

                        for miss in mission_lines_ids:
                            docs.append({
                                'ID': miss.employee_id.emp_no,
                                'Name': miss.employee_id.english_name,
                                'Account #': miss.employee_id.bank_account_id.acc_number,
                                'Bank': miss.employee_id.bank_account_id.bank_id.bic,
                                'Salary': miss.amount,
                                'National': miss.employee_id.saudi_number.saudi_id if miss.employee_id.check_nationality == True else
                                miss.employee_id.iqama_number.iqama_id,
                                'Basic': 0.0,
                                'Housing': 0.0,
                                'Other': 0.0,
                                'Deduction': 0.0,
                                'Address': miss.employee_id.branch_id.name if branch else miss.employee_id.working_location.name,
                                'Pay Description': report_type,
                                'currency':  miss.employee_id.company_id.currency_id.name
                            })
                elif report_type == 'training':
                    trainings = self.sudo().env['hr.official.mission'].search(
                        ['&', ('date_from', '>=', date_from), ('date_to', '<=', date_to),
                         ('process_type', '=', 'training'), ('state', '=', 'approve')
                         ])
                    for training in trainings:
                        training_line_obj = self.sudo().env['hr.official.mission.employee']
                        if entry_type == 'all':
                            if employees:
                                training_lines_ids = training_line_obj.sudo().search(
                                    [('official_mission_id', '=', training.id),
                                     ('employee_id.bank_account_id.bank_id', '=', bank.id),
                                     ('employee_id', 'in', employees.ids)])
                            else:
                                training_lines_ids = training_line_obj.sudo().search(
                                    [('official_mission_id', '=', training.id),
                                     ('employee_id.bank_account_id.bank_id', '=', bank.id)])
                        elif entry_type == 'posted':
                            if employees:
                                training_lines_ids = training_line_obj.sudo().search(
                                    [('official_mission_id', '=', training.id),
                                     ('employee_id.bank_account_id.bank_id', '=', bank.id),
                                     ('employee_id', 'in', employees.ids), ('account_move_id.state', '=', 'posted')])
                            else:
                                training_lines_ids = training_line_obj.sudo().search(
                                    [('official_mission_id', '=', training.id),
                                     ('employee_id.bank_account_id.bank_id', '=', bank.id),
                                     ('account_move_id.state', '=', 'posted')])
                        elif entry_type == 'unposted':
                            if employees:
                                training_lines_ids = training_line_obj.sudo().search(
                                    [('official_mission_id', '=', training.id), ('account_move_id.state', '=', 'draft'),
                                     ('employee_id.bank_account_id.bank_id', '=', bank.id),
                                     ('employee_id', 'in', employees.ids)])
                            else:
                                training_lines_ids = training_line_obj.sudo().search(
                                    [('official_mission_id', '=', training.id), ('account_move_id.state', '=', 'draft'),
                                     ('employee_id.bank_account_id.bank_id', '=', bank.id)])

                        if not training_lines_ids:
                            continue

                        for train in training_lines_ids:
                            docs.append({
                                'ID': train.employee_id.emp_no,
                                'Name': train.employee_id.english_name,
                                'Account #': train.employee_id.bank_account_id.acc_number,
                                'Bank': train.employee_id.bank_account_id.bank_id.bic,
                                'Salary': train.amount,
                                'National': train.employee_id.saudi_number.saudi_id if train.employee_id.check_nationality == True else
                                train.employee_id.iqama_number.iqama_id,
                                'Basic': 0.0,
                                'Housing': 0.0,
                                'Other': 0.0,
                                'Deduction': 0.0,
                                'Address': train.employee_id.branch_id.name if branch else train.employee_id.working_location.name,
                                'Pay Description': report_type,
                                'currency': train.employee_id.company_id.currency_id.name
                            })

                counter = docs.count
                data.append({
                    'docs': docs,

                    'bank': bank.name,
                    'report_type': report_type,
                    'no_details': no_details,
                    'bank_type': bank_type,
                    'counter': counter
                })

        else:
            docs = []
            if report_type == 'salary':
                if entry_type == 'all':
                    if employees:
                        payslips = self.sudo().env['hr.payslip'].search(
                            ['&', ('date_from', '>=', date_from), ('date_to', '<=', date_to),
                             ('state', '=', 'transfered'),
                             ('employee_id', 'in', employees.ids),
                             ('employee_id.bank_account_id.bank_id', 'in', all_bank.ids)])

                    elif salary:
                        payslips = self.sudo().env['hr.payslip'].search(
                            ['&', ('date_from', '>=', date_from), ('date_to', '<=', date_to),
                             ('state', '=', 'transfered'),
                             ('struct_id', 'in', salary_ids),
                             ('employee_id.bank_account_id.bank_id', 'in', all_bank.ids)])
                    elif salary and employees:
                        payslips = self.sudo().env['hr.payslip'].search(
                            ['&', ('date_from', '>=', date_from), ('date_to', '<=', date_to),
                             ('state', '=', 'transfered'),
                             ('employee_id', 'in', employees.ids), ('struct_id', 'in', salary.ids),
                             ('employee_id.bank_account_id.bank_id', 'in', all_bank.ids)])
                    else:
                        payslips = self.sudo().env['hr.payslip'].search(
                            ['&', ('date_from', '>=', date_from), ('date_to', '<=', date_to),
                             ('state', '=', 'transfered'),
                             ('employee_id.bank_account_id.bank_id', 'in', all_bank.ids)])
                elif entry_type == 'posted':
                    if employees:
                        payslips = self.sudo().env['hr.payslip'].search(
                            ['&', ('date_from', '>=', date_from), ('date_to', '<=', date_to),
                             ('state', '=', 'transfered'),
                             ('employee_id', 'in', employees.ids),
                             ('employee_id.bank_account_id.bank_id', 'in', all_bank.ids)
                                , '|',
                             ('move_id.state', '=', 'posted'), ('payslip_run_id.move_id.state', '=', 'posted')
                             ])

                    elif salary:
                        payslips = self.sudo().env['hr.payslip'].search(
                            ['&', ('date_from', '>=', date_from), ('date_to', '<=', date_to),
                             ('state', '=', 'transfered'), ('struct_id', 'in', salary_ids),
                             ('employee_id.bank_account_id.bank_id', 'in', all_bank.ids), '|',
                             ('move_id.state', '=', 'posted'), ('payslip_run_id.move_id.state', '=', 'posted')])
                    elif salary and employees:
                        payslips = self.sudo().env['hr.payslip'].search(
                            ['&', ('date_from', '>=', date_from), ('date_to', '<=', date_to),
                             ('state', '=', 'transfered'), ('employee_id', 'in', employees.ids),
                             ('struct_id', 'in', salary.ids),
                             ('employee_id.bank_account_id.bank_id', 'in', all_bank.ids), '|',
                             ('move_id.state', '=', 'posted'), ('payslip_run_id.move_id.state', '=', 'posted')])
                    else:
                        payslips = self.sudo().env['hr.payslip'].search(
                            ['&', ('date_from', '>=', date_from), ('date_to', '<=', date_to),
                             ('state', '=', 'transfered'),
                             ('employee_id.bank_account_id.bank_id', 'in', all_bank.ids)
                                , '|',
                             ('move_id.state', '=', 'posted'), ('payslip_run_id.move_id.state', '=', 'posted')
                             ])
                elif entry_type == 'unposted':
                    if employees:
                        payslips = self.sudo().env['hr.payslip'].search(
                            ['&', ('date_from', '>=', date_from), ('date_to', '<=', date_to),
                             ('state', '=', 'transfered'),
                             ('employee_id', 'in', employees.ids),
                             ('employee_id.bank_account_id.bank_id', 'in', all_bank.ids)
                                , '|',
                             ('move_id.state', '=', 'draft'), ('payslip_run_id.move_id.state', '=', 'draft')
                             ])

                    elif salary:
                        payslips = self.sudo().env['hr.payslip'].search(
                            ['&', ('date_from', '>=', date_from), ('date_to', '<=', date_to),
                             ('state', '=', 'transfered'),
                             ('struct_id', 'in', salary_ids),
                             ('employee_id.bank_account_id.bank_id', 'in', all_bank.ids)
                                , '|',
                             ('move_id.state', '=', 'draft'), ('payslip_run_id.move_id.state', '=', 'draft')
                             ])
                    elif salary and employees:
                        payslips = self.sudo().env['hr.payslip'].search(
                            ['&', ('date_from', '>=', date_from), ('date_to', '<=', date_to),
                             ('state', '=', 'transfered'),
                             ('employee_id', 'in', employees.ids), ('struct_id', 'in', salary.ids),
                             ('employee_id.bank_account_id.bank_id', 'in', all_bank.ids)
                                , '|',
                             ('move_id.state', '=', 'draft'), ('payslip_run_id.move_id.state', '=', 'draft')
                             ])
                    else:
                        payslips = self.sudo().env['hr.payslip'].search(
                            ['&', ('date_from', '>=', date_from), ('date_to', '<=', date_to),
                             ('state', '=', 'transfered'),
                             ('employee_id.bank_account_id.bank_id', 'in', all_bank.ids)
                                , '|',
                             ('move_id.state', '=', 'draft'), ('payslip_run_id.move_id.state', '=', 'draft')
                             ])

                for payslip in payslips:
                    tot_basic = 0.0
                    tot_housing = 0.0
                    tot_other = 0.0
                    tot_net = 0.0
                    tot_ded = 0.0
                    net = 0.0
                    basic = 0.0
                    housing = 0.0
                    other = 0.0
                    total = 0.0
                    Deduction_postive = 0.0
                    salary_rules = self.sudo().env['hr.salary.rule'].search([]).sorted(
                        key=lambda v: v.sequence).ids
                    payslip_line_obj = self.sudo().env['hr.payslip.line']
                    payslip_lines_ids = payslip_line_obj.sudo().search([('slip_id', '=', payslip.id)])
                    if not payslip_lines_ids:
                        continue

                    for payslip_line_rec in payslip_lines_ids:
                        if payslip_line_rec.salary_rule_id.id in salary_rules:
                            if payslip_line_rec.salary_rule_id.rules_type == 'salary':
                                basic += payslip_line_rec.total
                            elif payslip_line_rec.salary_rule_id.rules_type == 'house':
                                housing += payslip_line_rec.total
                        other = payslip.total_allowances - basic - housing
                        deduction = total - net
                        tot_net += net
                        tot_basic += basic
                        tot_housing += housing
                        tot_other += other
                        tot_ded += deduction

                        Deduction_postive= round(payslip.total_deductions + payslip.total_loans,2)
                        if Deduction_postive < 0.0:
                           Deduction_postive = -round(payslip.total_deductions + payslip.total_loans,2)
                    docs.append({
                        'ID': payslip.employee_id.emp_no,
                        'Name': payslip.employee_id.english_name,
                        'Account #': payslip.employee_id.bank_account_id.acc_number,
                        'Bank': payslip.employee_id.bank_account_id.bank_id.bic,
                        'Salary': payslip.total_sum,
                        'National': payslip.employee_id.saudi_number.saudi_id if payslip.employee_id.check_nationality == True else
                        payslip.employee_id.iqama_number.iqama_id,
                        'Basic': basic,
                        'Housing': housing,
                        'Other': round(other, 2),
                        #'Deduction': round(-(payslip.total_deductions + payslip.total_loans), 2),
                        'Deduction': Deduction_postive,
                        'Address': payslip.employee_id.branch_id.name if branch else payslip.employee_id.working_location.name,
                        'Pay Description': report_type,
                        'currency':  payslip.employee_id.company_id.currency_id.name
                    })
            elif report_type == 'allowance':
                allowances = self.sudo().env['hr.employee.reward'].search(
                    ['&', ('date', '>=', date_from), ('date', '<=', date_to), ('state', '=', 'done')
                     ])
                for allowance in allowances:
                    reward_line_obj = self.sudo().env['lines.ids.reward']
                    if entry_type == 'all':
                        if employees:
                            reward_lines_ids = reward_line_obj.sudo().search(
                                [('employee_reward_id', '=', allowance.id),
                                 ('employee_id.bank_account_id.bank_id', 'in', all_bank.ids),
                                 ('employee_id', 'in', employees.ids)])
                        else:
                            reward_lines_ids = reward_line_obj.sudo().search(
                                [('employee_reward_id', '=', allowance.id),
                                 ('employee_id.bank_account_id.bank_id', 'in', all_bank.ids)])
                    elif entry_type == 'posted':
                        if employees:
                            reward_lines_ids = reward_line_obj.sudo().search(
                                [('employee_reward_id', '=', allowance.id),
                                 ('employee_id.bank_account_id.bank_id', 'in', all_bank.ids),
                                 ('employee_id', 'in', employees.ids), ('move_id.state', '=', 'posted')])
                        else:
                            reward_lines_ids = reward_line_obj.sudo().search(
                                [('employee_reward_id', '=', allowance.id), ('move_id.state', '=', 'posted'),
                                 ('employee_id.bank_account_id.bank_id', 'in', all_bank.ids)])
                    elif entry_type == 'unposted':
                        if employees:
                            reward_lines_ids = reward_line_obj.sudo().search(
                                [('employee_reward_id', '=', allowance.id), ('move_id.state', '=', 'draft'),
                                 ('employee_id.bank_account_id.bank_id', 'in', all_bank.ids),
                                 ('employee_id', 'in', employees.ids)])
                        else:
                            reward_lines_ids = reward_line_obj.sudo().search(
                                [('employee_reward_id', '=', allowance.id), ('move_id.state', '=', 'draft'),
                                 ('employee_id.bank_account_id.bank_id', 'in', all_bank.ids)])

                    if not reward_lines_ids:
                        continue

                    for reward in reward_lines_ids:
                        docs.append({
                            'ID': reward.employee_id.emp_no,
                            'Name': reward.employee_id.english_name,
                            'Account #': reward.employee_id.bank_account_id.acc_number,
                            'Bank': reward.employee_id.bank_account_id.bank_id.bic,
                            'Salary': reward.amount,
                            'National': reward.employee_id.saudi_number.saudi_id if reward.employee_id.check_nationality == True else
                            reward.employee_id.iqama_number.iqama_id,
                            'Basic': 0.0,
                            'Housing': 0.0,
                            'Other': 0.0,
                            'Deduction': 0.0,
                            'Address': reward.employee_id.branch_id.name if branch else reward.employee_id.working_location.name,
                            'Pay Description': report_type,
                            'currency': reward.employee_id.company_id.currency_id.name
                        })
            elif report_type == 'overtime':
                overtime = self.sudo().env['employee.overtime.request'].search(
                    ['&', ('date_from', '>=', date_from), ('date_to', '<=', date_to),
                     ('transfer_type', '=', 'accounting'), ('state', '=', 'validated')
                     ])
                for over in overtime:
                    reward_line_obj = self.sudo().env['line.ids.over.time']
                    if entry_type == 'all':
                        if employees:
                            overtime_lines_ids = reward_line_obj.sudo().search(
                                [('employee_over_time_id', '=', over.id),
                                 ('employee_id.bank_account_id.bank_id', 'in', all_bank.ids),
                                 ('employee_id', 'in', employees.ids)])
                        else:
                            overtime_lines_ids = reward_line_obj.sudo().search(
                                [('employee_over_time_id', '=', over.id),
                                 ('employee_id.bank_account_id.bank_id', 'in', all_bank.ids)])
                    elif entry_type == 'posted':
                        if employees:
                            overtime_lines_ids = reward_line_obj.sudo().search(
                                [('employee_over_time_id', '=', over.id),
                                 ('employee_id.bank_account_id.bank_id', 'in', all_bank.ids),
                                 ('employee_id', 'in', employees.ids), ('move_id.state', '=', 'posted')])
                        else:
                            overtime_lines_ids = reward_line_obj.sudo().search(
                                [('employee_over_time_id', '=', over.id), ('move_id.state', '=', 'posted'),
                                 ('employee_id.bank_account_id.bank_id', 'in', all_bank.ids)])
                    elif entry_type == 'unposted':
                        if employees:
                            overtime_lines_ids = reward_line_obj.sudo().search(
                                [('employee_over_time_id', '=', over.id),
                                 ('employee_id.bank_account_id.bank_id', 'in', all_bank.ids),
                                 ('employee_id', 'in', employees.ids), ('move_id.state', '=', 'draft')])
                        else:
                            overtime_lines_ids = reward_line_obj.sudo().search(
                                [('employee_over_time_id', '=', over.id), ('move_id.state', '=', 'draft'),
                                 ('employee_id.bank_account_id.bank_id', 'in', all_bank.ids)])

                    if not overtime_lines_ids:
                        continue

                    for ove in overtime_lines_ids:
                        docs.append({
                            'ID': ove.employee_id.emp_no,
                            'Name': ove.employee_id.english_name,
                            'Account #': ove.employee_id.bank_account_id.acc_number,
                            'Bank': ove.employee_id.bank_account_id.bank_id.bic,
                            'Salary': ove.price_hour,
                            'National': ove.employee_id.saudi_number.saudi_id if ove.employee_id.check_nationality == True else
                            ove.employee_id.iqama_number.iqama_id,
                            'Basic': 0.0,
                            'Housing': 0.0,
                            'Other': 0.0,
                            'Deduction': 0.0,
                            'Address': ove.employee_id.branch_id.name if branch else ove.employee_id.working_location.name,
                            'Pay Description': report_type,
                            'currency':ove.employee_id.company_id.currency_id.name
                        })
            elif report_type == 'mission':
                missions = self.sudo().env['hr.official.mission'].search(
                    ['&', ('date_from', '>=', date_from), ('date_to', '<=', date_to), ('process_type', '=', 'mission'),
                     ('state', '=', 'approve')
                     ])
                for mission in missions:
                    mission_line_obj = self.sudo().env['hr.official.mission.employee']
                    if entry_type == 'all':
                        if employees:
                            mission_lines_ids = mission_line_obj.sudo().search(
                                [('official_mission_id', '=', mission.id),
                                 ('employee_id.bank_account_id.bank_id', 'in', all_bank.ids),
                                 ('employee_id', 'in', employees.ids)])
                        else:
                            mission_lines_ids = mission_line_obj.sudo().search(
                                [('official_mission_id', '=', mission.id),
                                 ('employee_id.bank_account_id.bank_id', 'in', all_bank.ids)])
                    elif entry_type == 'posted':
                        if employees:
                            mission_lines_ids = mission_line_obj.sudo().search(
                                [('official_mission_id', '=', mission.id),
                                 ('employee_id.bank_account_id.bank_id', 'in', all_bank.ids),
                                 ('employee_id', 'in', employees.ids), ('account_move_id.state', '=', 'posted')])
                        else:
                            mission_lines_ids = mission_line_obj.sudo().search(
                                [('official_mission_id', '=', mission.id), ('account_move_id.state', '=', 'posted'),
                                 ('employee_id.bank_account_id.bank_id', 'in', all_bank.ids)])
                    elif entry_type == 'unposted':
                        if employees:
                            mission_lines_ids = mission_line_obj.sudo().search(
                                [('official_mission_id', '=', mission.id), ('account_move_id.state', '=', 'draft'),
                                 ('employee_id.bank_account_id.bank_id', 'in', all_bank.ids),
                                 ('employee_id', 'in', employees.ids)])
                        else:
                            mission_lines_ids = mission_line_obj.sudo().search(
                                [('official_mission_id', '=', mission.id), ('account_move_id.state', '=', 'draft'),
                                 ('employee_id.bank_account_id.bank_id', 'in', all_bank.ids)])

                    if not mission_lines_ids:
                        continue

                    for miss in mission_lines_ids:
                        docs.append({
                            'ID': miss.employee_id.emp_no,
                            'Name': miss.employee_id.english_name,
                            'Account #': miss.employee_id.bank_account_id.acc_number,
                            'Bank': miss.employee_id.bank_account_id.bank_id.bic,
                            'Salary': miss.amount,
                            'National': miss.employee_id.saudi_number.saudi_id if miss.employee_id.check_nationality == True else
                            miss.employee_id.iqama_number.iqama_id,
                            'Basic': 0.0,
                            'Housing': 0.0,
                            'Other': 0.0,
                            'Deduction': 0.0,
                            'Address': miss.employee_id.branch_id.name if branch else miss.employee_id.working_location.name,
                            'Pay Description': report_type,
                            'currency': miss.employee_id.company_id.currency_id.name
                        })
            elif report_type == 'training':
                trainings = self.sudo().env['hr.official.mission'].search(
                    ['&', ('date_from', '>=', date_from), ('date_to', '<=', date_to),
                     ('process_type', '=', 'training'), ('state', '=', 'approve')
                     ])
                for training in trainings:
                    training_line_obj = self.sudo().env['hr.official.mission.employee']
                    if entry_type == 'all':
                        if employees:
                            training_lines_ids = training_line_obj.sudo().search(
                                [('official_mission_id', '=', training.id),
                                 ('employee_id.bank_account_id.bank_id', 'in', all_bank.ids),
                                 ('employee_id', 'in', employees.ids)])
                        else:
                            training_lines_ids = training_line_obj.sudo().search(
                                [('official_mission_id', '=', training.id),
                                 ('employee_id.bank_account_id.bank_id', 'in', all_bank.ids)])
                    elif entry_type == 'posted':
                        if employees:
                            training_lines_ids = training_line_obj.sudo().search(
                                [('official_mission_id', '=', training.id),
                                 ('employee_id.bank_account_id.bank_id', 'in', all_bank.ids),
                                 ('employee_id', 'in', employees.ids), ('account_move_id.state', '=', 'posted')])
                        else:
                            training_lines_ids = training_line_obj.sudo().search(
                                [('official_mission_id', '=', training.id),
                                 ('employee_id.bank_account_id.bank_id', 'in', all_bank.ids),
                                 ('account_move_id.state', '=', 'posted')])
                    elif entry_type == 'unposted':
                        if employees:
                            training_lines_ids = training_line_obj.sudo().search(
                                [('official_mission_id', '=', training.id),
                                 ('employee_id.bank_account_id.bank_id', 'in', all_bank.ids),
                                 ('employee_id', 'in', employees.ids), ('account_move_id.state', '=', 'draft')])
                        else:
                            training_lines_ids = training_line_obj.sudo().search(
                                [('official_mission_id', '=', training.id),
                                 ('employee_id.bank_account_id.bank_id', 'in', all_bank.ids),
                                 ('account_move_id.state', '=', 'draft')])

                    if not training_lines_ids:
                        continue

                    for train in training_lines_ids:
                        docs.append({
                            'ID': train.employee_id.emp_no,
                            'Name': train.employee_id.english_name,
                            'Account #': train.employee_id.bank_account_id.acc_number,
                            'Bank': train.employee_id.bank_account_id.bank_id.bic,
                            'Salary': train.amount,
                            'National': train.employee_id.saudi_number.saudi_id if train.employee_id.check_nationality == True else
                            train.employee_id.iqama_number.iqama_id,
                            'Basic': 0.0,
                            'Housing': 0.0,
                            'Other': 0.0,
                            'Deduction': 0.0,
                            'Address': train.employee_id.branch_id.name if branch else train.employee_id.working_location.name,
                            'Pay Description': report_type,
                            'currency': train.employee_id.company_id.currency_id.name
                        })

            # counter = docs.count('ID')+1
            # print("###########################",counter)
            data.append({
                'docs': docs,
                'bank': '',
                'report_type': report_type,
                'no_details': no_details,
                # 'counter': counter
            })
            total_docs_count = sum(len(entry['docs']) for entry in data)
            total_amount_salary = sum(doc['Salary'] for entry in data for doc in entry['docs'])
            number_of_records = total_docs_count+2
        return {
            'banks': banks,
            'data': data,
            'date_from': date_from,
            'date_to': date_to,
            'company_id': company_id,
            'counter':total_docs_count,
            'number_of_records':number_of_records,
            'total_amount_salary':total_amount_salary
        }


class PayrollXlsx(models.AbstractModel):
    _name = 'report.exp_payroll_custom.report_payroll_bank_xlsx'
    _inherit = 'report.report_xlsx.abstract'

    def generate_xlsx_report(self, workbook, data, payslips):
        emp_ids = data['employees']
        bank_ids = data['banks']
        salary_ids = data['salary']
        date_from = data['date_from']
        date_to = data['date_to']
        company_id= data['company_id']
        employees = self.sudo().env['hr.employee'].browse(emp_ids)
        salary = self.sudo().env['hr.payroll.structure'].browse(salary_ids)
        banks = self.sudo().env['res.bank'].browse(bank_ids)
        salary_ids = self.sudo().env['hr.payroll.structure'].browse(salary)
        no_details = data['no_details']
        report_type = data['report_type']
        entry_type = data['entry_type']
        bank_type = data['bank_type']
        all_bank = self.sudo().env['res.bank'].search([])
        branch = self.env['ir.module.module'].sudo().search(
            [('state', '=', 'installed'), ('name', '=', 'bi_odoo_multi_branch_hr')])

        company_id = self.env['res.company'].search([('id', '=', company_id)])


        sheet = workbook.add_worksheet('Bank Sheet')
        format1 = workbook.add_format( {'font_size': 10, 'bottom': True, 'right': True, 'left': True, 'top': True, 'align': 'center','bold': True})
        format2 = workbook.add_format({'font_size': 10, 'bottom': True, 'right': True, 'left': True, 'top': True, 'align': 'center', 'bold': True})
        format3 = workbook.add_format({'bottom': True, 'align': 'center', 'bold': True, })
        format4 = workbook.add_format({'font_size': 10, 'bottom': True, 'right': True, 'left': True, 'top': True, 'align': 'center','bold': True})
        format2.set_align('center')
        format2.set_align('vcenter')
        format2.set_color('white')
        format2.set_bg_color('blue')
        format4.set_align('center')
        format4.set_align('vcenter')
        format4.set_color('white')
        format4.set_bg_color('green')
        if bank_type == 'riyadh':
            if report_type == 'salary':
                sheet.merge_range('E3:H3', (_("مسير البنك للرواتب")) + "  " + date_from + '  -  ' + date_to, format4)
            if report_type == 'allowance':
                sheet.merge_range('E3:H3', (_("مسير البنك للحوافز")) + "  " + date_from + '  -  ' + date_to, format4)
            if report_type == 'overtime':
                sheet.merge_range('E3:H3', (_("مسير البنك للعمل الإضافي")) + "  " + date_from + '  -  ' + date_to, format4)
            if report_type == 'training':
                sheet.merge_range('E3:H3', (_("مسير البنك للتدريب")) + "  " + date_from + '  -  ' + date_to, format4)
            if report_type == 'mission':
                sheet.merge_range('E3:H3', (_("مسير البنك لمهام العمل")) + "  " + date_from + '  -  ' + date_to, format4)
        else:
            if report_type == 'salary':
                sheet.merge_range('E3:H3', (_("مسير البنك للرواتب")) + "  " + date_from + '  -  ' + date_to, format2)
            if report_type == 'allowance':
                sheet.merge_range('E3:H3', (_("مسير البنك للحوافز")) + "  " + date_from + '  -  ' + date_to, format2)
            if report_type == 'overtime':
                sheet.merge_range('E3:H3', (_("مسير البنك للعمل الإضافي")) + "  " + date_from + '  -  ' + date_to, format2)
            if report_type == 'training':
                sheet.merge_range('E3:H3', (_("مسير البنك للتدريب")) + "  " + date_from + '  -  ' + date_to, format2)
            if report_type == 'mission':
                sheet.merge_range('E3:H3', (_("مسير البنك لمهام العمل")) + "  " + date_from + '  -  ' + date_to, format2)




        sheet.set_column(2, 11, 20)
        row = 2
        if not no_details:
            for bank in banks:
                row += 3
                if bank_type == 'rajhi':
                    sheet.write(row - 1, 1, bank.name, format3)
                    sheet.write(row, 2, 'Bank', format2)
                    sheet.write(row, 3, 'Account #', format2)
                    sheet.write(row, 4, 'Employee Name', format2)
                    sheet.write(row, 5, 'Employee Number', format2)
                    sheet.write(row, 6, 'Legal #', format2)
                    sheet.write(row, 7, 'Amount', format2)
                    sheet.write(row, 8, 'Employee Basic Salary', format2)
                    sheet.write(row, 9, 'Housing Allowance', format2)
                    sheet.write(row, 10, 'Other Earnings', format2)
                    sheet.write(row, 11, 'Deductions', format2)
                    row += 1
                    sheet.write(row, 2, 'البنك', format2)
                    sheet.write(row, 3, 'رقم الحساب', format2)
                    sheet.write(row, 4, 'إسم الموظف', format2)
                    sheet.write(row, 5, 'الرقم الوظيفي', format2)
                    sheet.write(row, 6, 'رقم الهويه/الإقامة', format2)
                    sheet.write(row, 7, 'المبلغ', format2)
                    sheet.write(row, 8, 'الراتب الاساسى', format2)
                    sheet.write(row, 9, 'بدل السكن', format2)
                    sheet.write(row, 10, 'دخل اخر', format2)
                    sheet.write(row, 11, 'الخصومات', format2)
                elif bank_type == 'alahli':
                    sheet.write(row - 1, 1, bank.name, format3)
                    sheet.write(row, 2, 'Bank', format1)
                    sheet.write(row, 3, 'Account Number', format1)
                    sheet.write(row, 4, 'Total Salary', format1)
                    sheet.write(row, 5, 'Transaction Reference', format1)
                    sheet.write(row, 6, 'Employee Name', format1)
                    sheet.write(row, 7, 'National ID/Iqama ID', format1)
                    sheet.write(row, 8, 'Employee Address', format1)
                    sheet.write(row, 9, 'Basic Salary', format1)
                    sheet.write(row, 10, 'Housing Allowance', format1)
                    sheet.write(row, 11, 'Other Earnings', format1)
                    sheet.write(row, 12, 'Deductions', format1)
                elif bank_type == 'riyadh':
                    sheet.write(row - 1, 1, bank.name, format3)
                    sheet.write(row, 2, 'SN', format4)
                    sheet.write(row, 3, 'هوية المستفيد/ المرجع', format4)
                    sheet.write(row, 4, 'المستفيد / اسم الموظف', format4)
                    sheet.write(row, 5, 'رقم الحساب ', format4)
                    sheet.write(row, 6, 'رمز البنك', format4)
                    sheet.write(row, 7, 'إجمالي المبلغ', format4)
                    sheet.write(row, 8, 'الراتب الأساسي', format4)
                    sheet.write(row, 9, 'بدل السكن', format4)
                    sheet.write(row, 10, 'دخل آخر', format4)
                    sheet.write(row, 11, 'الخصومات', format4)
                    sheet.write(row, 12, 'العنوان', format4)
                    sheet.write(row, 13, 'العملة', format4)
                    sheet.write(row, 14, 'الحالة', format4)
                    sheet.write(row, 15, 'وصف الدفع', format4)
                    sheet.write(row, 16, 'مرجع الدفع', format4)
                if report_type == 'salary':
                    if entry_type == 'all':
                        if employees:
                            payslip_ids = self.sudo().env['hr.payslip'].search(
                                ['&', ('date_from', '>=', date_from), ('date_to', '<=', date_to),
                                 ('state', '=', 'transfered'), ('employee_id', 'in', employees.ids),
                                 ('employee_id.bank_account_id.bank_id', '=', bank.id)
                                 ])

                        elif salary:
                            payslip_ids = self.sudo().env['hr.payslip'].search(
                                ['&', ('date_from', '>=', date_from), ('date_to', '<=', date_to),
                                 ('state', '=', 'transfered'), ('struct_id', 'in', salary_ids),
                                 ('employee_id.bank_account_id.bank_id', '=', bank.id)])
                        elif salary and employees:
                            payslip_ids = self.sudo().env['hr.payslip'].search(
                                ['&', ('date_from', '>=', date_from), ('date_to', '<=', date_to),
                                 ('state', '=', 'transfered'), ('employee_id', 'in', employees.ids),
                                 ('struct_id', 'in', salary.ids),
                                 ('employee_id.bank_account_id.bank_id', '=', bank.id)])
                        else:
                            payslip_ids = self.sudo().env['hr.payslip'].search(
                                ['&', ('date_from', '>=', date_from), ('date_to', '<=', date_to),
                                 ('state', '=', 'transfered'), ('employee_id.bank_account_id.bank_id', '=', bank.id)])
                    elif entry_type == 'posted':
                        if employees:
                            payslip_ids = self.sudo().env['hr.payslip'].search(
                                [('date_from', '>=', date_from), ('date_to', '<=', date_to),
                                 ('state', '=', 'transfered'), ('employee_id', 'in', employees.ids),
                                 ('employee_id.bank_account_id.bank_id', '=', bank.id), '|',
                                 ('move_id.state', '=', 'posted'), ('payslip_run_id.move_id.state', '=', 'posted')])

                        elif salary:
                            payslip_ids = self.sudo().env['hr.payslip'].search(
                                ['&', ('date_from', '>=', date_from), ('date_to', '<=', date_to),
                                 ('state', '=', 'transfered'),
                                 ('struct_id', 'in', salary_ids), ('employee_id.bank_account_id.bank_id', '=', bank.id),
                                 '|'
                                    , ('move_id.state', '=', 'posted'), ('payslip_run_id.move_id.state', '=', 'posted')
                                 ])
                        elif salary and employees:
                            payslip_ids = self.sudo().env['hr.payslip'].search(
                                ['&', ('date_from', '>=', date_from), ('date_to', '<=', date_to),
                                 ('state', '=', 'transfered'), ('employee_id', 'in', employees.ids),
                                 ('struct_id', 'in', salary.ids),
                                 ('employee_id.bank_account_id.bank_id', '=', bank.id), '|',
                                 ('move_id.state', '=', 'posted'), ('payslip_run_id.move_id.state', '=', 'posted')])
                        else:
                            payslip_ids = self.sudo().env['hr.payslip'].search(
                                ['&', ('date_from', '>=', date_from), ('date_to', '<=', date_to),
                                 ('state', '=', 'transfered'), ('employee_id.bank_account_id.bank_id', '=', bank.id),
                                 '|',
                                 ('move_id.state', '=', 'posted'), ('payslip_run_id.move_id.state', '=', 'posted')])

                    elif entry_type == 'unposted':
                        if employees:
                            payslip_ids = self.sudo().env['hr.payslip'].search(
                                ['&', ('date_from', '>=', date_from), ('date_to', '<=', date_to),
                                 ('state', '=', 'transfered'), ('employee_id', 'in', employees.ids),
                                 ('employee_id.bank_account_id.bank_id', '=', bank.id), '|',
                                 ('move_id.state', '=', 'draft'), ('payslip_run_id.move_id.state', '=', 'draft'),
                                 ])

                        elif salary:
                            payslip_ids = self.sudo().env['hr.payslip'].search(
                                ['&', ('date_from', '>=', date_from), ('date_to', '<=', date_to),
                                 ('state', '=', 'transfered'), ('employee_id.bank_account_id.bank_id', '=', bank.id),
                                 ('struct_id', 'in', salary_ids), '|',
                                 ('move_id.state', '=', 'draft'), ('payslip_run_id.move_id.state', '=', 'draft'),
                                 ])
                        elif salary and employees:
                            payslip_ids = self.sudo().env['hr.payslip'].search(
                                ['&', ('date_from', '>=', date_from), ('date_to', '<=', date_to),
                                 ('state', '=', 'transfered'), ('employee_id', 'in', employees.ids),
                                 ('struct_id', 'in', salary.ids),
                                 ('employee_id.bank_account_id.bank_id', '=', bank.id), '|',
                                 ('move_id.state', '=', 'draft'), ('payslip_run_id.move_id.state', '=', 'draft')])
                        else:
                            payslip_ids = self.sudo().env['hr.payslip'].search(
                                ['&', ('date_from', '>=', date_from), ('date_to', '<=', date_to),
                                 ('state', '=', 'transfered'), ('employee_id.bank_account_id.bank_id', '=', bank.id),
                                 '|',
                                 ('move_id.state', '=', 'draft'), ('payslip_run_id.move_id.state', '=', 'draft')])

                    salary_rules = self.sudo().env['hr.salary.rule'].search([]).sorted(
                        key=lambda v: v.sequence).ids
                    payslip_line_obj = self.sudo().env['hr.payslip.line']
                    sn = 0o001
                    for payslip in payslip_ids:
                        basic = 0.0
                        housing = 0.0
                        payslip_lines_ids = payslip_line_obj.sudo().search([('slip_id', '=', payslip.id)])
                        if not payslip_lines_ids:
                            continue
                        for payslip_line_rec in payslip_lines_ids:
                            if payslip_line_rec.salary_rule_id.id in salary_rules:
                                if payslip_line_rec.salary_rule_id.rules_type == 'salary':
                                    basic += payslip_line_rec.total
                                elif payslip_line_rec.salary_rule_id.rules_type == 'house':
                                    housing += payslip_line_rec.total
                        other = round((payslip.total_allowances - basic - housing), 2)
                        data_list = [payslip.employee_id.emp_no,
                                     payslip.employee_id.name or ' ',
                                     payslip.employee_id.bank_account_id.acc_number or ' ',
                                     payslip.employee_id.bank_account_id.bank_id.bic,
                                     payslip.total_sum,
                                     payslip.employee_id.saudi_number.saudi_id if payslip.employee_id.check_nationality == True else payslip.employee_id.iqama_number.iqama_id,
                                     basic, housing, other, round((payslip.total_deductions + payslip.total_loans), 2),
                                     payslip.employee_id.branch_id.name if branch else payslip.employee_id.working_location.name,
                                     company_id.currency_id.name,'Active']

                        col = 1
                        row += 1
                        col += 1
                        if bank_type == 'rajhi':
                            sheet.write(row, 2, data_list[3], format1)
                            sheet.write(row, 3, data_list[2], format1)
                            sheet.write(row, 4, data_list[1], format1)
                            sheet.write(row, 5, data_list[0], format1)
                            sheet.write(row, 6, data_list[5], format1)
                            sheet.write(row, 7, data_list[4], format1)
                            sheet.write(row, 8, data_list[6], format1)
                            sheet.write(row, 9, data_list[7], format1)
                            sheet.write(row, 10, data_list[8], format1)
                            sheet.write(row, 11, data_list[9], format1)
                        elif bank_type == 'alahli':
                            sheet.write(row, 2, data_list[3], format1)
                            sheet.write(row, 3, data_list[2], format1)
                            sheet.write(row, 4, data_list[4], format1)
                            sheet.write(row, 5, data_list[0], format1)
                            sheet.write(row, 6, data_list[1], format1)
                            sheet.write(row, 7, data_list[5], format1)
                            sheet.write(row, 8, data_list[10], format1)
                            sheet.write(row, 9, data_list[6], format1)
                            sheet.write(row, 10, data_list[7], format1)
                            sheet.write(row, 11, data_list[8], format1)
                            sheet.write(row, 12, data_list[9], format1)
                        elif bank_type == 'riyadh':
                            sheet.write(row, 2, sn, format1)
                            sheet.write(row, 3, data_list[5], format1)
                            sheet.write(row, 4, data_list[1], format1)
                            sheet.write(row, 5, data_list[2], format1)
                            sheet.write(row, 6, data_list[3], format1)
                            sheet.write(row, 7, data_list[4], format1)
                            sheet.write(row, 8, data_list[6], format1)
                            sheet.write(row, 9, data_list[7], format1)
                            sheet.write(row, 10, data_list[8], format1)
                            sheet.write(row, 11, data_list[9], format1)
                            sheet.write(row, 12, data_list[5], format1)
                            sheet.write(row, 13, data_list[11], format1)
                            sheet.write(row, 14, data_list[12], format1)
                            sheet.write(row, 15, report_type, format1)
                            sheet.write(row, 16, data_list[0], format1)
                            sn += 1
                elif report_type == 'allowance':
                    allowances = self.sudo().env['hr.employee.reward'].search(
                        ['&', ('date', '>=', date_from), ('date', '<=', date_to), ('state', '=', 'done')
                         ])
                    for allowance in allowances:
                        reward_line_obj = self.sudo().env['lines.ids.reward']
                        if entry_type == 'all':
                            if employees:
                                reward_lines_ids = reward_line_obj.sudo().search(
                                    [('employee_reward_id', '=', allowance.id),
                                     ('employee_id.bank_account_id.bank_id', '=', bank.id),
                                     ('employee_id', 'in', employees.ids)])
                            else:
                                reward_lines_ids = reward_line_obj.sudo().search(
                                    [('employee_reward_id', '=', allowance.id),
                                     ('employee_id.bank_account_id.bank_id', '=', bank.id)])
                        elif entry_type == 'posted':
                            if employees:
                                reward_lines_ids = reward_line_obj.sudo().search(
                                    [('employee_reward_id', '=', allowance.id),
                                     ('employee_id.bank_account_id.bank_id', '=', bank.id),
                                     ('employee_id', 'in', employees.ids), ('move_id.state', '=', 'posted')])
                            else:
                                reward_lines_ids = reward_line_obj.sudo().search(
                                    [('employee_reward_id', '=', allowance.id), ('move_id.state', '=', 'posted'),
                                     ('employee_id.bank_account_id.bank_id', '=', bank.id)])

                        elif entry_type == 'unposted':
                            if employees:
                                reward_lines_ids = reward_line_obj.sudo().search(
                                    [('employee_reward_id', '=', allowance.id),
                                     ('employee_id.bank_account_id.bank_id', '=', bank.id),
                                     ('move_id.state', '=', 'draft'),
                                     ('employee_id', 'in', employees.ids)])
                            else:
                                reward_lines_ids = reward_line_obj.sudo().search(
                                    [('employee_reward_id', '=', allowance.id), ('move_id.state', '=', 'draft'),
                                     ('employee_id.bank_account_id.bank_id', '=', bank.id)])

                        if not reward_lines_ids:
                            continue
                        sn = 0o001
                        for reward in reward_lines_ids:
                            data_list = [reward.employee_id.emp_no, reward.employee_id.name or ' ',
                                         reward.employee_id.bank_account_id.acc_number or ' ',
                                         reward.employee_id.bank_account_id.bank_id.bic,
                                         round(reward.amount, 2),
                                         reward.employee_id.saudi_number.saudi_id if reward.employee_id.check_nationality == True else reward.employee_id.iqama_number.iqama_id,
                                         0.0, 0.0, 0.0, 0.0,
                                         reward.employee_id.branch_id.name if branch else reward.employee_id.working_location.name,
                                         company_id.currency_id.name,'Active']
                            col = 1
                            row += 1
                            col += 1
                            if bank_type == 'rajhi':
                                sheet.write(row, 2, data_list[3], format1)
                                sheet.write(row, 3, data_list[2], format1)
                                sheet.write(row, 4, data_list[1], format1)
                                sheet.write(row, 5, data_list[0], format1)
                                sheet.write(row, 6, data_list[5], format1)
                                sheet.write(row, 7, data_list[4], format1)
                                sheet.write(row, 8, data_list[6], format1)
                                sheet.write(row, 9, data_list[7], format1)
                                sheet.write(row, 10, data_list[8], format1)
                                sheet.write(row, 11, data_list[9], format1)
                            elif bank_type == 'alahli':
                                sheet.write(row, 2, data_list[3], format1)
                                sheet.write(row, 3, data_list[2], format1)
                                sheet.write(row, 4, data_list[4], format1)
                                sheet.write(row, 5, data_list[0], format1)
                                sheet.write(row, 6, data_list[1], format1)
                                sheet.write(row, 7, data_list[5], format1)
                                sheet.write(row, 8, data_list[10], format1)
                                sheet.write(row, 9, data_list[6], format1)
                                sheet.write(row, 10, data_list[7], format1)
                                sheet.write(row, 11, data_list[8], format1)
                                sheet.write(row, 12, data_list[9], format1)
                            elif bank_type == 'riyadh':
                                sheet.write(row, 2, sn, format1)
                                sheet.write(row, 3, data_list[5], format1)
                                sheet.write(row, 4, data_list[1], format1)
                                sheet.write(row, 5, data_list[2], format1)
                                sheet.write(row, 6, data_list[3], format1)
                                sheet.write(row, 7, data_list[4], format1)
                                sheet.write(row, 8, data_list[6], format1)
                                sheet.write(row, 9, data_list[7], format1)
                                sheet.write(row, 10, data_list[8], format1)
                                sheet.write(row, 11, data_list[9], format1)
                                sheet.write(row, 12, data_list[5], format1)
                                sheet.write(row, 13, data_list[12], format1)
                                sheet.write(row, 14, data_list[13], format1)
                                sheet.write(row, 15, report_type, format1)
                                sheet.write(row, 16, data_list[0], format1)
                                sn += 1
                elif report_type == 'overtime':
                    overtime = self.sudo().env['employee.overtime.request'].search(
                        ['&', ('date_from', '>=', date_from), ('date_to', '<=', date_to),
                         ('transfer_type', '=', 'accounting'), ('state', '=', 'validated')
                         ])
                    for over in overtime:
                        reward_line_obj = self.sudo().env['line.ids.over.time']
                        if entry_type == 'all':
                            if employees:
                                overtime_lines_ids = reward_line_obj.sudo().search(
                                    [('employee_over_time_id', '=', over.id),
                                     ('employee_id.bank_account_id.bank_id', '=', bank.id),
                                     ('employee_id', 'in', employees.ids)])
                            else:
                                overtime_lines_ids = reward_line_obj.sudo().search(
                                    [('employee_over_time_id', '=', over.id),
                                     ('employee_id.bank_account_id.bank_id', '=', bank.id)])
                        elif entry_type == 'posted':
                            if employees:
                                overtime_lines_ids = reward_line_obj.sudo().search(
                                    [('employee_over_time_id', '=', over.id), ('move_id.state', '=', 'posted'),
                                     ('employee_id.bank_account_id.bank_id', '=', bank.id),
                                     ('employee_id', 'in', employees.ids)])
                            else:
                                overtime_lines_ids = reward_line_obj.sudo().search(
                                    [('employee_over_time_id', '=', over.id), ('move_id.state', '=', 'posted'),
                                     ('employee_id.bank_account_id.bank_id', '=', bank.id)])

                        elif entry_type == 'unposted':
                            if employees:
                                overtime_lines_ids = reward_line_obj.sudo().search(
                                    [('employee_over_time_id', '=', over.id), ('move_id.state', '=', 'draft'),
                                     ('employee_id.bank_account_id.bank_id', '=', bank.id),
                                     ('employee_id', 'in', employees.ids)])
                            else:
                                overtime_lines_ids = reward_line_obj.sudo().search(
                                    [('employee_over_time_id', '=', over.id), ('move_id.state', '=', 'draft'),
                                     ('employee_id.bank_account_id.bank_id', '=', bank.id)])

                        if not overtime_lines_ids:
                            continue
                        sn = 0o001
                        for ove in overtime_lines_ids:
                            data_list = [ove.employee_id.emp_no, ove.employee_id.name or ' ',
                                         ove.employee_id.bank_account_id.acc_number or ' ',
                                         ove.employee_id.bank_account_id.bank_id.bic,
                                         round(ove.price_hour, 2),
                                         ove.employee_id.saudi_number.saudi_id if ove.employee_id.check_nationality == True else ove.employee_id.iqama_number.iqama_id,
                                         0.0, 0.0, 0.0, 0.0,
                                         ove.employee_id.branch_id.name if branch else ove.employee_id.working_location.name]
                            col = 1
                            row += 1
                            col += 1
                            if bank_type == 'rajhi':
                                sheet.write(row, 2, data_list[3], format1)
                                sheet.write(row, 3, data_list[2], format1)
                                sheet.write(row, 4, data_list[1], format1)
                                sheet.write(row, 5, data_list[0], format1)
                                sheet.write(row, 6, data_list[5], format1)
                                sheet.write(row, 7, data_list[4], format1)
                                sheet.write(row, 8, data_list[6], format1)
                                sheet.write(row, 9, data_list[7], format1)
                                sheet.write(row, 10, data_list[8], format1)
                                sheet.write(row, 11, data_list[9], format1)
                            elif bank_type == 'alahli':
                                sheet.write(row, 2, data_list[3], format1)
                                sheet.write(row, 3, data_list[2], format1)
                                sheet.write(row, 4, data_list[4], format1)
                                sheet.write(row, 5, data_list[0], format1)
                                sheet.write(row, 6, data_list[1], format1)
                                sheet.write(row, 7, data_list[5], format1)
                                sheet.write(row, 8, data_list[10], format1)
                                sheet.write(row, 9, data_list[6], format1)
                                sheet.write(row, 10, data_list[7], format1)
                                sheet.write(row, 11, data_list[8], format1)
                                sheet.write(row, 12, data_list[9], format1)
                            elif bank_type == 'riyadh':
                                sheet.write(row, 2, sn, format1)
                                sheet.write(row, 3, data_list[5], format1)
                                sheet.write(row, 4, data_list[1], format1)
                                sheet.write(row, 5, data_list[2], format1)
                                sheet.write(row, 6, data_list[3], format1)
                                sheet.write(row, 7, data_list[4], format1)
                                sheet.write(row, 8, data_list[6], format1)
                                sheet.write(row, 9, data_list[7], format1)
                                sheet.write(row, 10, data_list[8], format1)
                                sheet.write(row, 11, data_list[9], format1)
                                sheet.write(row, 12, data_list[5], format1)
                                sheet.write(row, 13, data_list[12], format1)
                                sheet.write(row, 14, data_list[13], format1)
                                sheet.write(row, 15, report_type, format1)
                                sheet.write(row, 16, data_list[0], format1)
                                sn += 1

                elif report_type == 'mission':
                    missions = self.sudo().env['hr.official.mission'].search(
                        ['&', ('date_from', '>=', date_from), ('date_to', '<=', date_to),
                         ('process_type', '=', 'mission'),
                         ('state', '=', 'approve')
                         ])
                    for mission in missions:
                        mission_line_obj = self.sudo().env['hr.official.mission.employee']
                        if entry_type == 'all':
                            if employees:
                                mission_lines_ids = mission_line_obj.sudo().search(
                                    [('official_mission_id', '=', mission.id),
                                     ('employee_id.bank_account_id.bank_id', '=', bank.id),
                                     ('employee_id', 'in', employees.ids)])
                            else:
                                mission_lines_ids = mission_line_obj.sudo().search(
                                    [('official_mission_id', '=', mission.id),
                                     ('employee_id.bank_account_id.bank_id', '=', bank.id)])
                        elif entry_type == 'posted':
                            if employees:
                                mission_lines_ids = mission_line_obj.sudo().search(
                                    [('official_mission_id', '=', mission.id),
                                     ('employee_id.bank_account_id.bank_id', '=', bank.id),
                                     ('employee_id', 'in', employees.ids), ('account_move_id.state', '=', 'posted')])
                            else:
                                mission_lines_ids = mission_line_obj.sudo().search(
                                    [('official_mission_id', '=', mission.id), ('account_move_id.state', '=', 'posted'),
                                     ('employee_id.bank_account_id.bank_id', '=', bank.id)])
                        elif entry_type == 'unposted':
                            if employees:
                                mission_lines_ids = mission_line_obj.sudo().search(
                                    [('official_mission_id', '=', mission.id), ('account_move_id.state', '=', 'draft'),
                                     ('employee_id.bank_account_id.bank_id', '=', bank.id),
                                     ('employee_id', 'in', employees.ids)])
                            else:
                                mission_lines_ids = mission_line_obj.sudo().search(
                                    [('official_mission_id', '=', mission.id), ('account_move_id.state', '=', 'draft'),
                                     ('employee_id.bank_account_id.bank_id', '=', bank.id)])

                        if not mission_lines_ids:
                            continue
                        sn = 0o001
                        for miss in mission_lines_ids:
                            data_list = [miss.employee_id.emp_no, miss.employee_id.name or ' ',
                                         miss.employee_id.bank_account_id.acc_number or ' ',
                                         miss.employee_id.bank_account_id.bank_id.bic,
                                         round(miss.amount, 2),
                                         miss.employee_id.saudi_number.saudi_id if miss.employee_id.check_nationality == True else miss.employee_id.iqama_number.iqama_id,
                                         0.0, 0.0, 0.0, 0.0,
                                         miss.employee_id.branch_id.name if branch else miss.employee_id.working_location.name,
                                         company_id.currency_id.name,'Active']
                            col = 1
                            row += 1
                            col += 1
                            if bank_type == 'rajhi':
                                sheet.write(row, 2, data_list[3], format1)
                                sheet.write(row, 3, data_list[2], format1)
                                sheet.write(row, 4, data_list[1], format1)
                                sheet.write(row, 5, data_list[0], format1)
                                sheet.write(row, 6, data_list[5], format1)
                                sheet.write(row, 7, data_list[4], format1)
                                sheet.write(row, 8, data_list[6], format1)
                                sheet.write(row, 9, data_list[7], format1)
                                sheet.write(row, 10, data_list[8], format1)
                                sheet.write(row, 11, data_list[9], format1)
                            elif bank_type == 'alahli':
                                sheet.write(row, 2, data_list[3], format1)
                                sheet.write(row, 3, data_list[2], format1)
                                sheet.write(row, 4, data_list[4], format1)
                                sheet.write(row, 5, data_list[0], format1)
                                sheet.write(row, 6, data_list[1], format1)
                                sheet.write(row, 7, data_list[5], format1)
                                sheet.write(row, 8, data_list[10], format1)
                                sheet.write(row, 9, data_list[6], format1)
                                sheet.write(row, 10, data_list[7], format1)
                                sheet.write(row, 11, data_list[8], format1)
                                sheet.write(row, 12, data_list[9], format1)
                            elif bank_type == 'riyadh':
                                sheet.write(row, 2, sn, format1)
                                sheet.write(row, 3, data_list[5], format1)
                                sheet.write(row, 4, data_list[1], format1)
                                sheet.write(row, 5, data_list[2], format1)
                                sheet.write(row, 6, data_list[3], format1)
                                sheet.write(row, 7, data_list[4], format1)
                                sheet.write(row, 8, data_list[6], format1)
                                sheet.write(row, 9, data_list[7], format1)
                                sheet.write(row, 10, data_list[8], format1)
                                sheet.write(row, 11, data_list[9], format1)
                                sheet.write(row, 12, data_list[5], format1)
                                sheet.write(row, 13, data_list[12], format1)
                                sheet.write(row, 14, data_list[13], format1)
                                sheet.write(row, 15, report_type, format1)
                                sheet.write(row, 16, data_list[0], format1)
                                sn += 1
                elif report_type == 'training':
                    trainings = self.sudo().env['hr.official.mission'].search(
                        ['&', ('date_from', '>=', date_from), ('date_to', '<=', date_to),
                         ('process_type', '=', 'training'), ('state', '=', 'approve')
                         ])
                    for training in trainings:
                        training_line_obj = self.sudo().env['hr.official.mission.employee']
                        if entry_type == 'all':
                            if employees:
                                training_lines_ids = training_line_obj.sudo().search(
                                    [('official_mission_id', '=', training.id),
                                     ('employee_id.bank_account_id.bank_id', '=', bank.id),
                                     ('employee_id', 'in', employees.ids)])
                            else:
                                training_lines_ids = training_line_obj.sudo().search(
                                    [('official_mission_id', '=', training.id),
                                     ('employee_id.bank_account_id.bank_id', '=', bank.id)])
                        elif entry_type == 'posted':
                            if employees:
                                training_lines_ids = training_line_obj.sudo().search(
                                    [('official_mission_id', '=', training.id),
                                     ('employee_id.bank_account_id.bank_id', '=', bank.id),
                                     ('employee_id', 'in', employees.ids), ('account_move_id.state', '=', 'posted')])
                            else:
                                training_lines_ids = training_line_obj.sudo().search(
                                    [('official_mission_id', '=', training.id),
                                     ('employee_id.bank_account_id.bank_id', '=', bank.id),
                                     ('account_move_id.state', '=', 'posted')])
                        elif entry_type == 'unposted':
                            if employees:
                                training_lines_ids = training_line_obj.sudo().search(
                                    [('official_mission_id', '=', training.id), ('account_move_id.state', '=', 'draft'),
                                     ('employee_id.bank_account_id.bank_id', '=', bank.id),
                                     ('employee_id', 'in', employees.ids)])
                            else:
                                training_lines_ids = training_line_obj.sudo().search(
                                    [('official_mission_id', '=', training.id), ('account_move_id.state', '=', 'draft'),
                                     ('employee_id.bank_account_id.bank_id', '=', bank.id)])

                        if not training_lines_ids:
                            continue
                        sn = 0o001
                        for train in training_lines_ids:
                            data_list = [train.employee_id.emp_no, train.employee_id.name or ' ',
                                         train.employee_id.bank_account_id.acc_number or ' ',
                                         train.employee_id.bank_account_id.bank_id.bic,
                                         round(train.amount, 2),
                                         train.employee_id.saudi_number.saudi_id if train.employee_id.check_nationality == True else train.employee_id.iqama_number.iqama_id,
                                         0.0, 0.0, 0.0, 0.0,
                                         train.employee_id.branch_id.name if branch else train.employee_id.working_location.name,
                                         company_id.currency_id.name,'Active']
                            col = 1
                            row += 1
                            col += 1
                            if bank_type == 'rajhi':
                                sheet.write(row, 2, data_list[3], format1)
                                sheet.write(row, 3, data_list[2], format1)
                                sheet.write(row, 4, data_list[1], format1)
                                sheet.write(row, 5, data_list[0], format1)
                                sheet.write(row, 6, data_list[5], format1)
                                sheet.write(row, 7, data_list[4], format1)
                                sheet.write(row, 8, data_list[6], format1)
                                sheet.write(row, 9, data_list[7], format1)
                                sheet.write(row, 10, data_list[8], format1)
                                sheet.write(row, 11, data_list[9], format1)
                            elif bank_type == 'alahli':
                                sheet.write(row, 2, data_list[3], format1)
                                sheet.write(row, 3, data_list[2], format1)
                                sheet.write(row, 4, data_list[4], format1)
                                sheet.write(row, 5, data_list[0], format1)
                                sheet.write(row, 6, data_list[1], format1)
                                sheet.write(row, 7, data_list[5], format1)
                                sheet.write(row, 8, data_list[10], format1)
                                sheet.write(row, 9, data_list[6], format1)
                                sheet.write(row, 10, data_list[7], format1)
                                sheet.write(row, 11, data_list[8], format1)
                                sheet.write(row, 12, data_list[9], format1)
                            elif bank_type == 'riyadh':
                                sheet.write(row, 2, sn, format1)
                                sheet.write(row, 3, data_list[5], format1)
                                sheet.write(row, 4, data_list[1], format1)
                                sheet.write(row, 5, data_list[2], format1)
                                sheet.write(row, 6, data_list[3], format1)
                                sheet.write(row, 7, data_list[4], format1)
                                sheet.write(row, 8, data_list[6], format1)
                                sheet.write(row, 9, data_list[7], format1)
                                sheet.write(row, 10, data_list[8], format1)
                                sheet.write(row, 11, data_list[9], format1)
                                sheet.write(row, 12, data_list[5], format1)
                                sheet.write(row, 13, data_list[12], format1)
                                sheet.write(row, 14, data_list[13], format1)
                                sheet.write(row, 15, report_type, format1)
                                sheet.write(row, 16, data_list[0], format1)
                                sn += 1
        else:

            row = 4
            if bank_type == 'rajhi':
                sheet.write(3, 2, 'Bank', format2)
                sheet.write(3, 3, 'Account #', format2)
                sheet.write(3, 4, 'Employee Name', format2)
                sheet.write(3, 5, 'Employee Number', format2)
                sheet.write(3, 6, 'Legal #', format2)
                sheet.write(3, 7, 'Amount', format2)
                sheet.write(3, 8, 'Employee Basic Salary', format2)
                sheet.write(3, 9, 'Housing Allowance', format2)
                sheet.write(3, 10, 'Other Earnings', format2)
                sheet.write(3, 11, 'Deductions', format2)
                sheet.write(4, 2, 'البنك', format2)
                sheet.write(4, 3, 'رقم الحساب', format2)
                sheet.write(4, 4, 'إسم الموظف', format2)
                sheet.write(4, 5, 'الرقم الوظيفي', format2)
                sheet.write(4, 6, 'رقم الهويه/الإقامة', format2)
                sheet.write(4, 7, 'المبلغ', format2)
                sheet.write(4, 8, 'الراتب الاساسى', format2)
                sheet.write(4, 9, 'بدل السكن', format2)
                sheet.write(4, 10, 'دخل اخر', format2)
                sheet.write(4, 11, 'الخصومات', format2)
            elif bank_type == 'alahli':
                sheet.write(row, 2, 'Bank', format1)
                sheet.write(row, 3, 'Account Number', format1)
                sheet.write(row, 4, 'Total Salary', format1)
                sheet.write(row, 5, 'Transaction Reference', format1)
                sheet.write(row, 6, 'Employee Name', format1)
                sheet.write(row, 7, 'National ID/Iqama ID', format1)
                sheet.write(row, 8, 'Employee Address', format1)
                sheet.write(row, 9, 'Basic Salary', format1)
                sheet.write(row, 10, 'Housing Allowance', format1)
                sheet.write(row, 11, 'Other Earnings', format1)
                sheet.write(row, 12, 'Deductions', format1)
            elif bank_type == 'riyadh':
                sheet.write(row, 2, 'SN', format4)
                sheet.write(row, 3, 'هوية المستفيد/ المرجع', format4)
                sheet.write(row, 4, 'المستفيد / اسم الموظف', format4)
                sheet.write(row, 5, 'رقم الحساب ', format4)
                sheet.write(row, 6, 'رمز البنك', format4)
                sheet.write(row, 7, 'إجمالي المبلغ', format4)
                sheet.write(row, 8, 'الراتب الأساسي', format4)
                sheet.write(row, 9, 'بدل السكن', format4)
                sheet.write(row, 10, 'دخل آخر', format4)
                sheet.write(row, 11, 'الخصومات', format4)
                sheet.write(row, 12, 'العنوان', format4)
                sheet.write(row, 13, 'العملة', format4)
                sheet.write(row, 14, 'الحالة', format4)
                sheet.write(row, 15, 'وصف الدفع', format4)
                sheet.write(row, 16, 'مرجع الدفع', format4)
            if report_type == 'salary':
                if entry_type == 'all':
                    if employees:
                        payslip_ids = self.sudo().env['hr.payslip'].search(
                            ['&', ('date_from', '>=', date_from), ('date_to', '<=', date_to),
                             ('state', '=', 'transfered'),
                             ('employee_id', 'in', employees.ids),
                             ('employee_id.bank_account_id.bank_id', 'in', all_bank.ids)])

                    elif salary:
                        payslip_ids = self.sudo().env['hr.payslip'].search(
                            ['&', ('date_from', '>=', date_from), ('date_to', '<=', date_to),
                             ('state', '=', 'transfered'),
                             ('struct_id', 'in', salary_ids),
                             ('employee_id.bank_account_id.bank_id', 'in', all_bank.ids)])
                    elif salary and employees:
                        payslip_ids = self.sudo().env['hr.payslip'].search(
                            ['&', ('date_from', '>=', date_from), ('date_to', '<=', date_to),
                             ('state', '=', 'transfered'),
                             ('employee_id', 'in', employees.ids), ('struct_id', 'in', salary.ids),
                             ('employee_id.bank_account_id.bank_id', 'in', all_bank.ids)])
                    else:
                        payslip_ids = self.sudo().env['hr.payslip'].search(
                            ['&', ('date_from', '>=', date_from), ('date_to', '<=', date_to),
                             ('state', '=', 'transfered'),
                             ('employee_id.bank_account_id.bank_id', 'in', all_bank.ids)])
                elif entry_type == 'posted':
                    if employees:
                        payslip_ids = self.sudo().env['hr.payslip'].search(
                            ['&', ('date_from', '>=', date_from), ('date_to', '<=', date_to),
                             ('state', '=', 'transfered'),
                             ('employee_id', 'in', employees.ids),
                             ('employee_id.bank_account_id.bank_id', 'in', all_bank.ids)
                                , '|',
                             ('move_id.state', '=', 'posted'), ('payslip_run_id.move_id.state', '=', 'posted')
                             ])

                    elif salary:
                        payslip_ids = self.sudo().env['hr.payslip'].search(
                            ['&', ('date_from', '>=', date_from), ('date_to', '<=', date_to),
                             ('state', '=', 'transfered'), ('struct_id', 'in', salary_ids),
                             ('employee_id.bank_account_id.bank_id', 'in', all_bank.ids), '|',
                             ('move_id.state', '=', 'posted'), ('payslip_run_id.move_id.state', '=', 'posted')])
                    elif salary and employees:
                        payslip_ids = self.sudo().env['hr.payslip'].search(
                            ['&', ('date_from', '>=', date_from), ('date_to', '<=', date_to),
                             ('state', '=', 'transfered'), ('employee_id', 'in', employees.ids),
                             ('struct_id', 'in', salary.ids),
                             ('employee_id.bank_account_id.bank_id', 'in', all_bank.ids), '|',
                             ('move_id.state', '=', 'posted'), ('payslip_run_id.move_id.state', '=', 'posted')])
                    else:
                        payslip_ids = self.sudo().env['hr.payslip'].search(
                            ['&', ('date_from', '>=', date_from), ('date_to', '<=', date_to),
                             ('state', '=', 'transfered'),
                             ('employee_id.bank_account_id.bank_id', 'in', all_bank.ids)
                                , '|',
                             ('move_id.state', '=', 'posted'), ('payslip_run_id.move_id.state', '=', 'posted')
                             ])
                elif entry_type == 'unposted':
                    if employees:
                        payslip_ids = self.sudo().env['hr.payslip'].search(
                            ['&', ('date_from', '>=', date_from), ('date_to', '<=', date_to),
                             ('state', '=', 'transfered'),
                             ('employee_id', 'in', employees.ids),
                             ('employee_id.bank_account_id.bank_id', 'in', all_bank.ids)
                                , '|',
                             ('move_id.state', '=', 'draft'), ('payslip_run_id.move_id.state', '=', 'draft')
                             ])

                    elif salary:
                        payslip_ids = self.sudo().env['hr.payslip'].search(
                            ['&', ('date_from', '>=', date_from), ('date_to', '<=', date_to),
                             ('state', '=', 'transfered'),
                             ('struct_id', 'in', salary_ids),
                             ('employee_id.bank_account_id.bank_id', 'in', all_bank.ids)
                                , '|',
                             ('move_id.state', '=', 'draft'), ('payslip_run_id.move_id.state', '=', 'draft')
                             ])
                    elif salary and employees:
                        payslip_ids = self.sudo().env['hr.payslip'].search(
                            ['&', ('date_from', '>=', date_from), ('date_to', '<=', date_to),
                             ('state', '=', 'transfered'),
                             ('employee_id', 'in', employees.ids), ('struct_id', 'in', salary.ids),
                             ('employee_id.bank_account_id.bank_id', 'in', all_bank.ids)
                                , '|',
                             ('move_id.state', '=', 'draft'), ('payslip_run_id.move_id.state', '=', 'draft')
                             ])
                    else:
                        payslip_ids = self.sudo().env['hr.payslip'].search(
                            ['&', ('date_from', '>=', date_from), ('date_to', '<=', date_to),
                             ('state', '=', 'transfered'),
                             ('employee_id.bank_account_id.bank_id', 'in', all_bank.ids)
                                , '|',
                             ('move_id.state', '=', 'draft'), ('payslip_run_id.move_id.state', '=', 'draft')
                             ])
                salary_rules = self.sudo().env['hr.salary.rule'].search([]).sorted(
                    key=lambda v: v.sequence).ids
                payslip_line_obj = self.sudo().env['hr.payslip.line']
                sn = 0o001
                for payslip in payslip_ids:

                    # sheet.write(row - 1, 1, bank.name, format3)

                    basic = 0.0
                    housing = 0.0
                    payslip_lines_ids = payslip_line_obj.sudo().search([('slip_id', '=', payslip.id)])
                    if not payslip_lines_ids:
                        continue
                    for payslip_line_rec in payslip_lines_ids:
                        if payslip_line_rec.salary_rule_id.id in salary_rules:
                            if payslip_line_rec.salary_rule_id.rules_type == 'salary':
                                basic += payslip_line_rec.total
                            elif payslip_line_rec.salary_rule_id.rules_type == 'house':
                                housing += payslip_line_rec.total
                    other = round((payslip.total_allowances - basic - housing), 2)
                    data_list = [payslip.employee_id.emp_no, payslip.employee_id.name or ' ',
                                 payslip.employee_id.bank_account_id.acc_number or ' ',
                                 payslip.employee_id.bank_account_id.bank_id.bic,
                                 payslip.total_sum,
                                 payslip.employee_id.saudi_number.saudi_id if payslip.employee_id.check_nationality == True else payslip.employee_id.iqama_number.iqama_id,
                                 basic, housing, other, round((payslip.total_deductions + payslip.total_loans), 2),
                                 payslip.employee_id.branch_id.name if branch else payslip.employee_id.working_location.name,
                                 company_id.currency_id.name,'Active']
                    print("============================",
                          payslip.employee_id.branch_id.name if branch else payslip.employee_id.working_location.name)
                    col = 1
                    row += 1
                    col += 1
                    if bank_type == 'rajhi':
                        sheet.write(row, 2, data_list[3], format1)
                        sheet.write(row, 3, data_list[2], format1)
                        sheet.write(row, 4, data_list[1], format1)
                        sheet.write(row, 5, data_list[0], format1)
                        sheet.write(row, 6, data_list[5], format1)
                        sheet.write(row, 7, data_list[4], format1)
                        sheet.write(row, 8, data_list[6], format1)
                        sheet.write(row, 9, data_list[7], format1)
                        sheet.write(row, 10, data_list[8], format1)
                        sheet.write(row, 11, data_list[9], format1)
                    elif bank_type == 'alahli':
                        sheet.write(row, 2, data_list[3], format1)
                        sheet.write(row, 3, data_list[2], format1)
                        sheet.write(row, 4, data_list[4], format1)
                        sheet.write(row, 5, data_list[0], format1)
                        sheet.write(row, 6, data_list[1], format1)
                        sheet.write(row, 7, data_list[5], format1)
                        sheet.write(row, 8, data_list[10], format1)
                        sheet.write(row, 9, data_list[6], format1)
                        sheet.write(row, 10, data_list[7], format1)
                        sheet.write(row, 11, data_list[8], format1)
                        sheet.write(row, 12, data_list[9], format1)
                    elif bank_type == 'riyadh':
                        sheet.write(row, 2, sn, format1)
                        sheet.write(row, 3, data_list[5], format1)
                        sheet.write(row, 4, data_list[1], format1)
                        sheet.write(row, 5, data_list[2], format1)
                        sheet.write(row, 6, data_list[3], format1)
                        sheet.write(row, 7, data_list[4], format1)
                        sheet.write(row, 8, data_list[6], format1)
                        sheet.write(row, 9, data_list[7], format1)
                        sheet.write(row, 10, data_list[8], format1)
                        sheet.write(row, 11, data_list[9], format1)
                        sheet.write(row, 12, data_list[10], format1)
                        sheet.write(row, 13, data_list[11], format1)
                        sheet.write(row, 14, data_list[12], format1)
                        sheet.write(row, 15, report_type, format1)
                        sheet.write(row, 16, data_list[0], format1)
                        sn += 1

            elif report_type == 'allowance':
                allowances = self.sudo().env['hr.employee.reward'].search(
                    ['&', ('date', '>=', date_from), ('date', '<=', date_to), ('state', '=', 'done')
                     ])
                for allowance in allowances:
                    reward_line_obj = self.sudo().env['lines.ids.reward']
                    if entry_type == 'all':
                        if employees:
                            reward_lines_ids = reward_line_obj.sudo().search(
                                [('employee_reward_id', '=', allowance.id),
                                 ('employee_id.bank_account_id.bank_id', 'in', all_bank.ids),
                                 ('employee_id', 'in', employees.ids)])
                        else:
                            reward_lines_ids = reward_line_obj.sudo().search(
                                [('employee_reward_id', '=', allowance.id),
                                 ('employee_id.bank_account_id.bank_id', 'in', all_bank.ids)])
                    elif entry_type == 'posted':
                        if employees:
                            reward_lines_ids = reward_line_obj.sudo().search(
                                [('employee_reward_id', '=', allowance.id),
                                 ('employee_id.bank_account_id.bank_id', 'in', all_bank.ids),
                                 ('employee_id', 'in', employees.ids), ('move_id.state', '=', 'posted')])
                        else:
                            reward_lines_ids = reward_line_obj.sudo().search(
                                [('employee_reward_id', '=', allowance.id), ('move_id.state', '=', 'posted'),
                                 ('employee_id.bank_account_id.bank_id', 'in', all_bank.ids)])
                    elif entry_type == 'unposted':
                        if employees:
                            reward_lines_ids = reward_line_obj.sudo().search(
                                [('employee_reward_id', '=', allowance.id), ('move_id.state', '=', 'draft'),
                                 ('employee_id.bank_account_id.bank_id', 'in', all_bank.ids),
                                 ('employee_id', 'in', employees.ids)])
                        else:
                            reward_lines_ids = reward_line_obj.sudo().search(
                                [('employee_reward_id', '=', allowance.id), ('move_id.state', '=', 'draft'),
                                 ('employee_id.bank_account_id.bank_id', 'in', all_bank.ids)])

                    if not reward_lines_ids:
                        continue
                    sn = 0o001
                    for reward in reward_lines_ids:
                        data_list = [reward.employee_id.emp_no, reward.employee_id.name or ' ',
                                     reward.employee_id.bank_account_id.acc_number or ' ',
                                     reward.employee_id.bank_account_id.bank_id.bic,
                                     round(reward.amount, 2),
                                     reward.employee_id.saudi_number.saudi_id if reward.employee_id.check_nationality == True else reward.employee_id.iqama_number.iqama_id,
                                     0.0, 0.0, 0.0, 0.0,
                                     reward.employee_id.branch_id.name if branch else reward.employee_id.working_location.name,
                                     company_id.currency_id.name,'Active']
                        col = 1
                        row += 1
                        col += 1
                        if bank_type == 'rajhi':
                            sheet.write(row, 2, data_list[3], format1)
                            sheet.write(row, 3, data_list[2], format1)
                            sheet.write(row, 4, data_list[1], format1)
                            sheet.write(row, 5, data_list[0], format1)
                            sheet.write(row, 6, data_list[5], format1)
                            sheet.write(row, 7, data_list[4], format1)
                            sheet.write(row, 8, data_list[6], format1)
                            sheet.write(row, 9, data_list[7], format1)
                            sheet.write(row, 10, data_list[8], format1)
                            sheet.write(row, 11, data_list[9], format1)
                        elif bank_type == 'alahli':
                            sheet.write(row, 2, data_list[3], format1)
                            sheet.write(row, 3, data_list[2], format1)
                            sheet.write(row, 4, data_list[4], format1)
                            sheet.write(row, 5, data_list[0], format1)
                            sheet.write(row, 6, data_list[1], format1)
                            sheet.write(row, 7, data_list[5], format1)
                            sheet.write(row, 8, data_list[10], format1)
                            sheet.write(row, 9, data_list[6], format1)
                            sheet.write(row, 10, data_list[7], format1)
                            sheet.write(row, 11, data_list[8], format1)
                            sheet.write(row, 12, data_list[9], format1)
                        elif bank_type == 'riyadh':
                            sheet.write(row, 2, sn, format1)
                            sheet.write(row, 3, data_list[5], format1)
                            sheet.write(row, 4, data_list[1], format1)
                            sheet.write(row, 5, data_list[2], format1)
                            sheet.write(row, 6, data_list[3], format1)
                            sheet.write(row, 7, data_list[4], format1)
                            sheet.write(row, 8, data_list[6], format1)
                            sheet.write(row, 9, data_list[7], format1)
                            sheet.write(row, 10, data_list[8], format1)
                            sheet.write(row, 11, data_list[9], format1)
                            sheet.write(row, 12, data_list[10], format1)
                            sheet.write(row, 13, data_list[11], format1)
                            sheet.write(row, 14, data_list[12], format1)
                            sheet.write(row, 15, report_type, format1)
                            sheet.write(row, 16, data_list[0], format1)
                            sn += 1
            elif report_type == 'overtime':
                overtime = self.sudo().env['employee.overtime.request'].search(
                    ['&', ('date_from', '>=', date_from), ('date_to', '<=', date_to), ('state', '=', 'validated'),
                     ('transfer_type', '=', 'accounting')
                     ])
                for over in overtime:
                    reward_line_obj = self.sudo().env['line.ids.over.time']
                    if entry_type == 'all':
                        if employees:
                            overtime_lines_ids = reward_line_obj.sudo().search(
                                [('employee_over_time_id', '=', over.id),
                                 ('employee_id.bank_account_id.bank_id', 'in', all_bank.ids),
                                 ('employee_id', 'in', employees.ids)])
                        else:
                            overtime_lines_ids = reward_line_obj.sudo().search(
                                [('employee_over_time_id', '=', over.id),
                                 ('employee_id.bank_account_id.bank_id', 'in', all_bank.ids)])
                    elif entry_type == 'posted':
                        if employees:
                            overtime_lines_ids = reward_line_obj.sudo().search(
                                [('employee_over_time_id', '=', over.id),
                                 ('employee_id.bank_account_id.bank_id', 'in', all_bank.ids),
                                 ('employee_id', 'in', employees.ids), ('move_id.state', '=', 'posted')])
                        else:
                            overtime_lines_ids = reward_line_obj.sudo().search(
                                [('employee_over_time_id', '=', over.id), ('move_id.state', '=', 'posted'),
                                 ('employee_id.bank_account_id.bank_id', 'in', all_bank.ids)])
                    elif entry_type == 'unposted':
                        if employees:
                            overtime_lines_ids = reward_line_obj.sudo().search(
                                [('employee_over_time_id', '=', over.id),
                                 ('employee_id.bank_account_id.bank_id', 'in', all_bank.ids),
                                 ('employee_id', 'in', employees.ids), ('move_id.state', '=', 'draft')])
                        else:
                            overtime_lines_ids = reward_line_obj.sudo().search(
                                [('employee_over_time_id', '=', over.id), ('move_id.state', '=', 'draft'),
                                 ('employee_id.bank_account_id.bank_id', 'in', all_bank.ids)])

                    if not overtime_lines_ids:
                        continue
                    sn = 0o001
                    for ove in overtime_lines_ids:
                        data_list = [ove.employee_id.emp_no,
                                     ove.employee_id.name or ' ',
                                     ove.employee_id.bank_account_id.acc_number or ' ',
                                     ove.employee_id.bank_account_id.bank_id.bic,
                                     round(ove.price_hour, 2),
                                     ove.employee_id.saudi_number.saudi_id if ove.employee_id.check_nationality == True else ove.employee_id.iqama_number.iqama_id,
                                     0.0, 0.0, 0.0, 0.0,
                                     ove.employee_id.branch_id.name if branch else ove.employee_id.working_location.name
                                     ,company_id.currency_id.name,'Active']
                        col = 1
                        row += 1
                        col += 1
                        if bank_type == 'rajhi':
                            sheet.write(row, 2, data_list[3], format1)
                            sheet.write(row, 3, data_list[2], format1)
                            sheet.write(row, 4, data_list[1], format1)
                            sheet.write(row, 5, data_list[0], format1)
                            sheet.write(row, 6, data_list[5], format1)
                            sheet.write(row, 7, data_list[4], format1)
                            sheet.write(row, 8, data_list[6], format1)
                            sheet.write(row, 9, data_list[7], format1)
                            sheet.write(row, 10, data_list[8], format1)
                            sheet.write(row, 11, data_list[9], format1)
                        elif bank_type == 'alahli':
                            sheet.write(row, 2, data_list[3], format1)
                            sheet.write(row, 3, data_list[2], format1)
                            sheet.write(row, 4, data_list[4], format1)
                            sheet.write(row, 5, data_list[0], format1)
                            sheet.write(row, 6, data_list[1], format1)
                            sheet.write(row, 7, data_list[5], format1)
                            sheet.write(row, 8, data_list[10], format1)
                            sheet.write(row, 9, data_list[6], format1)
                            sheet.write(row, 10, data_list[7], format1)
                            sheet.write(row, 11, data_list[8], format1)
                            sheet.write(row, 12, data_list[9], format1)
                        elif bank_type == 'riyadh':
                            sheet.write(row, 2, sn, format1)
                            sheet.write(row, 3, data_list[5], format1)
                            sheet.write(row, 4, data_list[1], format1)
                            sheet.write(row, 5, data_list[2], format1)
                            sheet.write(row, 6, data_list[3], format1)
                            sheet.write(row, 7, data_list[4], format1)
                            sheet.write(row, 8, data_list[6], format1)
                            sheet.write(row, 9, data_list[7], format1)
                            sheet.write(row, 10, data_list[8], format1)
                            sheet.write(row, 11, data_list[9], format1)
                            sheet.write(row, 12, data_list[10], format1)
                            sheet.write(row, 13, data_list[11], format1)
                            sheet.write(row, 14, data_list[12], format1)
                            sheet.write(row, 15, report_type, format1)
                            sheet.write(row, 16, data_list[0], format1)
                            sn += 1
            elif report_type == 'mission':
                missions = self.sudo().env['hr.official.mission'].search(
                    ['&', ('date_from', '>=', date_from), ('date_to', '<=', date_to),
                     ('process_type', '=', 'mission'),
                     ('state', '=', 'approve')
                     ])
                for mission in missions:
                    mission_line_obj = self.sudo().env['hr.official.mission.employee']
                    if entry_type == 'all':
                        if employees:
                            mission_lines_ids = mission_line_obj.sudo().search(
                                [('official_mission_id', '=', mission.id),
                                 ('employee_id.bank_account_id.bank_id', 'in', all_bank.ids),
                                 ('employee_id', 'in', employees.ids)])
                        else:
                            mission_lines_ids = mission_line_obj.sudo().search(
                                [('official_mission_id', '=', mission.id),
                                 ('employee_id.bank_account_id.bank_id', 'in', all_bank.ids)])
                    elif entry_type == 'posted':
                        if employees:
                            mission_lines_ids = mission_line_obj.sudo().search(
                                [('official_mission_id', '=', mission.id),
                                 ('employee_id.bank_account_id.bank_id', 'in', all_bank.ids),
                                 ('employee_id', 'in', employees.ids), ('account_move_id.state', '=', 'posted')])
                        else:
                            mission_lines_ids = mission_line_obj.sudo().search(
                                [('official_mission_id', '=', mission.id), ('account_move_id.state', '=', 'posted'),
                                 ('employee_id.bank_account_id.bank_id', 'in', all_bank.ids)])
                    elif entry_type == 'unposted':
                        if employees:
                            mission_lines_ids = mission_line_obj.sudo().search(
                                [('official_mission_id', '=', mission.id), ('account_move_id.state', '=', 'draft'),
                                 ('employee_id.bank_account_id.bank_id', 'in', all_bank.ids),
                                 ('employee_id', 'in', employees.ids)])
                        else:
                            mission_lines_ids = mission_line_obj.sudo().search(
                                [('official_mission_id', '=', mission.id), ('account_move_id.state', '=', 'draft'),
                                 ('employee_id.bank_account_id.bank_id', 'in', all_bank.ids)])

                    if not mission_lines_ids:
                        continue
                    sn = 0o001
                    for miss in mission_lines_ids:
                        data_list = [miss.employee_id.emp_no, miss.employee_id.name or ' ',
                                     miss.employee_id.bank_account_id.acc_number or ' ',
                                     miss.employee_id.bank_account_id.bank_id.bic,
                                     round(miss.amount, 2),
                                     miss.employee_id.saudi_number.saudi_id if miss.employee_id.check_nationality == True else miss.employee_id.iqama_number.iqama_id,
                                     0.0, 0.0, 0.0, 0.0,
                                     miss.employee_id.branch_id.name if branch else miss.employee_id.working_location.name,
                                     company_id.currency_id.name, 'Active']
                        col = 1
                        row += 1
                        col += 1
                        if bank_type == 'rajhi':
                            sheet.write(row, 2, data_list[3], format1)
                            sheet.write(row, 3, data_list[2], format1)
                            sheet.write(row, 4, data_list[1], format1)
                            sheet.write(row, 5, data_list[0], format1)
                            sheet.write(row, 6, data_list[5], format1)
                            sheet.write(row, 7, data_list[4], format1)
                            sheet.write(row, 8, data_list[6], format1)
                            sheet.write(row, 9, data_list[7], format1)
                            sheet.write(row, 10, data_list[8], format1)
                            sheet.write(row, 11, data_list[9], format1)
                        elif bank_type == 'alahli':
                            sheet.write(row, 2, data_list[3], format1)
                            sheet.write(row, 3, data_list[2], format1)
                            sheet.write(row, 4, data_list[4], format1)
                            sheet.write(row, 5, data_list[0], format1)
                            sheet.write(row, 6, data_list[1], format1)
                            sheet.write(row, 7, data_list[5], format1)
                            sheet.write(row, 8, data_list[10], format1)
                            sheet.write(row, 9, data_list[6], format1)
                            sheet.write(row, 10, data_list[7], format1)
                            sheet.write(row, 11, data_list[8], format1)
                            sheet.write(row, 12, data_list[9], format1)
                        elif bank_type == 'riyadh':
                            sheet.write(row, 2, sn, format1)
                            sheet.write(row, 3, data_list[5], format1)
                            sheet.write(row, 4, data_list[1], format1)
                            sheet.write(row, 5, data_list[2], format1)
                            sheet.write(row, 6, data_list[3], format1)
                            sheet.write(row, 7, data_list[4], format1)
                            sheet.write(row, 8, data_list[6], format1)
                            sheet.write(row, 9, data_list[7], format1)
                            sheet.write(row, 10, data_list[8], format1)
                            sheet.write(row, 11, data_list[9], format1)
                            sheet.write(row, 12, data_list[10], format1)
                            sheet.write(row, 13, data_list[11], format1)
                            sheet.write(row, 14, data_list[12], format1)
                            sheet.write(row, 15, report_type, format1)
                            sheet.write(row, 16, data_list[0], format1)
                            sn += 1
            elif report_type == 'training':
                trainings = self.sudo().env['hr.official.mission'].search(
                    ['&', ('date_from', '>=', date_from), ('date_to', '<=', date_to),
                     ('process_type', '=', 'training'), ('state', '=', 'approve')
                     ])
                for training in trainings:
                    training_line_obj = self.sudo().env['hr.official.mission.employee']
                    if entry_type == 'all':
                        if employees:
                            training_lines_ids = training_line_obj.sudo().search(
                                [('official_mission_id', '=', training.id),
                                 ('employee_id.bank_account_id.bank_id', 'in', all_bank.ids),
                                 ('employee_id', 'in', employees.ids)])
                        else:
                            training_lines_ids = training_line_obj.sudo().search(
                                [('official_mission_id', '=', training.id),
                                 ('employee_id.bank_account_id.bank_id', 'in', all_bank.ids)])
                    elif entry_type == 'posted':
                        if employees:
                            training_lines_ids = training_line_obj.sudo().search(
                                [('official_mission_id', '=', training.id),
                                 ('employee_id.bank_account_id.bank_id', 'in', all_bank.ids),
                                 ('employee_id', 'in', employees.ids), ('account_move_id.state', '=', 'posted')])
                        else:
                            training_lines_ids = training_line_obj.sudo().search(
                                [('official_mission_id', '=', training.id),
                                 ('employee_id.bank_account_id.bank_id', 'in', all_bank.ids),
                                 ('account_move_id.state', '=', 'posted')])
                    elif entry_type == 'unposted':
                        if employees:
                            training_lines_ids = training_line_obj.sudo().search(
                                [('official_mission_id', '=', training.id),
                                 ('employee_id.bank_account_id.bank_id', 'in', all_bank.ids),
                                 ('employee_id', 'in', employees.ids), ('account_move_id.state', '=', 'draft')])
                        else:
                            training_lines_ids = training_line_obj.sudo().search(
                                [('official_mission_id', '=', training.id),
                                 ('employee_id.bank_account_id.bank_id', 'in', all_bank.ids),
                                 ('account_move_id.state', '=', 'draft')])

                    if not training_lines_ids:
                        continue
                    sn = 0o001
                    for train in training_lines_ids:
                        data_list = [train.employee_id.emp_no, train.employee_id.name or ' ',
                                     train.employee_id.bank_account_id.acc_number or ' ',
                                     train.employee_id.bank_account_id.bank_id.bic,
                                     round(train.amount, 2),
                                     train.employee_id.saudi_number.saudi_id if train.employee_id.check_nationality == True else train.employee_id.iqama_number.iqama_id,
                                     0.0, 0.0, 0.0, 0.0,
                                     train.employee_id.branch_id.name if branch else train.employee_id.working_location.name,
                                     company_id.currency_id.name,'Active']
                        col = 1
                        row += 1
                        col += 1
                        if bank_type == 'rajhi':
                            sheet.write(row, 2, data_list[3], format1)
                            sheet.write(row, 3, data_list[2], format1)
                            sheet.write(row, 4, data_list[1], format1)
                            sheet.write(row, 5, data_list[0], format1)
                            sheet.write(row, 6, data_list[5], format1)
                            sheet.write(row, 7, data_list[4], format1)
                            sheet.write(row, 8, data_list[6], format1)
                            sheet.write(row, 9, data_list[7], format1)
                            sheet.write(row, 10, data_list[8], format1)
                            sheet.write(row, 11, data_list[9], format1)
                        elif bank_type == 'alahli':
                            sheet.write(row, 2, data_list[3], format1)
                            sheet.write(row, 3, data_list[2], format1)
                            sheet.write(row, 4, data_list[4], format1)
                            sheet.write(row, 5, data_list[0], format1)
                            sheet.write(row, 6, data_list[1], format1)
                            sheet.write(row, 7, data_list[5], format1)
                            sheet.write(row, 8, data_list[10], format1)
                            sheet.write(row, 9, data_list[6], format1)
                            sheet.write(row, 10, data_list[7], format1)
                            sheet.write(row, 11, data_list[8], format1)
                            sheet.write(row, 12, data_list[9], format1)
                        elif bank_type == 'riyadh':
                            sheet.write(row, 2, sn, format1)
                            sheet.write(row, 3, data_list[5], format1)
                            sheet.write(row, 4, data_list[1], format1)
                            sheet.write(row, 5, data_list[2], format1)
                            sheet.write(row, 6, data_list[3], format1)
                            sheet.write(row, 7, data_list[4], format1)
                            sheet.write(row, 8, data_list[6], format1)
                            sheet.write(row, 9, data_list[7], format1)
                            sheet.write(row, 10, data_list[8], format1)
                            sheet.write(row, 11, data_list[9], format1)
                            sheet.write(row, 12, data_list[10], format1)
                            sheet.write(row, 13, data_list[11], format1)
                            sheet.write(row, 14, data_list[12], format1)
                            sheet.write(row, 15, report_type, format1)
                            sheet.write(row, 16, data_list[0], format1)
                            sn += 1
