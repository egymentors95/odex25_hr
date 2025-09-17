# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
import logging

AVAILABLE_PRIORITIES = [
    ('0', 'Draft'),
    ('1', 'Normal'),
    ('2', 'Accept'),
    ('3', 'Good'),
    ('4', 'Very Good'),
    ('5', 'Excellent')]
_logger = logging.getLogger(__name__)


class Applicant(models.Model):
    _inherit = 'hr.applicant'

    answer = fields.Text()
    number = fields.Integer()
    applicants_id = fields.Many2one('applicant.questions', string="Applicant Questions")

    standard_applicant_employee_line_ids = fields.One2many('applicant.questions.line',
                                                           'standard_applicant_employee_line')
    priority = fields.Selection(AVAILABLE_PRIORITIES, "Appreciation", default='0')

    applicants_hr = fields.Many2one('applicant.questions', string="Applicant Questions")

    standard_applicant_hr_line_ids = fields.One2many('applicant.questions.line', 'standard_applicant_hr_line')

    # start_compute = fields.Char(compute='fill_employee_applicant')

    @api.depends('applicants_id')
    def fill_employee_applicant(self):
        for item in self:
            standard_applicant_list = []
            if item.applicants_id:
                # Fill standard_applicant_employee_line_ids to complete
                for line in item.applicants_id.standard_applicant_id:
                    standard_applicant_list.append({
                        'number': line.number,
                        'question': line.question
                    })
                item.standard_applicant_employee_line_ids = [(0, 0, value) for value in standard_applicant_list]

    @api.depends('applicants_hr')
    def fill_employee_applicant2(self):
        for item in self:
            # Fill standard_applicant_hr_line_ids to complete
            standard_applicant_list2 = []
            if item.applicants_hr:
                # Fill standard_applicant_hr_line_ids to complete
                for line in item.applicants_hr.standard_applicant_id:
                    standard_applicant_list2.append({
                        'number': line.number,
                        'question': line.question
                    })
                item.standard_applicant_hr_line_ids = [(0, 0, value) for value in standard_applicant_list2]

    @api.onchange('applicants_id')
    def onchange_applicants(self):
        # if self.standard_applicant_employee_line_ids:
        self.standard_applicant_employee_line_ids = False
        self.fill_employee_applicant()

    @api.onchange('applicants_hr')
    def onchange_applicants2(self):
        # if self.standard_applicant_employee_line_ids:
        self.standard_applicant_hr_line_ids = False
        self.fill_employee_applicant2()


class ApplicantQuestionsLines(models.Model):
    _name = 'applicant.questions.line'
    _rec_name = 'question'
    _description = 'Applicant Questions line'

    question = fields.Text()
    answer = fields.Text()
    number = fields.Integer()
    # Relational fields
    standard_applicant_employee_line = fields.Many2one('hr.applicant')  # inverse field
    standard_applicant_hr_line = fields.Many2one('hr.applicant')  # inverse field

    low_score = fields.Boolean("Low Score", default=False)
    average_score = fields.Boolean("Average Score", default=False)
    high_score = fields.Boolean("High Score", default=False)


class ApplicantQuestions(models.Model):
    _name = 'applicant.questions'

    name = fields.Char()
    standard_applicant_id = fields.One2many('hr.applicant.questions', 'standard_question_line')


class HrApplicantQuestions(models.Model):
    _name = 'hr.applicant.questions'

    _rec_name = 'question'

    number = fields.Integer()
    question = fields.Text()

    # Relational fields
    standard_question_line = fields.Many2one('applicant.questions')  # inverse field
