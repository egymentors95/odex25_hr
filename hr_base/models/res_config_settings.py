# -*- coding: utf-8 -*-

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    employee_login = fields.Selection([('email', 'By Email'), ('identity', 'By dentity')], 'Login Option', default='email', config_parameter='hr_base.employee_login')

