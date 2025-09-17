from odoo import models, fields, api, _


class HrPersonalPermissionType(models.Model):
    _name = 'hr.personal.permission.type'
    _order = 'sequence asc'

    name = fields.Char(required=True)
    sequence = fields.Integer(readonly=True)
    daily_hours = fields.Float()
    monthly_hours = fields.Float()
    approval_by = fields.Selection(
        [('direct_manager', 'Direct Manager'), ('hr_manager', 'HR Manager')], 
        default='direct_manager', 
        required=True
    )
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('uniq_name', 'UNIQUE(name)', _('Name should be unique!'))
    ]
    