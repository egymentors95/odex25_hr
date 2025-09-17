from odoo import api, fields, models, _


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    contract_id = fields.Many2one('hr.contract', string='Current Contract',
                                  groups="base.group_user",
                                  domain="[('company_id', '=', company_id)]",
                                  help='Current contract of the employee')


    barcode = fields.Char(string="Badge ID", help="ID used for employee identification.", groups="base.group_user",
                          copy=False)
    birthday = fields.Date('Date of Birth', groups="base.group_user", tracking=True)
    address_home_id = fields.Many2one(
        'res.partner', 'Address',
        help='Enter here the private address of the employee, not the one linked to your company.',
        groups="base.group_user", tracking=True,
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")

    certificate = fields.Selection([
        ('graduate', 'Graduate'),
        ('bachelor', 'Bachelor'),
        ('master', 'Master'),
        ('doctor', 'Doctor'),
        ('other', 'Other'),
    ], 'Certificate Level', default='other', groups="base.group_user", tracking=True)
    children = fields.Integer(string='Number of Children', groups="base.group_user", tracking=True)
    country_of_birth = fields.Many2one('res.country', string="Country of Birth", groups="base.group_user",
                                       tracking=True)
    emergency_contact = fields.Char("Emergency Contact", groups="base.group_user", tracking=True)
    emergency_phone = fields.Char("Emergency Phone", groups="base.group_user", tracking=True)
    phone = fields.Char(related='address_home_id.phone', related_sudo=False, readonly=False, string="Private Phone",
                        groups="base.group_user")
    identification_id = fields.Char(string='Identification No', groups="base.group_user", tracking=True)
    km_home_work = fields.Integer(string="Home-Work Distance", groups="base.group_user", tracking=True)
    permit_no = fields.Char('Work Permit No', groups="base.group_user", tracking=True)
    pin = fields.Char(string="PIN", groups="base.group_user", copy=False,
                      help="PIN used to Check In/Out in Kiosk Mode (if enabled in Configuration).")
    place_of_birth = fields.Char('Place of Birth', groups="base.group_user", tracking=True)
    spouse_birthdate = fields.Date(string="Spouse Birthdate", groups="base.group_user", tracking=True)
    spouse_complete_name = fields.Char(string="Spouse Complete Name", groups="base.group_user", tracking=True)
    study_field = fields.Char("Field of Study", groups="base.group_user", tracking=True)
    study_school = fields.Char("School", groups="base.group_user", tracking=True)
    visa_expire = fields.Date('Visa Expire Date', groups="base.group_user", tracking=True)
    visa_no = fields.Char('Visa No', groups="base.group_user", tracking=True)
