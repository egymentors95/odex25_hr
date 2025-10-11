# -*- coding: utf-8 -*-
from odoo.addons.mail.controllers.main import MailController
from odoo.http import request
from odoo import http


class ZatcaMailController(MailController):

    @http.route('/mail/thread/data', methods=['POST'], type='json', auth='user')
    def mail_thread_data(self, thread_model, thread_id, request_list, **kwargs):
        ret_list = super().mail_thread_data(thread_model, thread_id, request_list, **kwargs)
        if thread_model == 'account.move' and thread_id and 'attachments' in request_list:
            thread = request.env[thread_model].with_context(
                active_test=False).search([('id', '=', thread_id)])
            if thread.disable_odoo_invoices and thread.zatca_invoice_name:
                report_name = thread.zatca_invoice_name.replace('.xml', '.pdf')
                zatca_attachment = [rec for rec in ret_list['attachments'] if
                                    rec['name'] == report_name]
                if len(zatca_attachment) > 0:
                    ret_list['attachments'] = [
                        {**rec, 'is_main': rec['name'] == report_name}
                        for rec in ret_list['attachments']
                    ]
        return ret_list
