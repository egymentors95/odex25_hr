# -*- coding: utf-8 -*-
import math
from dateutil import relativedelta

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class HrHolidaysStatus(models.Model):
    _inherit = 'hr.holidays.status'

    studying_leave = fields.Boolean('Studying Leave', default=False)


class HrHolidays(models.Model):
    _inherit = 'hr.holidays'

    successful_completion = fields.Boolean('Successful Completion', default=False)
