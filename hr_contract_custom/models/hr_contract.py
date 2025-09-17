# -*- coding: utf-8 -*-

import datetime
from datetime import datetime as dt
from datetime import timedelta
from dateutil import relativedelta
from hijri_converter import convert
# from googletrans import Translator

from odoo import models, fields, api, _, exceptions

# translator = Translator()


# Contract
class Contract(models.Model):
    _inherit = 'hr.contract'

    name = fields.Char(related="employee_id.emp_no", readonly=True, string='Employee Number')
    state = fields.Selection(selection=[('draft', _('Draft')),
                                        ('employeed_aproval', _('Employeed Approval')),
                                        ('hr_head_approval', _('HR Head Approval')),
                                        ('program_directory', _('Executive Approval')),
                                        ('end_contract', _('End Contract'))], default="draft", tracking=True)

    active = fields.Boolean(default=True)
    employee_name = fields.Char(related="employee_id.name", readonly=True)
    employee_type = fields.Selection(selection=[('saudi', _('Saudi')), ('foreign', _('Foreign')),
                                                ('displaced', _('Displaced Tribes')),
                                                ('external', _('Outsource1')), ('external2', _('Outsource2'))],
                                     default='saudi',
                                     tracking=True)
    contract_status = fields.Selection(selection=[('single', _('single contract')),
                                                  ('marriage', _('marriage contract'))], default='single',
                                       tracking=True)
    contract_duration = fields.Selection(selection=[('3_months', _('3 Months')),
                                                    ('6_months', _('6 Months')),
                                                    ('9_months', _('9 Months')),
                                                    ('12_months', _('12 Months')),
                                                    ('24_months', _('24 Months')), ('36_months', _('36 Months')),
                                                    ('none', _('None'))], default='12_months')
    experience_year = fields.Integer()
    has_end_service_benefit = fields.Boolean(string='Has end service benefits')

    # fields on salary information page
    suspended = fields.Boolean(string='Suspended')
    social_insurance = fields.Boolean(string='Social Insurance')
    salary = fields.Float(string='Base Salary', tracking=True)

    # fields of information page
    wage = fields.Float()
    advatages = fields.Text()
    trial_date_start = fields.Date(tracking=True)
    trial_date_end = fields.Date(tracking=True)
    date_start = fields.Date(tracking=True)
    date_end = fields.Date(tracking=True)
    note = fields.Text()
    # fields of dependent page
    employee_code = fields.Char()
    allow_mbl = fields.Boolean(string='Allow Mobile Allowance')
    sign_bonous = fields.Boolean(string='Sign on Bounus')
    loan_allow = fields.Boolean(string='Allow Loan Allowance')
    air_allow = fields.Boolean(string='Air Allowance')
    adults = fields.Integer(string='Adult(s)')
    # children = fields.Integer()
    infants = fields.Integer()
    package = fields.Float()
    gosi = fields.Boolean(string='GOSI')
    # vehicle_attendance = fields.Integer(string='Vehicle Attendance')
    # system_attendance = fields.Integer(string='System Attendance')
    # line_manager_attendance = fields.Integer(string='Line Manager Attendance')
    # expense_claim = fields.Float(string='Expense Claim')
    # hr_visa_ticket = fields.Float(string='HR Visa/Ticket')
    # other_allowances = fields.Float(string='Other Allowances')
    # advance_salary = fields.Float(string='Advance AGT Salary')
    hr_expense = fields.Float(string='Hr Expense')
    cash_sales = fields.Float(string='Cash Sales')
    traffic_fine = fields.Float(string='Traffic Fine')
    bk_balance = fields.Float(string='Bank Balance')
    other_deductions = fields.Float(string='Other Deductions')

    fn = fields.Char(string="First Name")
    mn = fields.Char("Middle Name")
    ln = fields.Char(string="Last Name")
    dn = fields.Char(string="Display Name")
    e_date = fields.Date(string="Effective Date")

    status = fields.Selection(selection=[('bachelor', 'Bachelor'), ('family', 'family')], string='Status')
    hra = fields.Char("HRA")
    t_allow = fields.Float(string="Transport Allowance")
    f_allow = fields.Float(string="Food Allowance")
    f_ot = fields.Float(string="Fixed OT")
    departure = fields.Char(string="Departure Air Port")
    destination = fields.Char(string="Destination Air Port")
    medical = fields.Selection(selection=[('yes', 'Yes'), ('no', 'No')], string='Medical')

    c_accommodation = fields.Selection(selection=[(
        'yes', 'Yes'),
        ('no', 'No')], string='Company Accommodation')

    c_vehicle = fields.Selection(selection=[(
        'yes', 'Yes'),
        ('no', 'No')], string='Company Vehicle')

    c_vacation = fields.Selection(selection=[(
        '12', '12 Months'),
        ('18', '18 Months'),
        ('24', '24 Months')], string='Contractual Vacation')

    nod = fields.Selection(selection=[(
        '12', '12 Months'),
        ('18', '18 Months'),
        ('24', '24 Months')], string='Number of days')

    probation = fields.Selection(selection=[(
        '3', '3 Months'),
        ('6', '6 Months')], string='Probation')

    dependent = fields.Selection(selection=[(
        '1', '1+1 '),
        ('2', '1+2 '),
        ('3', '1+3 '),
        ('all', 'All ')], string='Dependent')

    incentive = fields.Selection(selection=[(
        'yes', 'Yes'),
        ('no', 'No')], string='Incentive')

    monthly_salary = fields.Float(string='Monthly Salary', compute='_compute_monthly_salary')
    saudi_emp_type = fields.Selection([('saudi-contract', _('Saudi Contracting')),
                                       ('saudi-non', _('Saudi Non-Contracting'))], _('Saudi Employee Type'),
                                      default='saudi-contract')

    contract_type = fields.Selection([('local', _('Local')), ('international', _('International'))], _('Contract Type'))

    contract_description = fields.Selection([('locum', _('Temporary')), ('permanent', _('Permanent'))],
                                            _('Contract Description'), default='permanent')

    house_allowance_type = fields.Selection([('none', _('None')), ('perc', _('Percentage')), ('num', _('Number'))],
                                            _('House Allowance Type'), default='none')
    house_allowance = fields.Float(_('House Allowance'))
    salary_insurnce = fields.Float(string='Salary Insurnce')
    overtime_eligible = fields.Selection([('yes', _('Yes')), ('no', _('No'))], _('Overtime Eligibility'), default='no')
    overtime_eligible_float = fields.Float(_('Overtime Eligibility Amount'))
    exit_and_return = fields.Selection([('yes', _('Yes')), ('no', _('No'))], _('Exit and Return'), default='no')
    exit_and_return_amount = fields.Float(_('Exit and Return Amount'), default=200)

    air_ticket_eligible = fields.Selection([('yes', _('Yes')), ('no', _('No'))],
                                           _('Air Ticket Eligible'), default='no')
    annual_leave = fields.Selection([('yes', 'Yes'), ('no', 'No')], string='Annual Leave', default="no")
    annual_leave_days = fields.Float(string='Annual Leave In Days')
    transport_allowance_type = fields.Selection(
        [('none', _('None')), ('perc', _('Percentage')), ('num', _('Number')), ('company', 'By Company')],
        _('Transportation Allowance Type'), default='none')
    transport_allowance = fields.Float(_('Transportation Allowance'))

    transport_allowance_temp = fields.Float(string='Transportation Allowance', compute='_get_amount')

    field_allowance_type = fields.Selection(
        [('none', _('None')), ('perc', _('Percentage')), ('num', _('Number')), ('company', 'By Company')],
        _('Field Allowance Type'), default='none')
    field_allowance = fields.Float(_('Field Allowance'))

    field_allowance_temp = fields.Float(string='Field Allowance', compute='_get_amount')

    special_allowance_type = fields.Selection([('none', _('None')), ('perc', _('Percentage')), ('num', _('Number'))],
                                              _('Special Allowance Type'), default='none')
    special_allowance = fields.Float(_('Special Allowance'))
    special_allowance_temp = fields.Float(_('Special Allowance'), compute='_get_amount')

    other_allowance_type = fields.Selection([('none', _('None')), ('perc', _('Percentage')), ('num', _('Number'))],
                                            _('Other Allowances Type'), default='none')
    other_allowance = fields.Float(_('Other Allowances'))
    other_allowance_temp = fields.Float(_('Other Allowances'), compute='_get_amount')

    travel_allowance_type = fields.Selection([('none', _('None')), ('perc', _('Percentage')), ('num', _('Number'))],
                                             _('Travel Allowance Type'), default='none')
    travel_allowance = fields.Float(_('Travel Allowance'))
    travel_allowance_temp = fields.Float(_('Travel Allowance'), compute='_get_amount')
    education_allowance_type = fields.Selection([('none', _('None')), ('perc', _('Percentage')), ('num', _('Number'))],
                                                _('Education Allowance Type'), default='none')
    education_allowance = fields.Float(_('Education Allowance'))
    education_allowance_temp = fields.Float(_('Education Allowance'), compute='_get_amount')

    food_allowance_type = fields.Selection([('none', _('None')), ('perc', _('Percentage')), ('num', _('Number'))],
                                           _('Food Allowance Type'), default='none')
    food_allowance2 = fields.Float(_('Food Allowance'))
    food_allowance2_temp = fields.Float(_('Food Allowance'), compute='_get_amount')

    security_allowance_type = fields.Selection([('none', _('None')), ('perc', _('Percentage')), ('num', _('Number'))],
                                               _('Security Allowance Type'), default='none')
    security_allowance = fields.Float(_('Security Allowance'))
    security_allowance_temp = fields.Float(_('Security Allowance'), compute='_get_amount')
    communication_allowance_type = fields.Selection(
        [('none', _('None')), ('perc', _('Percentage')), ('num', _('Number'))],
        _('Communication Allowance Type'), default='none')
    communication_allowance = fields.Float(_('Communication Allowance'))
    communication_allowance_temp = fields.Float(_('Communication Allowance'), compute='_get_amount')

    retire_allowance_type = fields.Selection([('none', _('None')), ('perc', _('Percentage')), ('num', _('Number'))],
                                             _('Retire Allowance Type'), default='none')
    retire_allowance = fields.Float(_('Retirement Allowance'))

    infect_allowance_type = fields.Selection([('none', _('None')), ('perc', _('Percentage')), ('num', _('Number'))],
                                             _('Infection Allowance Type'), default='none')
    infect_allowance = fields.Float(_('Infection Allowance'))
    supervision_allowance_type = fields.Selection(
        [('none', _('None')), ('perc', _('Percentage')), ('num', _('Number'))],
        _('Supervision Allowance Type'), default='none')
    supervision_allowance = fields.Float(_('Supervision Allowance'))
    insurance_type = fields.Selection([('none', _('None')), ('perc', _('Percentage')), ('num', _('Number'))],
                                      _('Insurance Type'), default='none')
    insurance = fields.Float(_('Insurance'))
    other_deduction_type = fields.Selection([('none', _('None')), ('perc', _('Percentage')), ('num', _('Number'))],
                                            _('Other Deductions Type'), default='none')
    other_deduction = fields.Float(_('Other Deductions'))
    gosi_deduction = fields.Float(compute="_calculate_gosi", string='Gosi (Employee Percentage)')
    gosi_employer_deduction = fields.Float(compute="_calculate_gosi", string='Gosi (Employer Percentage)')
    total_gosi = fields.Float(compute="_calculate_gosi", string='Total')
    is_gosi_deducted = fields.Selection([('yes', _('Yes')), ('no', _('No'))], default='yes')
    blood_type = fields.Selection(
        [('O-', 'O−'), ('O+', 'O+'), ('A-', 'A−'), ('A+', 'A+'), ('B-', 'B−'), ('B+', 'B+'), ('AB-', 'AB−'),
         ('AB+', 'AB+')], 'Blood Type')

    religion = fields.Selection([('muslim', _('Muslim')), ('christian', _('Christian')), ('other', _('Other'))],
                                _('Religion'))
    gender = fields.Selection([('male', _('Male')), ('female', _('Female'))],
                              _('Gender'))

    birth_place = fields.Char(_('Birth Place'))

    point_of_hire = fields.Char(_('Point of hire'))
    city = fields.Char(_('City Hired From'))
    country = fields.Char(_('Country Hired From'))
    contact_address = fields.Char(_('Contact address'), size=512)

    date_of_birth = fields.Date(_('Date Of Birth'))
    marital = fields.Selection(
        [('single', _('Single')), ('married', _('Married')), ('widower', _('Widower')), ('divorced', _('Divorced'))],
        _('Marital Status'), default='single')
    mobile_no = fields.Char(_('Mobile No'))
    p_o_box_no = fields.Char(_('P. O. Box'))
    zip_code = fields.Char(_('Zip Code'))
    saudi_id_iqama = fields.Char(_('Saudi ID / Identity No.'))
    saudi_id_iqama_date = fields.Date(_('Saudi ID / Identity Issue Date'))
    saudi_id_iqama_expiry = fields.Date(_('Saudi ID / Identity Expiry Date'))
    passport_number = fields.Char(_('Passport number'))
    passport_issue_date = fields.Date(_('Passport Issue Date'))
    passport_expiry_date = fields.Date(_('Passport Expiry Date'))
    passport_issue_place = fields.Char(_('Passport Issue Place'))
    saudi_com_number = fields.Char(_('Saudi Commission Number'))
    saudi_com_date = fields.Date(_('Saudi Commission Issue Date'))
    saudi_com_expiry_date = fields.Date(_('Saudi Commission Expiry Date'))
    bls_date = fields.Date(_('BLS Date'))
    acls_date = fields.Date(_('ACLS Date'))
    insurance_date = fields.Date(_('Insurance Date'))
    specialty = fields.Char(_('Specialty'))
    category = fields.Char(_('Category'))
    effective_from = fields.Date(_('Effective From'))
    to_contact = fields.Text(_('To contact in case of Emergency'))

    emp_type = fields.Selection([('saudi', _('Holiday1')), 
                                 ('other', _('Holiday2')),
                                 ('displaced', _('Holiday3')),
                                 ('external', _('Holiday4')),
                                 ('external2', _('Other'))], _('Annual Leave Entitlement'), tracking=True)
    appraisal = fields.Boolean(_('Appraisal'))
    re_contract = fields.Boolean(_('re contract'))
    contract_draft = fields.Boolean(_('Contract Draft'))
    breakdown_allowance = fields.Float(compute="_cal_allowance", string='Breakdown Allowance')
    car_allowance = fields.Float(_('Car Allowance'))
    ticket_allowance = fields.Float(_('Ticket Allowance'))
    medical_ins_allowance = fields.Float(_('Medical Insurance Allowance'))
    medical_ins_issue_date = fields.Date(_('Medical Insurance Issue Date'))
    medical_ins_exp_date = fields.Date(_('Medical Insurance Expiry Date'))
    join_date = fields.Date(_('Join Date'))
    driving_lic_issue_date = fields.Date(_('Driving License Issue Date'))
    driving_lic_exp_date = fields.Date(_('Driving License Expiry Date'))
    driving_lic_issue_place = fields.Char(_('Driving License Issue Place'))
    dependants_ticket_amount = fields.Float(string='Dependants Ticket Amount', compute='_get_dependants_ticket_amount')
    air_ticket_amount = fields.Float(string='Air Ticket Amount')
    air_ticket_number = fields.Integer(string='Air Ticket No.')
    total_air_ticket_amount = fields.Float(string='Total Air Ticket Amount', compute='_get_total_ticket_amount')
    trial_duration = fields.Float(string='Trail Duration', compute='_compute_contract_duration')
    contract_duration_cal = fields.Float(string='Contract Duration', compute='_compute_contract_duration')

    # Relational fields
    job_id = fields.Many2one(related="employee_id.job_id", readonly=True, tracking=True)
    working_hours = fields.Many2one(related='employee_id.resource_calendar_id')
    analytic_account_id = fields.Many2one(comodel_name='account.analytic.account')
    journal_id = fields.Many2one(comodel_name='account.journal')
    vac_des = fields.Many2one(comodel_name='hr.vacation.dest', string='Vacation Destination')
    employee_dependent_ids = fields.One2many(comodel_name='hr.employee.dependent', inverse_name='contract_id')
    employee_dependant = fields.One2many('hr.employee.dependent', 'contract_id', _('Employee Dependants'))
    children_allowance = fields.One2many('hr.children.allowance', 'contract_id', _('Children Allowance'))
    nationality = fields.Many2one('res.country', related='employee_id.country_id', readonly=True)
    type_id = fields.Many2one(related='employee_id.employee_type_id', string="Contractor Type", tracking=True)
    contractor_type = fields.Many2one(related='employee_id.employee_type_id', string="Contractor Type", required=False, tracking=True, store=True)
    employee_id = fields.Many2one('hr.employee')
    department_id = fields.Many2one('hr.department', _('Department Name'), related='employee_id.department_id',
                                    readonly=True)
    hiring_date = fields.Date(related='employee_id.first_hiring_date', string="Hiring Date", readonly=True)
    all_exper_year = fields.Integer(compute='_compute_all_experience', store=True)
    all_exper_month = fields.Integer(compute='_compute_all_experience', store=True)
    all_exper_day = fields.Integer(compute='_compute_all_experience', store=True)

    previous_contract_id = fields.Many2one('hr.contract', store=True, string='Previous Contract',
                                           help='The Previous Contract Of The Employee')

    #########################  consultant #####################new /:19/10
    consultants = fields.Boolean(default=False)
    consultant_salary = fields.Float(string='Consultant Salary')
    consultant_hour = fields.Float(string='Consultant Hour')
    max_consultant_hour = fields.Float(string='Max Consultant Hour')

    salary_status = fields.Selection([('in', _('IN')), ('out', _('OUT'))],
                                     _('Salary Status'))
    recruited_talent = fields.Selection([('billable', _('Billable')), ('un_billable', _('Un Billable'))],
                                        _('Recruited Talent'))
    class_contract = fields.Selection([('employees', _('Employees')), ('collect_money', _('Collect Money')),
                                                ('endowments', _('Endowments')),('researchers', _('Researchers'))],
                                   _('Classification Contracts'), tracking=True)
    period_ticket = fields.Integer()
    dependant_count = fields.Integer(compute='_get_employee_dependant_count', store=True)

    has_transportation = fields.Boolean(string='Has Transportation?', default=True)
    has_housing = fields.Boolean(string='Has Housing?', default=True)

    check_nationality = fields.Boolean(related='employee_id.check_nationality', store=True, string="Saudi?")

    last_salary_gosi = fields.Float(string='Last Salary Gosi', help='The Last Salary Gosi After The Age 50 Years.')


    def _get_employee_dependant_count(self):
        for rec in self:
            rec.dependant_count = len(
                self.env['hr.employee.dependent'].search([('contract_id', '=', rec.id)]))

    @api.depends('employee_id')
    def _compute_all_experience(self):
        for item in self:
            if item.employee_id:
                item.all_exper_year = item.employee_id.experience_year + item.employee_id.service_year
                item.all_exper_month = item.employee_id.experience_month + item.employee_id.service_month
                item.all_exper_day = item.employee_id.experience_day + item.employee_id.service_day

                if item.all_exper_month > 11:
                    item.all_exper_year = item.all_exper_year + 1
                    item.all_exper_month = item.all_exper_month - 12
                if item.all_exper_day > 30:
                    item.all_exper_month = item.all_exper_month + 1
                    item.all_exper_day = item.all_exper_day - 30

    @api.onchange('contractor_type')
    def onchange_contractor_type(self):
        if self.contractor_type:
            self.type_id = self.contractor_type
            self.consultants = self.contractor_type.consultants
            self.employee_id.employee_type_id = self.contractor_type

    @api.onchange('date_start', 'hiring_date')
    def get_trial_date_field(self):
        for rec in self:
            # rec.trial_date_start = False
            # rec.trial_date_end = False
            if rec.hiring_date and rec.date_start:
                date_start = datetime.datetime.strptime(str(rec.hiring_date), '%Y-%m-%d')
                rec.trial_date_start = rec.hiring_date
                rec.trial_date_end = date_start + relativedelta.relativedelta(months=3)
            elif rec.date_start and not rec.hiring_date:
                date_start = datetime.datetime.strptime(str(rec.date_start), '%Y-%m-%d')
                rec.trial_date_start = rec.date_start
                rec.trial_date_end = date_start + relativedelta.relativedelta(months=3)

    @api.onchange('employee_id')
    def _emp_type_employee(self):
        for item in self:
            previous_contract = self.search([('employee_id', '=', item.employee_id.id),
                                             ('active', '=', True), ], limit=1)
            if previous_contract:
                raise exceptions.Warning(_('Sorry, Can Not Create More than One contract for an Employeet %s') %
                                         item.employee_id.name)

            if item.employee_id:
                #if item.employee_id.check_nationality:
                #    item.emp_type = 'saudi'
                #else:
                #    item.emp_type = 'other'
                if item.employee_id.marital == 'single':
                    item.contract_status = 'single'
                else:
                    item.contract_status = 'marriage'
                item.job_id = item.employee_id.job_id
                item.department_id = item.employee_id.department_id
                item.employee_code = item.employee_id.employee_code
                item.fn = item.employee_id.fn
                item.mn = item.employee_id.mn
                item.ln = item.employee_id.ln
                item.dn = item.employee_id.name

    '''@api.onchange('emp_type')
    def chick_saudi_percentage(self):
        for item in self:
            Saudization_percen = item.env.user.company_id.saudi_percentage
            if Saudization_percen > 0:
                saudi = len(item.search([('active', '=', True), ('emp_type', 'in', ('saudi', 'displaced')),
                                         ('state', '=', 'program_directory')]).ids)
                all_emp = len(item.search([('active', '=', True), ('state', '!=', 'end_contract')]).ids) + 1
                saudi_percen = (saudi / all_emp) * 100
                if saudi_percen > Saudization_percen and item.emp_type in ('saudi', 'displaced'):
                    raise exceptions.Warning(
                        _('The Saudization percentage should not exceed  Percentage %s') % Saudization_percen)

                none_saudi = len(item.search(
                    [('active', '=', True), ('emp_type', '=', 'other'), ('state', '=', 'program_directory')]).ids)
                none_Saudization_percen = (100 - Saudization_percen)
                none_percen = (none_saudi / all_emp) * 100
                if none_percen > none_Saudization_percen and item.emp_type == 'other':
                    raise exceptions.Warning(
                        _('The None Saudization percentage should not exceed Percentage %s') % none_Saudization_percen)'''

    def change_current_date_hijri(self, date):
        date = datetime.datetime.strptime(str(date), '%Y-%m-%d')
        year = date.year
        day = date.day
        month = date.month
        hijri_date = convert.Gregorian(year, month, day).to_hijri()
        return hijri_date

    def translate_to_eng(self, text):
        if text:
            eng_text = text
            ln = translator.detect(text)
            if ln.lang != 'en':
                eng_text = translator.translate(text, dest='en')
            return eng_text
        else:
            return ' '

    ###############>>send email end contract and trial peroid<<<##########
    @api.model
    def contract_mail_reminder(self):
        now = dt.now() + timedelta(days=1)
        date_now = now.date()
        match = self.search([('state', '!=', 'end_contract'),
                             ('contract_duration', 'not in',( '3_months','6_months'))])
        # trial_days_send_email=5
        cont_end_reminder = self.env.user.company_id.contract_end_reminder
        cont_trial_reminder = self.env.user.company_id.contract_trial_reminder
        for i in match:
            if i.date_end:
                exp_date = fields.Date.from_string(i.date_end) - timedelta(days=cont_end_reminder)
                if date_now >= exp_date:
                   self.env.ref('hr_contract_custom.email_template_contract_period_expiration_reminder', False).send_mail(i.id)

            if i.trial_date_end:
                exp_date = fields.Date.from_string(i.trial_date_end)
                exp_date1 = fields.Date.from_string(i.trial_date_end) - timedelta(days=cont_trial_reminder)
                # if date_now >= exp_date :
                if exp_date >= date_now and date_now >= exp_date1:
                   self.env.ref('hr_contract_custom.email_template_contract_trial_period_expiration_reminder', False).send_mail(i.id)

    ##########################################################################
    @api.onchange('contract_duration', 'date_start')
    def get_contract_end_date(self):
        if self.date_start and self.contract_description == 'locum':

            date_start = datetime.datetime.strptime(str(self.date_start), '%Y-%m-%d')

            if self.contract_duration == '3_months':
                self.date_end = date_start + relativedelta.relativedelta(months=3) - timedelta(days=1)
            elif self.contract_duration == '6_months':
                self.date_end = date_start + relativedelta.relativedelta(months=6) - timedelta(days=1)
            elif self.contract_duration == '9_months':
                self.date_end = date_start + relativedelta.relativedelta(months=9) - timedelta(days=1)
            elif self.contract_duration == '12_months':
                self.date_end = date_start + relativedelta.relativedelta(months=12) - timedelta(days=1)
            elif self.contract_duration == '24_months':
                self.date_end = date_start + relativedelta.relativedelta(months=24) - timedelta(days=1)
            elif self.contract_duration == '36_months':
                self.date_end = date_start + relativedelta.relativedelta(months=36) - timedelta(days=1)
            else:
                self.date_end = False

    # get salary amount form salary degree
    @api.onchange('salary_degree')
    def onchange_salary_degree(self):
        if self.salary_degree:
            self.salary = self.salary_degree.base_salary

    # Get Salary Insurnce from Salary amount
    @api.onchange('salary')
    def onchange_base_salary_insurance(self):
        if self.salary:
            self.salary_insurnce = self.salary

    # update  to control on date constrains
    @api.onchange('trial_date_start', 'trial_date_end', 'date_start', 'date_end')
    def onchange_dates(self):
        if self.trial_date_start:
            if self.trial_date_end:
                if self.date_start:
                    if self.date_end:
                        start_date_1 = dt.strptime(str(self.date_start), "%Y-%m-%d")
                        end_date_1 = dt.strptime(str(self.date_end), "%Y-%m-%d")
                        trial_start_date_1 = dt.strptime(str(self.trial_date_start), "%Y-%m-%d")
                        trial_end_date_1 = dt.strptime(str(self.trial_date_end), "%Y-%m-%d")

                        if trial_end_date_1 < trial_start_date_1:
                            raise exceptions.Warning(_('trial End Date  must be greater than Trial Start date'))
                        if end_date_1 < start_date_1:
                            raise exceptions.Warning(_('End  date must be greater than Start date'))

    @api.onchange('contract_description')
    def _contract_duration_change_state(self):
        if self.contract_description == 'permanent':
            self.contract_duration = 'none'
            self.date_end = ''

    @api.depends('wage', 'house_allowance', 'transport_allowance', 'communication_allowance')
    def _compute_monthly_salary(self):
        for rec in self:
            rec.monthly_salary = rec.wage + rec.house_allowance_temp + rec.transport_allowance_temp + \
                              rec.communication_allowance_temp + rec.field_allowance_temp + \
                              rec.special_allowance_temp + rec.other_allowance_temp

    @api.depends()
    def _cal_allowance(self):
        allowance = 0.0
        if self.employee_id.country_id.code == 'SA':
            allowance = self.salary * 1 / 100
        self.breakdown_allowance = allowance

    @api.depends()
    def _calculate_gosi(self):
        saudi_gosi = self.env.user.company_id.saudi_gosi
        company_gosi = self.env.user.company_id.company_gosi
        none_saudi_gosi = self.env.user.company_id.none_saudi_gosi

        max_saudi_gosi = self.env.user.company_id.max_amount_saudi_gosi
        max_company_gosi = self.env.user.company_id.max_amount_company_gosi

        Sanad_saudi_gosi = self.env.user.company_id.Sanad_saudi_gosi
        Sanad_company_gosi = self.env.user.company_id.Sanad_company_gosi

        for record in self:
            #if (record.emp_type == 'saudi' or record.emp_type == 'displaced') and record.is_gosi_deducted == "yes":
            record.employee_id._compute_employee_age()
            sanad_age = record.salary_scale.retirement_age
            emp_age = record.employee_id.employee_age

            if record.check_nationality==True and record.is_gosi_deducted == "yes":
                if emp_age >= sanad_age and sanad_age > 0 :
                   employee_gosi = (record.salary_insurnce + record.house_allowance_temp) * (saudi_gosi - Sanad_saudi_gosi) / 100
                   employer_gosi = (record.salary_insurnce + record.house_allowance_temp) * (company_gosi - Sanad_company_gosi)/ 100
                else:
                   employee_gosi = (record.salary_insurnce + record.house_allowance_temp) * saudi_gosi / 100
                   employer_gosi = (record.salary_insurnce + record.house_allowance_temp) * company_gosi / 100

                if employee_gosi <= max_saudi_gosi:
                   record.gosi_deduction = employee_gosi
                else:
                   record.gosi_deduction = max_saudi_gosi
                if employer_gosi <= max_company_gosi:
                   record.gosi_employer_deduction = employer_gosi
                else:
                   record.gosi_employer_deduction = max_company_gosi
                record.total_gosi = record.gosi_deduction + record.gosi_employer_deduction

            #elif (record.emp_type == 'saudi' or record.emp_type == 'displaced') and record.is_gosi_deducted == "no":
            elif record.check_nationality==True and record.is_gosi_deducted == "no":
                if emp_age >= sanad_age and sanad_age > 0 :
                   employee_gosi = (record.salary_insurnce + record.house_allowance_temp) * (saudi_gosi - Sanad_saudi_gosi) / 100
                   employer_gosi = (record.salary_insurnce + record.house_allowance_temp) * (company_gosi - Sanad_company_gosi) / 100
                else:
                   employee_gosi = (record.salary_insurnce + record.house_allowance_temp) * saudi_gosi / 100
                   employer_gosi = (record.salary_insurnce + record.house_allowance_temp) * company_gosi / 100

                if employee_gosi <= max_saudi_gosi:
                   employee_gosi = employee_gosi
                else:
                   employee_gosi = max_saudi_gosi
                if employer_gosi <= max_company_gosi:
                   employer_gosi = employer_gosi
                else:
                   employer_gosi = max_company_gosi

                record.gosi_deduction = 0.0
                record.gosi_employer_deduction = employee_gosi + employer_gosi
                record.total_gosi = employee_gosi + employer_gosi

            else:
                # pass
                employer_gosi = (record.salary_insurnce + record.house_allowance_temp) * none_saudi_gosi / 100

                record.gosi_deduction = 0.0
                record.gosi_employer_deduction = employer_gosi
                record.total_gosi = employer_gosi

            #if (record.emp_type == 'saudi' or record.emp_type == 'displaced') and record.saudi_emp_type == 'saudi-non':
            if record.check_nationality==True and record.saudi_emp_type == 'saudi-non':
                record.gosi_deduction = 0.0
                record.gosi_employer_deduction = 0.0
                record.total_gosi = 0.0

    @api.depends('date_start', 'date_end', 'trial_date_start', 'trial_date_end')
    def _compute_contract_duration(self):
        for item in self:
            item.contract_duration_cal = 0
            item.trial_duration = 0
            if item.date_start and item.date_end:
                date_start = datetime.datetime.strptime(str(item.date_start), '%Y-%m-%d').date()
                date_end = datetime.datetime.strptime(str(item.date_end), '%Y-%m-%d').date()
                item.contract_duration_cal = relativedelta.relativedelta(date_end, date_start).years

            if item.trial_date_start and item.trial_date_end:
                date_start = datetime.datetime.strptime(str(item.trial_date_start), '%Y-%m-%d').date()
                date_end = datetime.datetime.strptime(str(item.trial_date_end), '%Y-%m-%d').date()
                item.trial_duration = relativedelta.relativedelta(date_end, date_start).months
                if item.trial_duration > 6:
                    raise exceptions.Warning(_('The period of trail duration must be not more than 6 months'))

    '''@api.onchange('date_start')
    def _compute_trial_period(self):
        if self.date_start and self.date_end:
            date_start = datetime.datetime.strptime(str(self.date_start), '%Y-%m-%d').date()
            self.trial_date_start = self.date_start
            self.trial_date_end = date_start + relativedelta.relativedelta(months=3) - timedelta(days=1)'''

    @api.depends('air_ticket_amount')
    def _get_total_ticket_amount(self):
        self.total_air_ticket_amount = self.air_ticket_amount * self.air_ticket_number

    @api.onchange('employee_id')
    def _onchange_employee_id(self):
        if self.employee_id:
            self.job_id = self.employee_id.job_id
            self.department_id = self.employee_id.department_id
            self.employee_code = self.employee_id.employee_code
            self.fn = self.employee_id.fn
            self.mn = self.employee_id.mn
            self.ln = self.employee_id.ln
            self.dn = self.employee_id.name

    @api.model
    def create(self, vals):
        contracts = super(Contract, self).create(vals)
        contracts.employee_id.contract_id = contracts.id
        return contracts

    def draft_state(self):
        self.state = "draft"

    def employeed_aproval(self):
        #self.chick_saudi_percentage()
        self.state = "employeed_aproval"

    def hr_head_approval(self):
        #self.chick_saudi_percentage()
        self.state = "hr_head_approval"

    def end_contract_state(self):
        if self.date_end == False:
            raise exceptions.Warning(_('The contract End Date Must Be Entered'))
        else:
            self.state = "end_contract"

    def program_directory(self):
        #self.chick_saudi_percentage()
        self.state = "program_directory"

    def unlink(self):
        for i in self:
            if i.state != 'draft':
                raise exceptions.Warning(_('You can not delete record in state not in draft'))
            # if i.hiring_date:
            # raise exceptions.Warning(_('You can not delete record has Hiring date'))
        return super(Contract, self).unlink()

    @api.onchange('working_hours')
    def _onchange_working_hours(self):
        if self.employee_id.contract_id.id == self._origin.id:
            self.env['resource.resource'].browse([self.employee_id.resource_id.id]).write(
                {'calendar_id': self.working_hours.id})


class VacationDest(models.Model):
    _name = 'hr.vacation.dest'

    _rec_name = 'name'
    name = fields.Char(required=True)


class EmployeeChildAllowance(models.Model):
    _name = 'hr.children.allowance'

    name = fields.Char(_('Children Name'))
    age = fields.Integer(_('Age'))
    fees = fields.Float(_('Educational Fees'))
    remarks = fields.Text(_('Remarks'))

    # Relational fields
    contract_id = fields.Many2one('hr.contract', _('Contract'))


class ContractType(models.Model):
    _name = "hr.contract.type"
    _description = "Contract Type"
    _order = "sequence, id"

    name = fields.Char(string="Contract Type", required=True)
    sequence = fields.Integer(help="Gives the sequence when displaying a list of Contract.", default=10)
    salary_type = fields.Selection([("amount", _("Amount")), ("scale", _("Scale"))], string="Salary Type")
    code = fields.Char(string='Code')
    consultants = fields.Boolean(default=False, string='Consultants')

    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)

