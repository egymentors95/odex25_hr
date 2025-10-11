# -*- coding: utf-8 -*-
from odoo import models


class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    def _post_pdf(self, save_in_attachment, pdf_content=None, res_ids=None):
        # OVERRIDE to embed some EDI documents inside the PDF.
        if self.model == 'account.move' and res_ids and len(res_ids) == 1 and pdf_content and \
                self.xml_id in ['ksa_zatca_integration.report_e_invoicing_b2b_01',
                                'ksa_zatca_integration.report_e_invoicing_b2b_02',
                                'ksa_zatca_integration.report_e_invoicing_b2c']:
            invoice = self.env['account.move'].browse(res_ids)
            if invoice.is_zatca:
                pdf_content = invoice._l10n_sa_pdf_conversion(pdf_content)

        return super(IrActionsReport, self)._post_pdf(save_in_attachment, pdf_content=pdf_content,
                                                      res_ids=res_ids)
