# -*- coding: utf-8 -*-
from datetime import datetime, timedelta, date
from dateutil import relativedelta
from hijri_converter import convert
from num2words import num2words
from odoo import api, exceptions, fields, models, _
from odoo.exceptions import ValidationError, Warning
from odoo.tools.translate import _

class HrEmployeePublic(models.Model):
    _inherit = 'hr.employee.public'

    #name = fields.Char(related="user_id.employee_id.name")

    coach_id = fields.Many2one('hr.employee.public', 'Department Manager', readonly=True)

    current_leave_id = fields.Many2one('hr.holidays.status', related="user_id.employee_id.current_leave_id",
                                       string="Current Leave Type")
    current_leave_state = fields.Selection(related="user_id.employee_id.current_leave_state", string="Current Leave Status")

    leave_date_from = fields.Date('From Date', related="user_id.employee_id.leave_date_from")
    leave_date_to = fields.Date('To Date', related="user_id.employee_id.leave_date_to")


# Hr_Employee
class HrEmployee(models.Model):
    _inherit = "hr.employee"
    _order = 'id'

    # iqama fields in employee view
    identity_number = fields.Char(compute_sudo=True, compute='_compute_identity_number', string='Identity Number',store=True)
    iqama_creat_date = fields.Date(related="iqama_number.issue_date", readonly=True,string="Iqama Issue Date")
    iqama_expiy_date = fields.Date(related="iqama_number.expiry_date", readonly=True)
    iqama_job = fields.Many2one(related="iqama_number.job_id", readonly=True)
    emp_iqama_job = fields.Char(related="iqama_number.emp_iqama_job", readonly=True)
    name_as_pass = fields.Char("Name(As in Passport)")
    employee_code = fields.Char()
    arabic_name = fields.Char()
    work_fax = fields.Char("Work Fax")
    serial_num = fields.Char("Serial No.")
    grade = fields.Char()
    is_head = fields.Boolean("Is Head  of Function")
    is_line_man = fields.Boolean("Is Line Manager")

    is_calender = fields.Boolean(default=False)
    spouse_no = fields.Char("Spouse Phone No.")
    joining_date = fields.Date("Job Joining Date")
    leaving_date = fields.Date(tracking=True)
    serv_year = fields.Char("Total Service Year", store=True, readonly=True)
    vendor_no = fields.Char("Vendor No")
    mol_no = fields.Char("MOL No")
    # iban = fields.Char("IBAN")
    bank_account_id = fields.Many2one("res.partner.bank", "Bank Account Number",
                                      domain="[('partner_id', '=', address_home_id)]",
                                      help="Employee bank salary account", groups="base.group_user")
    bank_code = fields.Char("Bank Name", related="bank_account_id.bank_id.name")
    issue = fields.Date("Issue Date")
    expiry = fields.Date("Expiry Date")
    # passport fields to private information page
    date_issuance_passport = fields.Date(related="passport_id.issue_date", readonly=True,string="Passport Issue Date")
    expiration_date_passport = fields.Date(related="passport_id.expiry_date", readonly=True,string="Passport Expiry Date")
    place_issuance_passport = fields.Char(related="passport_id.place_issue_id", readonly=True)

    # related fields if employee is saudi
    date_issuance_saudi_id = fields.Date(related="saudi_number.issue_date",string="Saudi Issue Date",  readonly=True)
    expiration_date_saudi_id = fields.Date(related="saudi_number.expiry_date")
    place_issuance_saudi_id = fields.Char(related="saudi_number.place_issue_id", readonly=True)

    own_license = fields.Boolean()
    from_chart = fields.Boolean(string="From Chart")

    depend = fields.Boolean("Have Dependent")
    fn = fields.Char("First Name")
    mn = fields.Char("Middle Name")
    ln = fields.Char("Last Name")
    bg = fields.Char("Blood Group")
    a_email = fields.Char("Alternate Email ID")
    airport = fields.Char("Nearest Airport")

    first_hiring_date = fields.Date(string="First Hiring Date")
    # duration_in_months = fields.Float(compute_sudo=True, compute='_get_months_no')
    contact_no = fields.Char("Contact No")
    reason = fields.Char(string="Reason")
    r_name = fields.Char("Name")

    # fields of page work information in employees view
    emp_no = fields.Char(string="Employee number", tracking=True)
    english_name = fields.Char(string="English Name")
    home_no = fields.Char()
    present_address = fields.Char()
    work_location = fields.Char(string="Work Location")
    working_location = fields.Many2one('work.location', string="Work Location")
    #department = fields.Many2one(comodel_name='hr.department')
    direct_emp = fields.Selection(selection=[("yes", "direct employee"), ("no", "not direct employee")], default="yes")
    is_marketer = fields.Boolean(string="marketer?")
    finger_print = fields.Boolean()
    payment_method = fields.Selection(selection=[("cash", "cash"), ("bank", "bank")], default="cash")
    # fields of page private information in notebook in employees view
    religion = fields.Selection(selection=[("muslim", "Muslim"), ("christian", "Christian"), ("other", "Other")])
    blood_type = fields.Selection([
        ("o-", "O-"),
        ("o+", "O+"),
        ("A-", "A-"),
        ("A+", "A+"),
        ("B-", "B-"),
        ("B+", "B+"),
        ("AB-", "AB-"),
        ("AB+", "AB+")])
    employee_from = fields.Selection(selection=[("citizen", "Citizen"), ("other", "Other")], default="citizen")
    entry_date_ksa = fields.Date(attrs="{'invisible':[('employee_from','=','citizen)]'}")
    visa_number = fields.Char()
    number_child = fields.Integer()
    place_birth = fields.Char()
    state = fields.Selection(selection=[("draft", _("Draft")), ("complete", _("Complete Data")),
                                        ('open', _('In Service')),("under_out_of_service", _("Under Out of service")),
                                        ("out_of_service", _("Out of service"))],
                             default="draft", tracking=True)
    # fields of hr settings page in notebook
    vihcle = fields.Char()
    vihcle_distance = fields.Integer()
    attendance = fields.Selection(selection=[("present", "Present"), ("Apsent", "Apsent")], default="present")
    active = fields.Boolean(default=True)
    # Employee_type = fields.Many2one('hr.contract.type', string="Employee Type", default=lambda self: self.env['hr.contract.type'].search([], limit=1),store=True, store=True)

    medical_exam_check = fields.Boolean()
    is_cordinator = fields.Boolean()
    is_revisor = fields.Boolean()
    is_evaluation_manager = fields.Boolean()
    evaluator_membership_no = fields.Char()

    # Fields of iqama and health
    medical_insuranc = fields.Boolean(tracking=True)
    medical_class = fields.Selection(
        selection=[("vip", "vip"), ("a", "A"), ("b", "B"), ("c_senior", "C senior")]
    )
    medical_membership_no = fields.Char()
    medical_membership_exp = fields.Date()
    medical_exam_file = fields.Binary()
    filename = fields.Char()

    # Relational fields
    address_home_id = fields.Many2one("res.partner", "Private Address", help="", groups="hr.group_hr_user")
    # private partner
    # sick leaves page
    saudi_number = fields.Many2one("hr.employee.document", domain=[("document_type", "=", "saudi")], tracking=True)
    # passport_id = fields.Many2one('hr.employee.document', domain=[('document_type', '=', 'passport')],
    #                               tracking=True)
    p_state_id = fields.Many2one(comodel_name="res.country.state", string="Fed. State")
    r_manager = fields.Many2one(comodel_name="hr.employee", string="Reporting Manager")
    dependent_id = fields.One2many("hr.dependent", "dependent_relation", string="Dependent")
    qualifiction_id = fields.One2many("hr.qualification", "qualification_relation_name", string="Qualifications")
    certification_id = fields.One2many("hr.certification", "certification_relation", string="Certification")
    insurance_id = fields.One2many("hr.insurance", "insurance_relation", string="Insurance")
    trainings_id = fields.One2many("hr.trainings", "employee_id", string="Trainings")
    #other_asset = fields.Many2many("maintenance.equipment", string="Other Assets")
    project = fields.Many2one(comodel_name="projects.projects")
    employment_history_ids = fields.One2many(comodel_name="hr.employee.history", inverse_name="employement_history")
    attachment_ids = fields.One2many('emplpyee.attachment', 'employee_attaches_id', string="Employee Attachments")
    head = fields.Many2one(comodel_name="hr.employee", string="Head of Function")
    line_man = fields.Many2one(comodel_name="hr.employee", string="Line Manager")
    performence_manager = fields.Many2one(comodel_name="hr.employee", string="Performance Manager")
    office = fields.Many2one(comodel_name="office.office")
    iqama_number = fields.Many2one(comodel_name="hr.employee.document", domain=[("document_type", "=", "Iqama")],
                                   tracking=True,string="Identity")

    country_id = fields.Many2one("res.country", "Nationality (Country)", groups="base.group_user")
    gender = fields.Selection([("male", "Male"), ("female", "Female")],
                              groups="base.group_user", default="male")
    marital = fields.Selection([("single", "Single"), ("married", "Married"),
                                ("widower", "Widower"), ("divorced", "Divorced")],
                               string="Marital Status", groups="base.group_user", default="single", tracking=True)

    base_salary = fields.Float(compute_sudo=True, compute='compute_base_salary')
    salary_in_words = fields.Char(compute_sudo=True, compute='get_salary_amount')
    payslip_lines = fields.One2many(comodel_name='hr.payslip.line', compute_sudo=True, compute='compute_base_salary')
    check_nationality = fields.Boolean(compute_sudo=True, compute="_check_nationality_type")
    # National address
    address_city = fields.Many2one("address.city")
    address_region = fields.Many2one("address.region")
    street = fields.Char()
    building_number = fields.Char()
    postal_code = fields.Char()
    extra_number = fields.Char()
    property_type = fields.Char()
    drug_type = fields.Selection([('company_property', 'Company Property'), ('property', 'Employee Property'),
                                  ('rent', 'Rent')], default="rent")
    apartment_number = fields.Char()
    service_year = fields.Integer(compute_sudo=True, compute='_compute_service_duration')
    service_month = fields.Integer(compute_sudo=True, compute='_compute_service_duration')
    service_day = fields.Integer(compute_sudo=True, compute='_compute_service_duration')
    experience_year = fields.Integer(compute_sudo=True, compute='_compute_duration_experience')
    experience_month = fields.Integer(compute_sudo=True, compute='_compute_duration_experience')
    experience_day = fields.Integer(compute_sudo=True, compute='_compute_duration_experience')
    relationship = fields.Char(string="Relationship")
    employee_age = fields.Integer(string="Age", compute_sudo=True, compute='_compute_employee_age', store=True)

    personal_email = fields.Char('Personal Email')

    country_address_id = fields.Many2one("res.country", string="Country")
    contract_id = fields.Many2one('hr.contract', string='Current Contract',
                                  groups="base.group_user",
                                  domain="[('company_id', '=', company_id)]",
                                  help='Current contract of the employee')
    phone_ext = fields.Char(string="Extension Phone")
    first_contract_date = fields.Date(compute_sudo=True, compute='_compute_first_contract_date', groups="base.group_user")

    contract_warning = fields.Boolean(string='Contract Warning', store=True, compute_sudo=True, compute='_compute_contract_warning',
                                      groups="base.group_user")

    barcode = fields.Char(string="Badge ID", help="ID used for employee identification.", groups="base.group_user",
                          copy=False)
    birthday = fields.Date('Date of Birth', groups="base.group_user", tracking=True)
    place_of_birth = fields.Char('Place of Birth', groups="base.group_user", tracking=True)
    address_home_id = fields.Many2one(
        'res.partner', 'Address',
        help='Enter here the private address of the employee, not the one linked to your company.',
        groups="base.group_user", tracking=True,
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")
    visa_no = fields.Char('Visa No', groups="base.group_user", tracking=True)
    study_school = fields.Char("School", groups="base.group_user", tracking=True)
    visa_expire = fields.Date('Visa Expire Date', groups="base.group_user", tracking=True)
    country_of_birth = fields.Many2one('res.country', string="Country of Birth", groups="base.group_user",
                                       tracking=True)
    spouse_birthdate = fields.Date(string="Spouse Birthdate", groups="base.group_user", tracking=True)
    identification_id = fields.Char(string='Identification No', groups="base.group_user", tracking=True)
    km_home_work = fields.Integer(string="Home-Work Distance", groups="base.group_user", tracking=True)
    permit_no = fields.Char('Work Permit No', groups="base.group_user", tracking=True)
    pin = fields.Char(string="PIN", groups="base.group_user", copy=False,
                      help="PIN used to Check In/Out in Kiosk Mode (if enabled in Configuration).")
    place_of_birth = fields.Char('Place of Birth', groups="base.group_user", tracking=True)
    spouse_complete_name = fields.Char(string="Spouse Complete Name", groups="base.group_user", tracking=True)
    emergency_contact = fields.Char("Emergency Contact", groups="base.group_user", tracking=True)
    emergency_phone = fields.Char("Emergency Phone", groups="base.group_user", tracking=True)
    phone = fields.Char(related='address_home_id.phone', related_sudo=False, readonly=False, string="Private Phone",
                        groups="base.group_user")
    study_field = fields.Char("Field of Study", groups="base.group_user", tracking=True)
    certificate = fields.Selection([
        ('graduate', 'Graduate'),
        ('bachelor', 'Bachelor'),
        ('master', 'Master'),
        ('doctor', 'Doctor'),
        ('other', 'Other'),
    ], 'Certificate Level', default='other', groups="base.group_user", tracking=True)
    children = fields.Integer(string='Number of Children', groups="base.group_user", tracking=True)
    branch_name = fields.Many2one(related='department_id.branch_name', store=True, string="Branch Name")

    insurance_date = fields.Date(string="Insurance Date")
    new_insurance = fields.Boolean(string="New Insurance", 
                    help='New participants who have no prior periods of contribution under the GOSI.')
    insurance_years = fields.Integer(string="Insurance Years", compute='_compute_insurance_years', store=True)

    @api.depends('insurance_date')
    def _compute_insurance_years(self):
        for emp in self:
            years = 0
            if emp.insurance_date:
                insurance_date = datetime.strptime(str(emp.insurance_date), '%Y-%m-%d')
                today = date.today()
                years = today.year - insurance_date.year - ((today.month, today.day) < (insurance_date.month, insurance_date.day))
            emp.sudo().insurance_years = years

    '''employee_cars_count = fields.Integer(compute_sudo=True, compute="_compute_employee_cars_count", string="Cars",
                                         groups="base.group_user")

    def _compute_employee_cars_count(self):
        driver_ids = (self.mapped('user_id.partner_id') | self.sudo().mapped('address_home_id')).ids
        fleet_data = self.env['fleet.vehicle.assignation.log'].read_group(
            domain=[('driver_id', 'in', driver_ids)], fields=['vehicle_id:array_agg'], groupby=['driver_id'])
        mapped_data = {
            group['driver_id'][0]: len(set(group['vehicle_id']))
            for group in fleet_data
        }
        for employee in self:
            drivers = employee.user_id.partner_id | employee.sudo().address_home_id
            employee.employee_cars_count = sum(mapped_data.get(pid, 0) for pid in drivers.ids)'''

    '''@api.onchange('emp_no')
    def onchang_barcode(self):
        self.barcode = self.emp_no'''

    #override search method
    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        if operator not in ('ilike', 'like', '=', '=like', '=ilike') or not name:
            return super(HrEmployee, self).name_search(name, args, operator, limit)
        args = args or []
        # add emp no in search
        domain = ['|',('emp_no', operator, name),('name', operator, name)]
        recs = self.search(domain + args, limit=limit)
        return recs.name_get()


    @api.depends('saudi_number','iqama_number','check_nationality')
    def _compute_identity_number(self):
        for rec in self:
           if rec.check_nationality == True:
              rec.identity_number = rec.saudi_number.saudi_id
           else:
              rec.identity_number = rec.iqama_number.iqama_id

    @api.depends('birthday')
    def _compute_employee_age(self):
        for emp in self:
            age = 0
            if emp.birthday:
                dob = datetime.strptime(str(emp.birthday), '%Y-%m-%d')
                today = date.today()
                age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
            emp.sudo().employee_age = age

    # @api.constrains('parent_id')
    # def _check_parent_id(self):
    #     for employee in self:
    #         if not employee._check_recursion():
    #             parent_id = employee.sudo().department_id.parent_id.manager_id
    #             if parent_id:
    #                employee.parent_id = parent_id
    #             else:
    #                employee.parent_id = False
    #
    # @api.constrains('coach_id')
    # def _check_coach_id(self):
    #     for employee in self:
    #         if not employee._check_recursion():
    #             parent_id = employee.sudo().department_id.parent_id.manager_id
    #             if parent_id:
    #                employee.parent_id = parent_id
    #             else:
    #                employee.coach_id = False

    @api.onchange('department_id')
    def _onchange_department(self):
        # self.sudo().parent_id = self.sudo().department_id.manager_id
        # self.sudo().coach_id = self.sudo().department_id.parent_id.manager_id
        for emp in self:
            dept = emp.department_id
            manager = dept.manager_id
            if manager == emp:
                cur = dept.parent_id
                while cur:
                    if cur.manager_id and cur.manager_id != emp:
                        manager = cur.manager_id
                        break
                    cur = cur.parent_id
                else:
                    manager = emp

            emp.sudo().parent_id = manager or False

            coach = False
            cur = dept.parent_id
            while cur:
                # if cur.manager_id:
                if cur.manager_id and cur.manager_id not in (emp):
                    coach = cur.manager_id
                    break
                cur = cur.parent_id

            # emp.coach_id = coach or dept.manager_id or False
            if not coach and dept.manager_id not in (emp):
                coach = dept.manager_id

            emp.sudo().coach_id = coach or False

    # to Calculate duration service Period
    @api.onchange('first_hiring_date', 'leaving_date')
    def _compute_service_duration(self):
        for rec in self:
            rec._compute_employee_age()
            rec._compute_insurance_years()
            rec.service_year = 0
            rec.service_month = 0
            rec.service_day = 0
            if rec.first_hiring_date:
                if rec.leaving_date:
                    # date_start = datetime.strptime(rec.first_hiring_date, '%Y-%m-%d').date()
                    # date_end = datetime.strptime(rec.leaving_date, '%Y-%m-%d').date()
                    date_start = rec.first_hiring_date
                    date_end = rec.leaving_date
                    rec.service_year = relativedelta.relativedelta(date_end, date_start).years
                    rec.service_month = relativedelta.relativedelta(date_end, date_start).months
                    rec.service_day = relativedelta.relativedelta(date_end, date_start).days

                elif not rec.leaving_date:
                    # start_date_1 = datetime.strptime(rec.first_hiring_date, "%Y-%m-%d").date()
                    start_date_1 = rec.first_hiring_date
                    end_date_1 = datetime.now().date()
                    if start_date_1:
                        rec.service_year = relativedelta.relativedelta(end_date_1, start_date_1).years
                        rec.service_month = relativedelta.relativedelta(end_date_1, start_date_1).months
                        rec.service_day = relativedelta.relativedelta(end_date_1, start_date_1).days

    # to Calculate duration experience Period
    @api.depends('employment_history_ids')
    def _compute_duration_experience(self):
        for item in self:
            item.experience_year = 0
            item.experience_month = 0
            item.experience_day = 0
            if item.employment_history_ids:
                for rec in item.employment_history_ids:
                    if rec.date_from and rec.date_to:
                        # date_start = datetime.strptime(rec.date_from, '%Y-%m-%d').date()
                        # date_end = datetime.strptime(rec.date_to, '%Y-%m-%d').date() + timedelta(days=1)
                        date_start = rec.date_from
                        date_end = rec.date_to + timedelta(days=1)

                        item.experience_year += relativedelta.relativedelta(date_end, date_start).years
                        item.experience_month += relativedelta.relativedelta(date_end, date_start).months
                        item.experience_day += relativedelta.relativedelta(date_end, date_start).days

                        if item.experience_month > 11:
                            item.experience_year = item.experience_year + 1
                            item.experience_month = item.experience_month - 12

                        if item.experience_day > 30:
                            item.experience_month = item.experience_month + 1
                            item.experience_day = item.experience_day - 30

    # @api.onchange('employee_type_id')
    # def onchang_emp_no(self):
    #     for rec in self:
    #         seq = rec.env['ir.sequence'].next_by_code('hr.employee') or '/'
    #         emp_seq = self.env['hr.employee'].search([])
    #         heights = []
    #         new_swq = False
    #         currnt_sequance = rec.env['ir.sequence'].search([('code', '=', 'hr.employee')], limit=1)
    #         if emp_seq and not rec.emp_no:
    #             for emp in emp_seq:
    #                 if emp.emp_no:
    #                     currnt_code = emp.employee_type_id.code
    #                     i = 0
    #                     fix_code = 0
    #                     size_seq = currnt_sequance.padding
    #                     for c in emp.emp_no:
    #                         i += 1
    #                         first_chars = emp.emp_no[0:i]
    #                         if currnt_code == first_chars:
    #                             fix_code = emp.emp_no[i:i + size_seq]
    #
    #                     heights.append(int(fix_code))
    #                     max_number = max(heights)
    #                     if fix_code:
    #                         if int(seq) > max_number + 1 or int(seq) < max_number:
    #                             new_swq = max_number + 1
    #                             rec.emp_no = str(rec.employee_type_id.code) + str(new_swq).zfill(size_seq)
    #                         else:
    #                             new_swq = seq
    #                             rec.emp_no = str(rec.employee_type_id.code) + str(seq)
    #             currnt_sequance.write({'number_next_actual': new_swq})
    #         if not emp_seq or new_swq == False:
    #             rec.emp_no = str(rec.employee_type_id.code) + str(seq)

    '''def write(self, vals):
        for rec in self:
            currnt_sequance = rec.env['ir.sequence'].search([('code', '=', 'hr.employee')], limit=1)
            size_seq = currnt_sequance.padding
            code = rec.emp_no
            currnt_code = rec.employee_type_id.code
            currnt_employee_type_id = rec.employee_type_id.id
            i = 0
            fix_code = 0
            if code:
                for c in code:
                    i += 1
                    first_chars = code[0:i]
                    if currnt_code == first_chars:
                        fix_code = code[i:i + size_seq]
            super(HrEmployee, rec).write(vals)
            if 'context' in dir(self.env) and ('name' in vals or 'english_name' in vals):
                if not rec.english_name: return True
                rec.translate_employee_name()

            if ('employee_type_id' in vals):
                value = vals['employee_type_id']
                if currnt_employee_type_id != value:
                    if rec.employee_type_id:
                        if not rec.emp_no:
                            seq = rec.env['ir.sequence'].next_by_code('hr.employee') or '/'
                            rec.emp_no = str(rec.employee_type_id.code) + str(seq)
                        else:
                            rec.emp_no = str(rec.employee_type_id.code) + str(fix_code)'''

    # get address_home_id field from user_id partner and email
    @api.onchange('user_id','work_email','name')
    def _get_address_home_id(self):
        for item in self:
            if item.user_id:
               item.address_home_id = item.user_id.partner_id.id
               ''' reset email in related partner user '''
               item.user_id.write({'name': item.name})
               if item.work_email:
                  item.user_id.partner_id.write({'email': item.work_email, 'employee': True})

    @api.depends("country_id")
    def _check_nationality_type(self):
        for item in self:
            if item.country_id.code == "SA":
                item.check_nationality = True
            else:
                item.check_nationality = False

    def translate_employee_name(self):
        ir_trans = self.env["ir.translation"]
        cur_lang = self.env.context.get("lang", False)
        langs = [l[0] for l in ir_trans._get_languages()]

        for lang in langs:
            tname = ir_trans.search(
                [
                    ("res_id", "=", self.id),
                    ("lang", "=", lang),
                    ("type", "=", "model"),
                    ("name", "=", "hr.employee,name"),
                ]
            )
            if tname:
                if lang == cur_lang:
                    tname[0].value = self.name
                elif self.english_name and lang.startswith("en_"):
                    tname[0].value = self.english_name
            else:
                if lang == cur_lang:
                    value = self.name
                else:
                    if lang.startswith("en_"):
                        value = self.english_name
                    else:
                        value = self.name
                ir_trans.create(
                    {
                        "lang": lang,
                        "type": "model",
                        "name": "hr.employee,name",
                        "res_id": self.id,
                        "src": self.name,
                        "value": value,
                        "state": "translated",
                    }
                )

    def change_current_date_hijri(self):
        year = datetime.now().year
        day = datetime.now().day
        month = datetime.now().month
        hijri_date = convert.Gregorian(year, month, day).to_hijri()
        return hijri_date

    @api.depends('base_salary')
    def get_salary_amount(self):
        for item in self:
            item.salary_in_words = num2words(item.base_salary, lang=self.env.user.lang)

    def compute_base_salary(self):
        for item in self:
            last_day_of_prev_month = datetime.now().date().replace(day=1) - timedelta(days=1)
            start_day_of_prev_month = datetime.now().date().replace(day=1) - timedelta(days=last_day_of_prev_month.day)

            payroll = item.env['hr.payslip'].search(
                [('employee_id', '=', item.name), ('date_from', '<=', datetime.now().date()),
                 ('date_to', '>=', datetime.now().date()), ('contract_id', '=', item.contract_id.id)], limit=1)
            if not payroll:
                payroll = item.env['hr.payslip'].search(
                    [('employee_id', '=', item.name), ('date_from', '<=', start_day_of_prev_month),
                     ('date_to', '>=', last_day_of_prev_month), ('contract_id', '=', item.contract_id.id)], limit=1)

            item.base_salary = payroll.total_allowances
            item.payslip_lines = payroll.allowance_ids.filtered(
                lambda r: r.salary_rule_id.rules_type in ('salary', 'house', 'transport', 'other')).sorted(
                lambda b: b.name)

    @api.model
    def create(self, vals):
        new_record = super(HrEmployee, self).create(vals)
        update_list = []
        if vals.get("passport_id", False):
            update_list.append(vals.get("passport_id", False))

        if vals.get("iqama_number", False):
            update_list.append(vals.get("iqama_number", False))

        if vals.get("saudi_number", False):
            update_list.append(vals.get("saudi_number", False))

        if vals.get("license_number_id", False):
            update_list.append(vals.get("license_number_id", False))

        if vals.get("copy_examination_file", False):
            update_list.append(vals.get("copy_examination_file", False))

        if update_list:
            documents_ids = self.env["hr.employee.document"].browse(update_list)
            documents_ids.write({"employee_ref": new_record.id})
        if "context" in dir(self.env) and new_record.name:
            if new_record.english_name:
                new_record.translate_employee_name()
        # seq = self.env['ir.sequence'].next_by_code('hr.employee') or '/'
        return new_record

    @api.constrains("emp_no", "birthday", 'attachment_ids')
    def e_unique_field_name_constrains(self):
        for item in self:
            items = self.search([("emp_no", "=", item.emp_no)])
            if len(items) > 1:  # return more than one item with the same value
                raise ValidationError(
                    _("You cannot create Employee with the same employee number")
                )
            if item.birthday >= date.today():
                raise Warning(_("Sorry,The Birthday Must Be Less than Date Today"))
            if item.attachment_ids:
                for rec in item.attachment_ids:
                    if not rec.doc_name:
                        raise exceptions.Warning(_('Attach the attachment to the Document %s') % (rec.name))

    @api.constrains("user_id")
    def e_unique_user_id(self):
        for item in self:
            items = self.search([("user_id", "=", item.user_id.id)]).ids
            if (
                    len(items) > 1 and item.user_id.id > 1
            ):  # return more than one item with the same value
                raise ValidationError(
                    _(
                        "This User Cannot Be Selected While He is Linked to Another Employee"
                    )
                )

    '''@api.onchange('department_id')
    def onchange_department_id(self):
        if self.department_id:
            self.department = self.department_id'''

    @api.onchange("line_man")
    def onchange_line_man(self):
        self.r_manager = self.line_man

    def action_create_user(self):
        self.ensure_one()
        config = self.env['ir.config_parameter'].sudo()
        login_option = config.get_param('hr_base.employee_login')
        if login_option == 'identity':
            login = self.iqama_number.iqama_id or self.saudi_number.saudi_id
            login_label = _('Identity Number')
        else:
            login = self.work_email
            login_label = _('Email Address')

        if self.user_id:
            raise ValidationError(_("This employee already has an user."))
        return {
            'name': _('Create User'),
            'type': 'ir.actions.act_window',
            'res_model': 'res.users',
            'view_mode': 'form',
            'view_id': self.env.ref('hr_base.view_users_simple_form').id,
            'target': 'new',
            'context': {
                'default_create_employee_id': self.id,
                'default_name': self.name,
                'default_phone': self.work_phone,
                'default_mobile': self.mobile_phone,
                'default_login': login,

            }
        }

    def draft_state(self):
        for item in self:
            state = item.state
            # Check if the employee contract is End
            if state == "out_of_service":
                if item.contract_id:
                    if item.contract_id.state == "end_contract":
                        raise exceptions.Warning(_("Please Re-contract ,because the contract in End contract state"))
            item.state = "draft"

    def complete_state(self):
        self.state = "complete"

    # create contract
    def create_contract(self):
        if self.contract_id:
            raise exceptions.Warning(_("You have already a contract"))
        else:
            seq = self.env["ir.sequence"].next_by_code("hr.contract") or "/"
            action = self.env.ref("hr_contract.action_hr_contract")
            result = action.read()[0]
            result["views"] = [
                (self.env.ref("hr_contract.hr_contract_view_form").id, "form")
            ]
            # override the context to get rid of the default filtering
            result["context"] = {"default_name": seq, "default_employee_id": self.id}
            result.update(
                {"view_type": "form", "view_mode": "form", "target": "current"}
            )

        self.state = "open"
        return result

    # Change state to open if there is a contract
    def open_sate(self):
        for item in self:
            if item.contract_id:
                item.state = "open"
            else:
                raise exceptions.Warning(_("Employee %s has no contract") % item.name)

    def unlink(self):
        for i in self:
            if i.state != 'draft':
                raise exceptions.Warning(_('You can not delete record in state not in draft'))
            if i.contract_id.hiring_date:
                raise exceptions.Warning(_('You can not delete record has Hiring date'))
        return super(HrEmployee, self).unlink()


class emplpyeeattachmentname(models.Model):
    _name = 'emplpyee.attachment.name'

    _rec_name = 'name'
    name = fields.Char()


class emplpyeeattachment(models.Model):
    _name = 'emplpyee.attachment'
    _rec_name = 'doc_name'

    employee_attaches_id = fields.Many2one(comodel_name='hr.employee')
    name = fields.Char()
    db_datas = fields.Char()
    doc_name = fields.Many2one(comodel_name='emplpyee.attachment.name', required=True)
    attachment = fields.Binary('Attachment')


class Trainings(models.Model):
    _name = "hr.trainings"
    _rec_name = "training_sum"
    _description = "HR Trainings"

    training_sum = fields.Char("Training Summary")
    start_date = fields.Date("Start Date")
    end_date = fields.Date("End Date")
    type_training = fields.Char("Type of Training")
    training_company = fields.Char("Training Company")
    training_place = fields.Char("Training Place")
    status = fields.Char()
    employee_id = fields.Many2one(
        comodel_name="hr.employee", string="Training Relation"
    )


class Religion(models.Model):
    _name = "hr.religion.religion"
    _rec_name = "name"
    _description = "HR Religion"

    name = fields.Char(required=True)


class Relation(models.Model):
    _name = "hr.relation.relation"
    _rec_name = "name"
    _description = "HR Relation"

    name = fields.Char(required=True)


class College(models.Model):
    _name = "hr.college"
    _description = "HR College"
    _rec_name = "name"

    name = fields.Char(required=True)


class Qualification(models.Model):
    _name = "hr.qualification"
    _description = "HR Qualification"
    _rec_name = "uni_name"

    uni_name = fields.Many2one(
        comodel_name="office.office", string="University Name", required=True
    )
    col_name = fields.Many2one(comodel_name="hr.college", string="College Name")
    prg_status = fields.Char("Program Status")
    comp_date = fields.Date("Completion Date")
    contact_name = fields.Char("Contact Name")
    contact_phn = fields.Char("Contact Phone No")
    contact_email = fields.Char("Contact Email")
    country_name = fields.Many2one(comodel_name="res.country")
    qualification_degree = fields.Selection(
        [
            ("weak", _("Weak")),
            ("good", _("Good")),
            ("very_good", _("Very Good")),
            ("excellent", _("Excellent")),
        ]
    )
    qualification_specification_id = fields.Many2one(
        comodel_name="qualification.specification",
        domain=[("type", "=", "qualification")],
    )

    # relation field
    qualification_relation_name = fields.Many2one(comodel_name="hr.employee")
    qualification_id = fields.Many2one(comodel_name="hr.qualification.name", string="Qualification Name")
    attachment = fields.Binary("Attachment")


class HrEmployeeHistory(models.Model):
    _name = "hr.employee.history"
    _description = "HR Employee History"

    employement_history = fields.Many2one(comodel_name="hr.employee")
    name = fields.Char(required=True)
    position = fields.Char(required=True)
    employeer = fields.Char(required=True)
    salary = fields.Float(required=True)
    address = fields.Char(required=True)
    date_from = fields.Date()
    date_to = fields.Date()
    country = fields.Many2one(comodel_name="res.country")


class Payslip(models.Model):
    _name = "employee.payslip"
    _description = "Employee Payslip"

    payslip = fields.Char()
    date = fields.Date()


class Project(models.Model):
    _name = "projects.projects"
    _description = "Projects"

    _rec_name = "name"
    name = fields.Char()


class QualificationSpecification(models.Model):
    _name = "qualification.specification"
    _description = "Qualification Specification"

    name = fields.Char()
    type = fields.Selection(
        selection=[("qualification", "Qualification"), ("certificate", "Certificate")],
        string="Type")


# Hr_job
class Job(models.Model):
    _inherit = "hr.job"

    employee_ids = fields.One2many("hr.employee", "job_id", string="Employees", domain=[("state", "=", "open")])
    department_ids = fields.Many2many("hr.department", string="Departments")
    description = fields.Html(string="Job Description")
    english_name = fields.Char(string='English Name')

    @api.depends('no_of_recruitment', 'employee_ids.job_id', 'employee_ids.active','employee_ids.state')
    def _compute_employees(self):
        for rec in self:
            super(Job,rec)._compute_employees()


class AddressCity(models.Model):
    _name = "address.city"
    _description = "City Address"

    name = fields.Char()


class AddressRegion(models.Model):
    _name = "address.region"
    _description = "Region Address"

    name = fields.Char()


class HrAttendances(models.Model):
    _inherit = "resource.calendar"

    work_days = fields.Integer()
    work_hour = fields.Integer()
    overtime_factor_daily = fields.Float(string="Overtime Factor Daily")
    overtime_factor_holiday = fields.Float(string="Overtime Factor Holiday")
    max_overtime_hour = fields.Integer()
    request_after_day = fields.Integer(string='Request After Day',
          help='It is not possible to request Overtime after these days from the end of the request month')

    journal_overtime_id = fields.Many2one('account.journal')
    account_overtime_id = fields.Many2one('account.account')
    analytic_account_id = fields.Many2one(comodel_name='account.analytic.account')

    transfer_by_emp_type = fields.Boolean('Transfer By Emp Type')
    account_ids = fields.One2many('hr.overtim.accounts', 'overtim_id')

    #get account IDs base on Overtim Employees Type account config
    def get_debit_overtim_account_id(self, emp_type):
        if not self.transfer_by_emp_type :  return self.account_overtime_id
        account_mapping = self.account_ids.filtered(lambda a: a.emp_type_id.id == emp_type.id)
        return account_mapping[0].debit_account_id if account_mapping else False

class HrOvertimAccounts(models.Model):
    _name = 'hr.overtim.accounts'
    _description = 'Overtim Account Mapping'

    overtim_id = fields.Many2one('resource.calendar', string="Overtim Type", required=True, ondelete="cascade")
    emp_type_id = fields.Many2one('hr.contract.type', string="Employee Type", required=True)
    debit_account_id = fields.Many2one('account.account', string="Debit Account", required=True)


class HrQualificationName(models.Model):
    _name = "hr.qualification.name"
    _description = "HR Qualification Name"

    name = fields.Char(string="Qualification")
    sequence = fields.Integer(string="Sequence")
    parent_id = fields.Many2one(comodel_name="hr.qualification.name", string="Upper Qualification")


class WorkLocation(models.Model):
    _name = 'work.location'
    _description = "Work Location"

    name = fields.Char(string='Name')
