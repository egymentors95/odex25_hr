# -*- coding: utf-8 -*-

from odoo import api, fields, models, _, exceptions
from datetime import date


class EmployeesAppraisal(models.Model):
    _name = 'hr.group.employee.appraisal'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'
    _description = 'Appraisal'

    name = fields.Char()
    date = fields.Date()
    state = fields.Selection([("draft", _("Draft")),
                              ("gen_appraisal", _("Generate Appraisal")),
                              ("start_appraisal", _("Start Appraisal")),
                              ("finish_appraisal", _("Direct Manager")),
                              ("hr_approval", _("Department Manager")),
                              ("gm_approval", _("HR Approval")),
                              ("done", _("Done"))], default='draft', tracking=True)

    # Relational fields
    department_id = fields.Many2one('hr.department')
    manager_id = fields.Many2one('hr.employee', related='department_id.manager_id')
    employee_ids = fields.Many2many('hr.employee')
    appraisal_id = fields.One2many('hr.employee.appraisal', 'employee_appraisal')
    appraisal_plan_id = fields.Many2one('appraisal.plan')

    totals_great_level = fields.Float(compute='fill_totals_great_level', tracking=True)
    totals_level_achieved = fields.Float(compute='fill_totals_great_level', tracking=True)
    totals_level_achieved_percentage = fields.Float(compute='fill_totals_great_level', tracking=True)
    totals_appraisal_result = fields.Many2one('appraisal.result', tracking=True, compute='fill_totals_great_level')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)

    appraisal_type = fields.Selection(selection=[('performance', 'Performance'),
                                                 ('trial', 'Trial Period'),
                                                 ('training', 'Training'),
                                                 ('mission', 'Mission'),
                                                 ('general', 'General'),
                                                 ('other', 'Other')], string='Appraisal Type')
    employee_protest = fields.Boolean(
        readonly=True, 
        states={'draft': [('readonly', False)]}
    )


    # Dynamic domain for manager_id
    @api.onchange('department_id')
    def manager_domain(self):
        for item in self:
            if item.department_id:
                employee_ids = self.env['hr.employee'].search([])
                employee_list = []

                # Domain for manager_id
                if not item.department_id.manager_id:
                    item.manager_id = False
                    for line in employee_ids:
                        if line.department_id:
                            if line.department_id == item.department_id:
                                employee_list.append(line.id)
                    return {'domain': {'manager_id': [('id', 'in', employee_list)]}}

    # Dynamic domain for employee_ids

    @api.onchange('department_id')
    def employee_ids_domain(self):
        for item in self:
            if item.department_id:
                department_ids = self.env['hr.department'].search([])
                employee_ids = self.env['hr.employee'].search([])

                department_list, employee_list = [], []

                # Adding the selected department to department_list
                department_list.append(item.department_id.id)

                # Domain for employee_ids
                for line in department_ids:
                    if line.parent_id:
                        if line.parent_id == item.department_id:
                            department_list.append(line.id)
                            for sub_line in department_ids:
                                if sub_line.parent_id == line:
                                    department_list.append(sub_line.id)
                for line in employee_ids:
                    if line.department_id:
                        if line.department_id.id in department_list:
                            employee_list.append(line.id)
                if item.department_id:
                    return {'domain': {'employee_ids': [('id', 'in', employee_list)]}}

            # Create records in hr.employee.appraisal when change state to Generate Appraisal

    def gen_appraisal(self):
        for item in self:
            if item.employee_ids:
                appraisal_lines = []

                # Fill employee appraisal
                for element in item.employee_ids:
                    standard_appraisal_list, manager_appraisal_list = [], []

                    if not item.appraisal_plan_id.is_manager:
                        # Fill standard_appraisal_employee_line_ids to complete
                        for line in item.appraisal_plan_id.standard_appraisal_id:
                            standard_appraisal_list.append({
                                'great_level': line.great_level,
                                'question': line.question
                            })
                    else:
                        # Fill manager_appraisal_line_id to complete
                        for line in item.appraisal_plan_id.manager_appraisal_id:
                            complete_manager_appraisal_list = []
                            for record in line.question_id.customize_appraisal_id:
                                complete_manager_appraisal_list.append({
                                    'question': record.question,
                                    'great_degree_level': record.great_degree_level,
                                    'degree_id': record.degree_id.id
                                })
                            record = self.env['manager.appraisal.complete.line'].create({
                                'name': line.question_id.name,
                                'great_level': line.great_level,
                                'customize_appraisal_id': [(0, 0, value) for value in complete_manager_appraisal_list]
                            })
                            manager_appraisal_list.append({
                                'appraisal_name': line.appraisal_name,
                                'question_id': line.question_id.id,
                                'question_complete_id': record.id
                            })
                    appraisal_line = {
                        'employee_id': element.id,
                        'appraisal_date': date.today(),
                        'is_manager': item.appraisal_plan_id.is_manager,
                        'appraisal_plan_id': item.appraisal_plan_id.id,
                        'appraisal_type': item.appraisal_type,
                        'standard_appraisal_employee_line_ids': [(0, 0, value) for value in standard_appraisal_list],
                        'manager_appraisal_line_id': [(0, 0, value) for value in manager_appraisal_list],
                        'employee_protest': item.employee_protest
                    }
                    line_id = self.env['hr.employee.appraisal'].create(appraisal_line)

                    # Initialize
                    total_greed, total_great_level, line_id.level_achieved, line_id.great_level = 0.0, 0.0, 0.0, 0.0
                    appraisal_result_list = []

                    if not line_id.is_manager:
                        for line in line_id.standard_appraisal_employee_line_ids:
                            # Update level achieved values when changed in lines
                            total_greed += line.greed
                            total_great_level += line.great_level
                        line_id.great_level = total_great_level
                        line_id.level_achieved = total_greed

                        # Update level achieved percentage when changed in lines
                        if line_id.level_achieved > 0.0 and line_id.great_level > 0.0:
                            line_id.level_achieved_percentage = (line_id.level_achieved * 100) / line_id.great_level

                        # Determine which appraisal result from appraisal percentage
                        appraisal_result = self.env['appraisal.result'].search([
                            ('result_from', '<', line_id.level_achieved_percentage),
                            ('result_to', '>=', line_id.level_achieved_percentage)])

                        if len(appraisal_result) > 1:
                            for line in appraisal_result:
                                appraisal_result_list.append(line.name)
                            raise exceptions.Warning(
                                _('Please check appraisal result configuration , there is more than result for '
                                  'percentage %s  are %s ') % (
                                    round(line_id.level_achieved_percentage, 2), appraisal_result_list))
                        else:
                            line_id.appraisal_result = appraisal_result.id

                    elif line_id.is_manager:
                        for line in line_id.manager_appraisal_line_id:
                            # Update level achieved values when changed in lines
                            total_greed += line.total
                            total_great_level += line.great_level
                        line_id.great_level = total_great_level
                        line_id.level_achieved = total_greed

                        # Update level achieved percentage when changed in lines
                        if line_id.level_achieved > 0.0 and line_id.great_level > 0.0:
                            line_id.level_achieved_percentage = (line_id.level_achieved * 100) / line_id.great_level

                        # Determine which appraisal result from appraisal percentage
                        appraisal_result = self.env['appraisal.result'].search([
                            ('result_from', '<', line_id.level_achieved_percentage),
                            ('result_to', '>=', line_id.level_achieved_percentage)])

                        if len(appraisal_result) > 1:
                            for line in appraisal_result:
                                appraisal_result_list.append(line.name)
                            raise exceptions.Warning(
                                _('Please check appraisal result configuration , there is more than result for '
                                  'percentage %s  are %s ') % (
                                    round(line_id.level_achieved_percentage, 2), appraisal_result_list))
                        else:
                            line_id.appraisal_result = appraisal_result.id
                    appraisal_lines.append(line_id.id)
                item.appraisal_id = self.env['hr.employee.appraisal'].browse(appraisal_lines)
            else:
                raise exceptions.Warning(_('Please select at least one employee to make appraisal.'))
            item.state = 'gen_appraisal'

    def start_appraisal(self):
        self.state = 'start_appraisal'

    def finish_appraisal(self):
        # Check if there is appraisal for employee in not in state done
        if self.appraisal_id:
            employee_appraisal_list = []
            for line in self.appraisal_id:
                if line.state != 'state_done':
                    employee_appraisal_list.append(line.employee_id.name)
            if employee_appraisal_list:
                raise exceptions.Warning(
                    _('Appraisal for employees "%s" is not in state done') % employee_appraisal_list)

        self.state = 'finish_appraisal'

    def hr_approval(self):
        self.state = 'hr_approval'

    def gm_approval(self):
        self.state = 'gm_approval'

    def state_done(self):
        # make all appraisal for all employees done
        if self.appraisal_id:
            for line in self.appraisal_id:
                line.state = 'closed'
        self.state = 'done'

    def draft(self):
        # Delete all appraisal when re-draft
        if self.appraisal_id:
            for line in self.appraisal_id:

                if line.state == 'draft':
                    line.unlink()
                    self.state = 'draft'

                elif line.state == 'closed':
                    line.state = 'state_done'
                    self.state = 'start_appraisal'

                elif line.state == 'state_done':
                    self.state = 'start_appraisal'

    # Override unlink function
    def unlink(self):
        for i in self:
            if i.state != 'draft':
                raise exceptions.Warning(_('You can not delete record in state not in draft'))
        return super(EmployeesAppraisal, self).unlink()

    # Fill total great level

    @api.depends('appraisal_id')
    def fill_totals_great_level(self):
        for item in self:
            item.totals_great_level = 0
            item.totals_level_achieved = 0
            item.totals_level_achieved_percentage = 0
            item.totals_appraisal_result = 0
            for element in item.appraisal_id:
                count_elment = 0
                appraisal_result_list = []
                # for line in element:
                count_elment += len(item.appraisal_id)
                item.totals_great_level += element.great_level / count_elment
                item.totals_level_achieved += element.level_achieved / count_elment
                item.totals_level_achieved_percentage = (item.totals_level_achieved / item.totals_great_level) * 100

                totals_appraisal_result = self.env['appraisal.result'].search([
                    ('result_from', '<=', item.totals_level_achieved_percentage),
                    ('result_to', '>=', item.totals_level_achieved_percentage)])
                if len(totals_appraisal_result) > 1:
                    for line in totals_appraisal_result:
                        appraisal_result_list.append(line.name)
                    raise exceptions.Warning(
                        _('Please check appraisal result configuration , there is more than result for percentage %s  are %s ') % (
                            round(item.totals_level_achieved_percentage, 2), appraisal_result_list))
                else:
                    item.totals_appraisal_result = totals_appraisal_result.id
