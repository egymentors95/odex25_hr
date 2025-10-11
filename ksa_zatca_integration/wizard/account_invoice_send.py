# -*- coding: utf-8 -*-

from odoo import api, fields, models, _, exceptions


class AccountInvoiceSend(models.TransientModel):
    _inherit = 'account.invoice.send'

    # snailmail_account inherit
    def snailmail_print_action(self):
        self.ensure_one()
        if list(set(self.invoice_ids.mapped('disable_odoo_invoices'))) == [False] or len(
                self.invoice_ids.ids) > 1 or not self.invoice_ids.is_zatca or not self.invoice_ids.zatca_invoice:
            return super().snailmail_print_action()

        is_tax_invoice = 1 if self.invoice_ids.l10n_sa_invoice_type == 'Standard' else 0
        if is_tax_invoice:
            report_template = self.invoice_ids._get_zatca_invoice()[0]
        else:
            report_template = self.invoice_ids._get_zatca_invoice()[1]

        letters = self.env['snailmail.letter']
        for invoice in self.invoice_ids:
            letter = self.env['snailmail.letter'].create({
                'partner_id': invoice.partner_id.id,
                'model': 'account.move',
                'res_id': invoice.id,
                'user_id': self.env.user.id,
                'company_id': invoice.company_id.id,
                'report_template': self.env.ref(report_template).id
            })
            letters |= letter

        self.invoice_ids.filtered(lambda inv: not inv.is_move_sent).write({'is_move_sent': True})
        if len(self.invoice_ids) == 1:
            letters._snailmail_print()
        else:
            letters._snailmail_print(immediate=False)

    # account inherit
    def _print_document(self):
        self.ensure_one()
        self = self.with_context(via_account_invoice_send=True)
        return super()._print_document()

    @api.onchange('invoice_ids')
    def _compute_composition_mode(self):
        self = self.with_context(via_account_invoice_send=True)
        for wizard in self:
            if list(set(wizard.invoice_ids.mapped('disable_odoo_invoices'))) == [True] and len(
                    wizard.invoice_ids) > 1 and any(
                invoice.is_zatca or invoice.zatca_invoice for invoice in wizard.invoice_ids):
                raise exceptions.ValidationError(_("Only 1 zatca invoice can used"))
                #
                # if not all(invoice.is_zatca or invoice.zatca_invoice for invoice in
                #            wizard.invoice_ids):
                # elif not all(invoice.l10n_sa_invoice_type == 'Standard' for invoice in
                #              wizard.invoice_ids):
                #     raise exceptions.ValidationError(_("All zatca invoices should be standard"))
                # elif not all(invoice.l10n_sa_invoice_type == 'Simplified' for invoice in
                #              wizard.invoice_ids):
                #     raise exceptions.ValidationError(_("All zatca invoices should be simplified"))
        super()._compute_composition_mode()

    def _send_email(self):
        if self.is_email:
            if self.invoice_ids.disable_odoo_invoices:
                self.invoice_ids.print_einv_auto(is_pdf=1)
                att = self.env['ir.attachment'].search(
                    [('res_id', 'in', self.invoice_ids.ids), ('res_model', '=', 'account.move'),
                     ('name', '=', self.invoice_ids.zatca_invoice_name.replace('.xml', '.pdf'))])
                self.attachment_ids = att.ids
                self.composer_id.attachment_ids = att.ids
        return super()._send_email()
