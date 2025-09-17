# -*- coding: utf-8 -*-

import datetime
from datetime import datetime as dt
from odoo import models, fields, _


class renew_official_paper(models.Model):
    _name = 'hr.renew.official.paper'
    _rec_name = 'document_type'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    document_type = fields.Selection([('passport', _('Passport')), ('license', _('License')),
                                      ('Iqama', _('Iqama')), ('saudi', _('Saudi ID')),
                                      ('medical_Examination', _('medical Examination')),
                                      ('other', _('Other'))])

    expire_before = fields.Selection(selection=[("date", _("Date")), ("days", _("Days"))])
    date = fields.Date()
    days = fields.Integer()
    official_paper_ids = fields.One2many(comodel_name='hr.official.paper.line', inverse_name='official_paper_line')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.user.company_id)

    def get_data(self):
        data = []
        for item in self:
            item.official_paper_ids.unlink()
            employee_ids = self.env['hr.employee'].search([('state', '=', 'open')], order='id desc')
            for employee_id in employee_ids:
                document_details_ids = self.env['hr.employee.document'].search(
                    [('employee_ref', '=', employee_id.id), ('document_type', '=', item.document_type)])
                for document_details in document_details_ids:
                    current_date = datetime.datetime.now()
                    if item.expire_before == 'date':
                        if self.date:
                            new_date = dt.strptime(str(self.date), "%Y-%m-%d")
                            if document_details.expiry_date:
                                document_date = dt.strptime(str(document_details.expiry_date), "%Y-%m-%d")

                                if document_date <= new_date:
                                    self.env['hr.official.paper.line'].create({
                                        'official_paper_line': item.id,
                                        'employee_id': employee_id.id,
                                        'department': employee_id.department_id.id,
                                        'job_id': employee_id.job_id.id,
                                        'job_no': employee_id.job_id.id,
                                        'nationality': employee_id.country_id.id,
                                        'document_type': document_details.document_type,
                                        'expire_date': document_details.expiry_date,

                                    })
                                    for items in self.official_paper_ids:
                                        data.append({
                                            'employee_id': items.employee_id.name,
                                            'department': items.department.name,
                                            'job_id': items.job_id.name,
                                            'job_no': items.job_no,
                                            'nationality': items.nationality.name,
                                            'document_type': items.document_type,
                                            'expire_date': items.expire_date,
                                        })
                    elif item.expire_before == 'days':
                        if document_details.expiry_date:
                            document_date = dt.strptime(str(document_details.expiry_date), "%Y-%m-%d")
                            if document_date:
                                days = (document_date - current_date).days
                                if days <= item.days:
                                    self.env['hr.official.paper.line'].create({
                                        'official_paper_line': item.id,
                                        'employee_id': employee_id.id,
                                        'department': employee_id.department_id.id,
                                        'job_id': employee_id.job_id.id,
                                        'job_no': employee_id.job_id.id,
                                        'nationality': employee_id.country_id.id,
                                        'document_type': document_details.document_type,
                                        'expire_date': document_details.expiry_date,

                                    })
                                    for items in self.official_paper_ids:
                                        data.append({
                                            'employee_id': items.employee_id.name,
                                            'department': items.department.name,
                                            'job_id': items.job_id.name,
                                            'job_no': items.job_no,
                                            'nationality': items.nationality.name,
                                            'document_type': items.document_type,
                                            'expire_date': items.expire_date,
                                        })
