from odoo import models, api
from odoo.exceptions import UserError
from odoo.tools.translate import _


class EmployeeVacation(models.AbstractModel):
    _name = "report.employee_requests.report_employee_identification"

    @api.model
    def _get_report_values(self, docids, data):
        docs = self.env['employee.other.request'].browse(docids)
        '''for record in docs:
            if record.state != 'approved':
                raise UserError(_("Sorry, you cannot print the report until final approval of the request"))'''
        docargs = {
            'doc_ids': [],
            'doc_model': ['employee.other.request'],
            'docs': docs,
        }
        return docargs
