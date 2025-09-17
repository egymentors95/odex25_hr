# -*- coding: utf-8 -*-
from datetime import datetime
from datetime import date, timedelta, datetime as dt
import collections
from dateutil import relativedelta
from odoo import api, fields, models, _
from odoo import exceptions
import calendar

from odoo.exceptions import UserError

date_format = "%Y-%m-%d"


class TreminationReport(models.TransientModel):
    _name = "employee.termination.report"
    _description = "Employee Termination Report"

    employee_ids = fields.Many2many(comodel_name='hr.employee', string='Employees', domain="[('state','=','open')]")
    cause_type = fields.Many2one(comodel_name='hr.termination.type')
    salary_date_from = fields.Date()
    salary_date_to = fields.Date()
    end_date = fields.Date(string='End Of Service')
    allowance_ids = fields.Many2many('hr.salary.rule', domain=[('rules_type', 'in', ['house', 'salary', 'transport'])])
    type = fields.Selection(selection=[('salary', 'Salary'), ('ticket', 'Ticket'), ('leave', 'Leave'),
                                       ('termination', 'Termination'), ('all', 'All')], required=True,
                            default='all', string='Type')

    def print_report(self):
        for emp in self.employee_ids:
            if not emp.first_hiring_date:
                raise exceptions.Warning(_('Please set the First Hiring Date %s')
                                         % emp.name)
        data = {
            'ids': self.ids,
            'model': self._name,
            'form': {
                'allowance_ids': self.allowance_ids.ids,
                'cause_type': self.cause_type.id,
                'employee_ids': self.employee_ids.ids,
                'type': self.type,
                'date_from': self.salary_date_from,
                'date_to': self.salary_date_to,
                'end_date': self.end_date,
            },
        }
        return self.env.ref('hr_termination.termination_benefits_action_report').report_action(self, data=data)

    def print_excel_report(self):
        for emp in self.employee_ids:
            if not emp.first_hiring_date:
                raise exceptions.Warning(_('Please set the First Hiring Date %s')
                % (emp.name))
        data = {
            'ids': self.ids,
            'model': self._name,
            'form': {
                'allowance_ids': self.allowance_ids.ids,
                'cause_type': self.cause_type.id,
                'employee_ids': self.employee_ids.ids,
                'type': self.type,
                'date_from': self.salary_date_from,
                'date_to': self.salary_date_to,
                'end_date': self.end_date,
            },
        }
        return self.env.ref('hr_termination.termination_benefits_xls').report_action(self, data=data, config=False)


class ReportTerminationPublic(models.AbstractModel):
    _name = 'report.hr_termination.termination_report_temp'

    def get_cause_amount(self, first_hire_date, cause_type_name, end_date, emp):
        # Get salary rule  form cause type
        if first_hire_date:
            cause_type_amount = 0.0
            five_year_benefit = 0
            amount = 0
            termination_model = self.env['hr.termination']
            if cause_type_name:
                start_date = datetime.strptime(str(first_hire_date), "%Y-%m-%d")
                end_date = datetime.strptime(str(end_date), "%Y-%m-%d")
                total_rules, amount_of_year, amount_of_month, amount_of_day, cause_type_amount = 0.0, 0.0, 0.0, 0.0, 0.0
                five_year_benefit, amount = 0, 0

                if end_date >= start_date:
                    value = relativedelta.relativedelta(end_date, start_date)
                    years = value.years
                    days = value.days
                    months = value.months
                    all_duration = months + (days / 30) + (years * 12)

                    if cause_type_name.allowance_ids and cause_type_name.termination_duration_ids:

                        # Get total for  all salary rules form cause type
                        for rule in cause_type_name.allowance_ids:
                            rule_flag = False
                            if rule_flag is False:
                                total_rules += termination_model.compute_rule(rule, emp.contract_id)
                        for end in cause_type_name.termination_duration_ids:
                            if all_duration >= 24:
                                if end.date_from <= 24 and end.date_to >= 60:
                                    total_rules_year = total_rules * end.factor * end.amount
                                    total_rules_month = total_rules_year / 12
                                    total_rules_day = total_rules_month / 30
                                    if years >= 1:
                                        amount_of_year = total_rules_year * years
                                    if months >= 1:
                                        amount_of_month = total_rules_month * months
                                    if days >= 1:
                                        amount_of_day = total_rules_day * days
                                five_year_benefit = amount_of_year + amount_of_month + amount_of_day
                        for line in cause_type_name.termination_duration_ids:
                            if line.date_from < all_duration and line.date_to >= all_duration:
                                total_rules_year = total_rules * line.factor * line.amount
                                total_rules_month = total_rules_year / 12
                                total_rules_day = total_rules_month / 30
                                if years >= 1:
                                    amount_of_year = total_rules_year * years
                                if months >= 1:
                                    amount_of_month = total_rules_month * months
                                if days >= 1:
                                    amount_of_day = total_rules_day * days
                            cause_type_amount = amount_of_year + amount_of_month + amount_of_day
                            amount = cause_type_amount - five_year_benefit
            return cause_type_amount, five_year_benefit, amount
        else:
            return 0.0

    def _get_holiday_amount(self, employee_id, leave_balance):
        salary = employee_id.contract_id.total_allowance
        leave_balance_money = 0.0
        if salary:
            days = employee_id.resource_calendar_id.work_days
            day_amount = salary / days if days else 0.0
            leave_balance = leave_balance
            holiday_amount = leave_balance * day_amount
            leave_balance_money = round(holiday_amount, 2)
        return leave_balance_money

    def create_rule_line(self, last_work_date, employee_id, cause_type_amount, cause_type_id, rule, amount, items, is_advantage, cause_type_factor,advantages_out_rule):
        # If cause type have factor then multiply it in salary rule amount
        if cause_type_id and cause_type_factor == 1:
            if cause_type_id.allowance_id and cause_type_amount:
                amount = round(cause_type_amount,2)
        # If cause type have holiday then multiply it in salary rule holiday amount
        holiday_allow = cause_type_id.holiday_allowance
        holiday_deduc = cause_type_id.holiday_deduction
        leave_balance = self.get_remaining_leaves(employee_id, last_work_date)
        leave_balance_money = self._get_holiday_amount(employee_id, leave_balance)
        if holiday_allow and holiday_allow.id == rule.id:
            amount = leave_balance_money
        if holiday_deduc and holiday_deduc.id == rule.id:
            amount = -(leave_balance_money)
            record = {
                'salary_rule_id': rule.id,
                'category_id': rule.category_id,
                'amount': amount,
                'is_advantage': is_advantage,
                'advantages_out_rule': advantages_out_rule,
            }
            items.append(record)
        if amount > 0 and not holiday_deduc.id == rule.id:
            record = {
                'salary_rule_id': rule.id,
                'category_id': rule.category_id,
                'amount': amount,
                'is_advantage': is_advantage,
                'advantages_out_rule': advantages_out_rule,
            }
            items.append(record)

    def compute_salary_rule(self, last_work_date, cause_type_amount, employee_id, rule, items, paid_percentage, advantages, cause_type_factor, cause_type_id):
        is_advantage = False
        advantages_out_rule = False
        amount = 0.0
        if employee_id.sudo().contract_id:
            if advantages:
                is_advantage = True
                # TODO
                if advantages.type == 'customize' and not advantages.out_rule:
                    # if advantages.type == 'customize' and self.contract_id.contractor_type.salary_type == 'amount':
                    amount = advantages.amount / paid_percentage
                else:
                    amount = advantages.amount
                    advantages_out_rule = True
                if advantages.type == 'exception':
                    amount = (self.compute_rule(rule,
                                                employee_id.sudo().contract_id) - advantages.amount) / paid_percentage
            else:
                amount = self.compute_rule(rule, employee_id.sudo().contract_id) / paid_percentage
            self.create_rule_line(last_work_date, employee_id, cause_type_amount, cause_type_id, rule, amount, items, is_advantage, cause_type_factor, advantages_out_rule)
        return round(amount, 2)

    def compute_rule(self, rule, contract):
        localdict = dict(employee=contract.employee_id, contract=contract)
        if rule.amount_select == 'percentage':
            total_percent = 0
            if rule.related_benefits_discounts:
                for line in rule.related_benefits_discounts:
                    if line.amount_select == 'fix':
                        total_percent += self.compute_rule(line, contract)
                    elif line.amount_select == 'percentage':
                        total_percent += self.compute_rule(line, contract)
                    else:
                        total_percent += self.compute_rule(line, contract)
            if total_percent:
                if rule.salary_type == 'fixed':
                    try:
                        return float(total_percent * rule.amount_percentage / 100)
                    except:
                        raise UserError(
                            _('Wrong percentage base or quantity defined for salary rule %s (%s).') % (
                                rule.name, rule.code))
                elif rule.salary_type == 'related_levels':
                    levels_ids = rule.salary_amount_ids.filtered(
                        lambda item: item.salary_scale_level.id == contract.salary_level.id)
                    if levels_ids:
                        for l in levels_ids:
                            try:
                                return float(l.salary * total_percent / 100)
                            except:
                                raise UserError(
                                    _('Wrong quantity defined for salary rule %s (%s).') % (
                                        rule.name, rule.code))
                    else:
                        return 0
                elif rule.salary_type == 'related_groups':
                    groups_ids = rule.salary_amount_ids.filtered(
                        lambda item: item.salary_scale_group.id == contract.salary_group.id)
                    if groups_ids:
                        for g in groups_ids:
                            try:
                                return float(g.salary * total_percent / 100)
                            except:
                                raise UserError(
                                    _('Wrong quantity defined for salary rule %s (%s).') % (
                                        rule.name, rule.code))
                    else:
                        return 0
                elif rule.salary_type == 'related_degrees':
                    degrees_ids = rule.salary_amount_ids.filtered(
                        lambda item: item.salary_scale_degree.id == contract.salary_degree.id)
                    if degrees_ids:
                        for d in degrees_ids:
                            try:
                                return float(d.salary * total_percent / 100)
                            except:
                                raise UserError(
                                    _('Wrong quantity defined for salary rule %s (%s).') % (
                                        rule.name, rule.code))
                    else:
                        return 0
            else:
                try:
                    return 0
                except:
                    raise Warning(_('There is no total for rule : %s') % (rule.name))

        elif rule.amount_select == 'fix':
            return rule._compute_rule(localdict)[0]

        else:
            return rule._compute_rule(localdict)[0]

    def _get_paid_duration(self, last_work_date):
        salary_date_from = 0.0
        salary_date_to = 0.0
        paid_duration = 0.0
        if last_work_date:
            date_to = datetime.strptime(str(last_work_date), "%Y-%m-%d").date()
            day = date_to.day
            salary_date_to = date_to
            salary_date_from = date_to - relativedelta.relativedelta(days=day - 1)
        if salary_date_from and salary_date_to and last_work_date:
            start_date = dt.strptime(str(salary_date_from), date_format)
            end_date = dt.strptime(str(salary_date_to), date_format)
            if end_date >= start_date:
                value = relativedelta.relativedelta(end_date, start_date)
                if value.months < 1:
                    if value.days == 30:
                        paid_duration = 31
                    else:
                        paid_duration = value.days + 1
        return paid_duration

    def get_salary_rules_and_loans(self, employee, last_work_date, first_hire_date, cause_type_id):
        paid_duration = 0.0
        number_of_days = 0.0
        if last_work_date:
            last_work_date = datetime.strptime(last_work_date, "%Y-%m-%d").date()
            _, number_of_days = calendar.monthrange(last_work_date.year, last_work_date.month)
            paid_duration = self._get_paid_duration(last_work_date)
        if paid_duration > 0:
            if number_of_days == 31:
                duration_percentage = 31 / paid_duration

            elif number_of_days == 28:
                duration_percentage = 28 / paid_duration

            elif number_of_days == 29:
                duration_percentage = 29 / paid_duration
            else:
                duration_percentage = 30 / paid_duration
        else:
            duration_percentage = 1

        # Initialize values
        items = []
        # Get all advantages from contract
        if employee.sudo().contract_id:
            if employee.sudo().contract_id.advantages:
                for item in employee.sudo().contract_id.advantages:
                    if item.date_from and item.amount > 0 and last_work_date:
                        td = datetime.now().strftime('%Y-%m-%d')
                        today = datetime.strptime(str(td), "%Y-%m-%d").date()
                        start = datetime.strptime(str(item.date_from), "%Y-%m-%d").date()
                        last_work = datetime.strptime(str(last_work_date), "%Y-%m-%d").date()

                        # if item.benefits_discounts in self.calculation_method:
                        if item.date_to:
                            end = datetime.strptime(str(item.date_to), "%Y-%m-%d").date()
                            if start <= last_work <= end:
                                amount = self.compute_salary_rule(last_work_date, 0.0, employee, item.benefits_discounts, items,
                                                                  duration_percentage, item, 0, cause_type_id)
                        else:
                            if last_work >= start:
                                amount = self.compute_salary_rule(last_work_date, 0.0, employee, item.benefits_discounts, items,
                                                                  duration_percentage, item, 0, cause_type_id)
        # Get all salary rules from calculation method
        calculation_method = []
        if cause_type_id:
            calculation_method = cause_type_id.allowance_ids
        salary_for_eos = 0.0
        if calculation_method:
            total = 0.0
            for rule in calculation_method:
                if rule._origin.id:
                    rule = rule.browse([rule._origin.id])
                self.compute_salary_rule(last_work_date, 0.0, employee, rule, items, duration_percentage, False, 0, cause_type_id)
                for item in items:
                    if rule.id == item.get('salary_rule_id') and rule.category_id.rule_type == 'allowance':
                        total += item.get('amount')
                    if rule.id == item.get('salary_rule_id') and rule.category_id.rule_type == 'deduction':
                        total -= item.get('amount')
            salary_for_eos += total
        leave_balance = 0
        leave_balance_money = 0
        cause_type_amount = 0
        minus_five_years_amount = 0
        plus_five_years_amount = 0
        # Get salary rule  form cause type
        if first_hire_date and last_work_date and cause_type_id:
            start_date = dt.strptime(str(first_hire_date), "%Y-%m-%d")
            end_date = dt.strptime(str(last_work_date), "%Y-%m-%d")
            total_rules, amount_of_year, amount_of_month, amount_of_day, cause_type_amount = 0.0, 0.0, 0.0, 0.0, 0.0

            if end_date >= start_date:
                years, months, days = self.get_duration_service(first_hire_date, last_work_date)
                all_duration = months + (days / 30) + (years * 12)
                all_duration = months + (days / 30) + (years * 12)
                if cause_type_id.allowance_ids and cause_type_id.termination_duration_ids:

                    # Get total for  all salary rules form cause type
                    for rule in cause_type_id.allowance_ids:
                        rule_flag = False
                        # Check if salary rule does  not duplicated when come from contract and is allowance only
                        if rule.category_id.rule_type == 'allowance':
                            if items:
                                for record in items:

                                    if record.get('salary_rule_id') == rule.id and record.get(
                                            'is_advantage') is True and record.get('advantages_out_rule'):
                                        total_rules += record.get('amount')
                                        rule_flag = True
                                    if record.get('salary_rule_id') == rule.id and record.get(
                                            'is_advantage') is True and not record.get('advantages_out_rule'):
                                        # Change salary rule value in "salary for eos" by that in contract that is duplicated
                                        total_rules += record.get('amount') * duration_percentage
                                        rule_flag = True

                            if rule_flag is False:
                                total_rules += self.compute_rule(rule, employee.sudo().contract_id)
                    reward_amount = 0
                    resedual = all_duration
                    line_amount = 0
                    duration_to = 0
                    # search line cause_type and get amount for each line factor
                    for line in cause_type_id.termination_duration_ids:
                        line_amount = line.amount
                        if line.date_to <= all_duration:
                            if line.amount > 0:
                                duration_to = line.date_to - duration_to
                                termination_amount = total_rules * (duration_to / 12) * line.factor
                                reward_amount += termination_amount
                                resedual = all_duration - line.date_to
                                if line.date_to <= 60:
                                    minus_five_years_amount += termination_amount
                                else:
                                    plus_five_years_amount += termination_amount
                        else:
                            termination_amount = total_rules * resedual / 12 * line.factor
                            reward_amount += termination_amount
                            if line.date_to <= 60:
                                minus_five_years_amount += termination_amount
                            else:
                                plus_five_years_amount += termination_amount
                            break
                    reward_amount = reward_amount * line_amount
                    cause_type_amount = round(reward_amount, 2)
                    amount = self.compute_salary_rule(last_work_date, cause_type_amount, employee, cause_type_id.allowance_id, items,
                                                      duration_percentage, False, 1, cause_type_id)
                leave_balance = self.get_remaining_leaves(employee, last_work_date)
                leave_balance_money = self._get_holiday_amount(employee, leave_balance)
                if cause_type_id.holiday:
                    if leave_balance_money >= 0:
                        amount = self.compute_salary_rule(last_work_date, cause_type_amount, employee, cause_type_id.holiday_allowance, items,
                                                          duration_percentage, False, 1, cause_type_id)
                    if leave_balance_money < 0:
                        amount = self.compute_salary_rule(last_work_date, cause_type_amount, employee, cause_type_id.holiday_deduction, items,
                                                          duration_percentage, False, 1, cause_type_id)
        # Check if salary rule does  not duplicated when come from contract
        lines_data = []
        for item in items:
            if not item.get('is_advantage'):
                lines_data.append(item)
            for advantages in employee.sudo().contract_id.advantages:
                if advantages.benefits_discounts.id == item.get('salary_rule_id') and advantages.out_rule:
                    lines_data.append(item)
            for rule in calculation_method:
                if (rule._origin.id == item.get('salary_rule_id') or rule.id == item.get(
                        'salary_rule_id')) and item.get('is_advantage'):
                    lines_data.append(item)
        set_data2 = {tuple(item.items()) for item in lines_data}
        # Convert back to list of dictionaries
        lines_data = [dict(item) for item in set_data2]
        if lines_data:
            for record in lines_data:
                for element in lines_data:
                    if record.get('salary_rule_id') == element.get('salary_rule_id'):
                        if record.get('is_advantage') is True and element.get('is_advantage') is False:
                            lines_data.remove(element)

                            # Change salary rule value in "salary for eos" by that in contract that is duplicated
                            rule = self.env['hr.salary.rule'].browse(element.get('salary_rule_id'))
                            salary_for_eos -= (self.compute_rule(rule, employee.sudo().contract_id) / duration_percentage)
        for line in lines_data:
            del line['advantages_out_rule']
        allowance_deduction_ids = lines_data
        total_deduction = 0.0
        total_allowance = 0.0
        for allowance in allowance_deduction_ids:
            category_id = allowance["category_id"]
            if category_id.rule_type == 'deduction':
                total_deduction += allowance["amount"]
            elif category_id.rule_type == 'allowance':
                total_allowance += allowance["amount"]
            # Other salary rules treat as allowance
            elif category_id.rule_type != 'deduction':
                total_allowance += allowance["amount"]

        total_loans = 0.0
        if employee:
            record_ids = self.env['hr.loan.salary.advance'].search([
                ('state', 'in', ['pay', 'closed']),  # Include both 'pay' and 'closed' states
                ('employee_id', '=', employee.id),
                ('remaining_loan_amount', '>', 0.0)  # Ensure loan amount is greater than zero
            ])
            total = sum(record_ids.mapped("remaining_loan_amount"))
            total_loans = round(total,2)
        net = abs(round(total_allowance, 2)) - abs(round(total_deduction, 2))
        net -= abs(round(total_loans, 2))
        return {
            "allowance_deduction_ids": allowance_deduction_ids,
            "total_allowance": total_allowance,
            "leave_balance": leave_balance,
            "leave_balance_money": leave_balance_money,
            "total_loans": total_loans,
            "net": net,
            "cause_type_amount": cause_type_amount,
            "minus_five_years_amount": minus_five_years_amount,
            "plus_five_years_amount": plus_five_years_amount,
        }

    def get_duration_service(self, first_hire_date, end_date):
        if first_hire_date:
            start_date = datetime.strptime(str(first_hire_date), "%Y-%m-%d")
            end_date = datetime.strptime(str(end_date), "%Y-%m-%d") + timedelta(days=1)
            if end_date > start_date:
                r = relativedelta.relativedelta(end_date, start_date)
                years = r.years
                months = r.months
                days = r.days
                # If days >= 30, convert to months
                if days >= 30:
                    months += days // 30  # Convert extra days into months
                    days %= 30  # Keep remaining days

                # If months >= 12, convert to years
                years += months // 12
                months %= 12
                return years, months, days
            else:
                raise exceptions.Warning(_('Leaving Date  must be greater than First Hiring Date'))

    def get_remaining_leaves(self, employee_id, end_date):

        leave = self.env['hr.holidays'].search([('type', '=', 'add'),
                                                ('check_allocation_view', '=', 'balance'),
                                                ('holiday_status_id.leave_type', '=', 'annual'),
                                                ('employee_id', '=', employee_id.id)],
                                               limit=1)
        leaves_after_end_date = self.env['hr.holidays'].search([('type', '=', 'remove'),
                                                ('date_from', '>=', end_date),
                                                ('state', '=', 'validate1'),
                                                ('holiday_status_id.leave_type', '=', 'annual'),
                                                ('employee_id', '=', employee_id.id)])
        leave_balance = 0.0
        if leave.holiday_ids and end_date and leave.holiday_status_id.duration_ids:
            cron_run_date = datetime.strptime(str(leave.holiday_ids[-1].cron_run_date), "%Y-%m-%d").date()
            last_working_date = datetime.strptime(str(end_date), "%Y-%m-%d").date()
            first_hiring_date = datetime.strptime(str(leave.hiring_date), "%Y-%m-%d").date()
            last_work_date = datetime.strptime(str(end_date), "%Y-%m-%d").date()
            working_days = (last_work_date - first_hiring_date).days + 1
            working_years = working_days / 365
            holiday_duration = 0.0
            for item in leave.holiday_status_id.duration_ids:
                if item.date_from <= working_years < item.date_to:
                    holiday_duration = item.duration
            ###get last cron date to compute leave_balance_date
            new_balance=0
            """the last working date less than cron run date"""
            if cron_run_date < last_working_date:
               diff_days = (last_working_date - cron_run_date).days
               for i in range(1, diff_days + 1):
                   cala_date = cron_run_date + timedelta(days=i)
                   balance_day = leave.remaining_leaves_of_day_by_date(employee_id, str(cala_date),
                                   leave.holiday_status_id , is_month=False, is_years=False)
                   new_balance = new_balance + balance_day
            else:
               diff_days = -(cron_run_date - last_working_date).days
               for i in range(1, -diff_days + 1):
                   cala_date = last_working_date + timedelta(days=i)
                   balance_day = leave.remaining_leaves_of_day_by_date(employee_id, str(cala_date),
                                   leave.holiday_status_id , is_month=False, is_years=False)
                   new_balance = new_balance - balance_day
            ####################### END
            leave_balance = round(employee_id.remaining_leaves + new_balance, 2)

            exceed_days = leave.holiday_status_id.number_of_save_days + holiday_duration
            if leave_balance > exceed_days:
                leave_balance = exceed_days
            else:
                leave_balance = round(employee_id.remaining_leaves + new_balance, 2)
            if leaves_after_end_date:
                leave_balance += sum(leave.number_of_days_temp for leave in leaves_after_end_date)
        return leave_balance

    def get_value(self, data):
        type = data['form']['type']
        employee_ids = data['form']['employee_ids']
        cause_type_id = data['form']['cause_type']
        cause_type_name = self.env['hr.termination.type'].search([('id', '=', cause_type_id)])
        allowance_ids = data['form']['allowance_ids']
        date_from = data['form']['date_from']
        date_to = data['form']['date_to']
        end_date = data['form']['end_date']
        termination_model = self.env['hr.termination']
        data = {'total_rule': {},
                'total_sum': {
                    'remaining_leaves': 0.0,
                    'ticket_num': 0.0,
                    'ticket_price': 0.0,
                    'lave_price': 0.0,
                    'termination_price': 0.0,
                    'five_year_price': 0.0,
                    'amount': 0.0,
                    'total': 0.0
                },
                'end_date': end_date}
        key_list = []
        employee_ids = self.env['hr.employee'].search([('id', 'in', employee_ids)])
        rules_ids = self.env['hr.salary.rule'].search([('id', 'in', allowance_ids)])
        if not employee_ids:
          raise exceptions.Warning(_('Sorry, Not Select Employees'))
        for emp in employee_ids:
            total = 0.0
            ticket_num = 0
            ticket_price = 0.0
            cause_amount = 0.0
            five_cause_amount = 0
            amount = 0
            number_year = '0:0:0'
            if emp.first_hiring_date:
                year, month, day = self.get_duration_service(emp.first_hiring_date, end_date)
            if type == 'all' or type == 'termination':
                cause_amount, five_cause_amount, amount = self.get_cause_amount(emp.first_hiring_date, cause_type_name,
                                                                                end_date, emp)
            if emp.check_nationality ==False and (type == 'all' or type == 'ticket'):
                ticket = self.env['hr.ticket.request'].search([('employee_id', '=', emp.id), ('state', '=', 'done'),('mission_check','=',False)])
                if ticket:
                    if len(ticket) != year:
                        if len(ticket) < year:
                            ticket_num = year - len(ticket)
                            ticket_price = ticket_num * emp.contract_id.ticket_allowance
                    else:
                        ticket_num = 0
                else:
                    #if year < 2:
                    ticket_num = year
                    ticket_price = ticket_num * emp.contract_id.ticket_allowance
                    #else:
                        #ticket_num = 2
                        #ticket_price = ticket_num * emp.contract_id.ticket_allowance
            number_year = ' سنه %s : شهر%s : يوم%s' % (year, month, day)
            salary = 0.0
            result = self.get_salary_rules_and_loans(emp, end_date, emp.first_hiring_date, cause_type_name)
            total_allowance = result["total_allowance"]
            total_loans = result["total_loans"]
            net = result["net"]
            plus_five_years_amount = result["plus_five_years_amount"]
            minus_five_years_amount = result["minus_five_years_amount"]
            cause_type_amount = result["cause_type_amount"]
            leave_balance = result["leave_balance"]
            leave_balance_money = result["leave_balance_money"]
            data[emp.name] = {
                'date': emp.first_hiring_date,
                'termination_reson': cause_type_name.name,
                'remind_leave_day': leave_balance,
                'experiences_year': number_year,
                'ticket': ticket_num,
                'ticket_price': ticket_price,
                'leave_price': '',
                # 'leave_price': leave_balance_money,
                'termination_price': cause_type_amount,
                'five_year_price': minus_five_years_amount,
                'amount': plus_five_years_amount,
                'total': total_allowance,
                'total_salary': 0.0,
                'rule': '',
                'employee_name': emp.name,

            }
            rules = {}
            lave_price = 0.0
            if type == 'all' or type == 'salary' or type == 'leave':
                for rule in rules_ids:
                    rule_amount = termination_model.compute_rule(rule, emp.contract_id)
                    if type == 'all' or type == 'salary':
                        rules[rule.name] = rule_amount
                        name = rule.name
                        if name not in data['total_rule']:
                            data['total_rule'][name] = rule_amount
                        else:
                            data['total_rule'][name] += rule_amount
                    salary += rule_amount
                if type == 'all' or type == 'salary':
                    if 'total_salary' not in data['total_rule']:
                        data['total_rule']['total_salary'] = salary
                    else:
                        data['total_rule']['total_salary'] += salary
                    data[emp.name]['rule'] = rules
                    data[emp.name]['total_salary'] = salary
                if type == 'all' or type == 'leave':
                    if salary > 0:
                        amount_per_day = salary / 30
                        lave_price = leave_balance*amount_per_day
                    if 'lave_price' not in data['total_sum']:
                        data['total_sum']['lave_price'] = lave_price
                    else:
                        data['total_sum']['lave_price'] += lave_price
                data[emp.name]['leave_price'] = lave_price
            key_list.append(emp.name)
            data['total_sum']['ticket_price'] += ticket_price
            data['total_sum']['ticket_num'] += ticket_num
            data['total_sum']['remaining_leaves'] += leave_balance
            # data['total_sum']['lave_price'] += leave_balance_money
            data['total_sum']['termination_price'] += cause_type_amount
            data['total_sum']['five_year_price'] += minus_five_years_amount
            data['total_sum']['amount'] += plus_five_years_amount
            data['total_sum']['total'] += total_allowance
        mykey = list(dict.fromkeys(key_list))
        return data, mykey

    @api.model
    def _get_report_values(self, docids, data=None):
        data_dic, mykey = self.get_value(data)
        allowance_ids = data['form']['allowance_ids']
        len_of_salary = len(allowance_ids)
        type = data['form']['type']
        date_to = data['form']['date_to']
        return {
            'doc_ids': data['ids'],
            'doc_model': data['model'],
            'type': type,
            'data': data_dic,
            'mykey': mykey,
            'len_of_salary': len_of_salary,
            'date_to': date_to,
        }
class TerminationReportXls(models.AbstractModel):
    _name = 'report.hr_termination.termination_benefits_xls'
    _inherit = 'report.report_xlsx.abstract'

    def generate_xlsx_report(self, workbook, data, datas):
        x = self.env['report.hr_termination.termination_report_temp']
        final_dic, mykey = ReportTerminationPublic.get_value(x, data)
        type = data['form']['type']
        allowance_ids = data['form']['allowance_ids']
        len_of_salary = len(allowance_ids)
        sheet = workbook.add_worksheet(U'Holiday Report')
        sheet.right_to_left()
        format2 = workbook.add_format(
            {'font_size': 10, 'bottom': True, 'right': True, 'left': True, 'top': True, 'align': 'center',
             'bold': True})
        format2.set_align('center')
        format2.set_align('vcenter')
        sheet.merge_range('B2:P2', _("تقرير المخصصات حتى تاريخ") + data['form']['end_date'], format2)
        sheet.write(3, 1, ('اسم الموظف'), format2)
        sheet.write(3, 2, ('تاريخ المباشرة '), format2)
        z = 'D' + str(4)
        y = 'E' + str(3)
        x = len_of_salary + 3
        not_salary = 3
        if type == 'all' or type == 'salary':
            sheet.merge_range(3, 3, 3, x, ('الراتب الشهري '), format2)
            flag = 1
            x = 3
            for key in mykey:
                if flag == 1:
                    for rule in final_dic[key]['rule']:
                        sheet.write(4, x, rule, format2)
                        x += 1
                    flag += 1
                sheet.write(4, len_of_salary + 3, ('المجموع'), format2)
            sheet.write(3, len_of_salary + 4, ('سنوات الخدمة(سنة/شهر/يوم)'), format2)
            sheet.write(3, len_of_salary + 5, ('سبب إنهاء الخدمة'), format2)
        else:
            sheet.write(3, not_salary, ('سنوات الخدمة(سنة/شهر/يوم)'), format2)
            sheet.write(3, not_salary + 1, ('سبب إنهاء الخدمة'), format2)
        if type == 'leave':
            sheet.write(3, not_salary + 2, ('رصيد الإجازة'), format2)
            sheet.write(3, not_salary + 3, ('قيمة الإجازة'), format2)
        if type == 'all':
            sheet.write(3, len_of_salary + 6, ('رصيد الإجازة'), format2)
            sheet.write(3, len_of_salary + 7, ('عدد تذاكر السفر المستحقة'), format2)
            sheet.write(3, len_of_salary + 8, ('مبلغ تذكرة السفر'), format2)
            sheet.write(3, len_of_salary + 9, ('قيمة الإجازة'), format2)
            sheet.merge_range(3, len_of_salary + 10, 3, len_of_salary + 11, ('نهاية الخدمة '), format2)
            sheet.write(4, len_of_salary + 10, ('نهاية الخدمة لأقل من 5 سنة'), format2)
            sheet.write(4, len_of_salary + 11, ('نهاية الخدمة لأكبر من 5 سنة'), format2)
            sheet.write(3, len_of_salary + 12, ('قيمة نهاية الخدمة'), format2)
            sheet.write(3, len_of_salary + 13, ('إجمالي المستحق'), format2)
        if type == 'ticket':
            sheet.write(3, not_salary + 2, ('عدد تذاكر السفر المستحقة'), format2)
            sheet.write(3, not_salary + 3, ('مبلغ تذكرة السفر'), format2)
        if type == 'termination':
            sheet.merge_range(3, not_salary + 2, 3, not_salary + 3, ('قيمة نهاية الخدمة '), format2)
            sheet.write(4, not_salary + 2, ('نهاية الخدمة لأقل من5 سنة'), format2)
            sheet.write(4, not_salary + 3, ('قيمة نهاية الخدمة لأكبر من 5 سنة'), format2)
            sheet.write(3, not_salary + 5, ('قيمة نهاية الخدمة'), format2)
            #sheet.write(3, not_salary + 4, ('إجمالي المستحق'), format2)

        if type == 'salary':
            sheet.write(3, len_of_salary + 6, ('إجمالي المستحق'), format2)
        #if type != 'salary' and type != 'all' and type != 'termination':
            #sheet.write(3, not_salary + 4, ('إجمالي المستحق'), format2)
        row = 4
        for key in mykey:
            row += 1
            n = 3
            data_row = 3
            sheet.write(row, 1, final_dic[key]['employee_name'], format2)
            sheet.write(row, 2, final_dic[key]['date'], format2)
            if type == 'all' or type == 'salary':
                for rule in final_dic[key]['rule']:
                    sheet.write(row, n, final_dic[key]['rule'][rule], format2)
                    n += 1
                sheet.write(row, data_row + len_of_salary, final_dic[key]['total_salary'], format2)
                sheet.write(row, data_row + len_of_salary + 1, final_dic[key]['experiences_year'], format2)
                sheet.write(row, data_row + len_of_salary + 2, final_dic[key]['termination_reson'], format2)
            else:
                sheet.write(row, data_row, final_dic[key]['experiences_year'], format2)
                sheet.write(row, data_row + 1, final_dic[key]['termination_reson'], format2)
            if type == 'leave':
                sheet.write(row, data_row + 2, final_dic[key]['remind_leave_day'], format2)
                sheet.write(row, data_row + 3, final_dic[key]['leave_price'], format2)
            if type == 'all':
                sheet.write(row, data_row + len_of_salary + 3, final_dic[key]['remind_leave_day'], format2)
                sheet.write(row, data_row + len_of_salary + 4, final_dic[key]['ticket'], format2)
                sheet.write(row, data_row + len_of_salary + 5, final_dic[key]['ticket_price'], format2)
                sheet.write(row, data_row + len_of_salary + 6, final_dic[key]['leave_price'], format2)
                sheet.write(row, data_row + len_of_salary + 7, final_dic[key]['five_year_price'], format2)
                sheet.write(row, data_row + len_of_salary + 8, final_dic[key]['amount'], format2)
                sheet.write(row, data_row + len_of_salary + 9, final_dic[key]['termination_price'], format2)
                sheet.write(row, data_row + len_of_salary + 10, final_dic[key]['total'], format2)
            if type == 'ticket':
                sheet.write(row, data_row + 2, final_dic[key]['ticket'], format2)
                sheet.write(row, data_row + 3, final_dic[key]['ticket_price'], format2)
            if type == 'termination':
                sheet.write(row, data_row + 1, final_dic[key]['termination_reson'], format2)
                sheet.write(row, data_row + 2, final_dic[key]['five_year_price'], format2)
                sheet.write(row, data_row + 3, final_dic[key]['amount'], format2)
                sheet.write(row, data_row + 4, final_dic[key]['termination_price'], format2)
                #sheet.write(row, data_row + 5, final_dic[key]['total'], format2)
            if type == 'salary':
                sheet.write(row, len_of_salary + 6, final_dic[key]['total'], format2)
            #if type != 'salary' and type != 'all' and type != 'termination':
                #sheet.write(row, data_row + 4, final_dic[key]['total'], format2)
        y = len(final_dic) + 1 + len_of_salary + 1
        sheet.merge_range(y, 1, y, 2, _('الاجمالى'), format2)
        m = 3
        for tot_rule in final_dic['total_rule']:
            sheet.write(y, m, final_dic['total_rule'][tot_rule], format2)
            m += 1
        m = m + 2
        if type == 'all' or type == 'leave':
            sheet.write(y, m, final_dic['total_sum']['remaining_leaves'], format2)
        if type == 'all' or type == 'ticket':
            sheet.write(y, m + 1, final_dic['total_sum']['ticket_num'], format2)
            sheet.write(y, m + 2, final_dic['total_sum']['ticket_price'], format2)
        if type == 'all' or type == 'leave':
            sheet.write(y, m + 3, final_dic['total_sum']['lave_price'], format2)
        if type == 'all' or type == 'termination':
            sheet.write(y, m + 4, final_dic['total_sum']['five_year_price'], format2)
            sheet.write(y, m + 5, final_dic['total_sum']['amount'], format2)
            sheet.write(y, m + 6, final_dic['total_sum']['termination_price'], format2)
        sheet.write(y, m + 7, final_dic['total_sum']['total'], format2)
