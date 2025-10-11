# -*- coding: utf-8 -*-

from odoo import models
import logging

_logger = logging.getLogger(__name__)


class AccountEdiFormat(models.Model):
    _inherit = "account.edi.format"

    def _embed_edis_to_pdf(self, pdf_content, invoice):
        is_tax_invoice = 1 if invoice.l10n_sa_invoice_type == 'Standard' else 0
        xml = invoice.zatca_hash_cleared_invoice if is_tax_invoice else invoice.zatca_invoice
        if xml:
            return pdf_content
        else:
            return super()._embed_edis_to_pdf(pdf_content, invoice)
