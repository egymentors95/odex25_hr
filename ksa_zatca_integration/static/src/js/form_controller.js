odoo.define('ksa_zatca_integration.FormController', function (require) {
    "use strict";

    var FormController = require('web.FormController');

    FormController.include({
        _getActionMenuItems: function (state) {
            var ret_dict = this._super.apply(this, arguments);
            var record = state?.data;
            var context = ret_dict?.context;
            if (state.model === 'account.move') {
                if (ret_dict?.items?.print.length > 1) {
                    if (record?.is_zatca)
                        ret_dict.items.print = ret_dict.items.print
                            .reduce((result, item) => {
                                if (item.name.includes("ZATCA")) {
                                    result.unshift(item);
                                } else {
                                    result.push(item);
                                }
                                return result;
                            }, []);
                    // remove zatca report print, for non zatca companies
                    else
                        ret_dict.items.print = ret_dict.items.print
                            .filter(item => !item.name.includes("ZATCA"));
                }

                if (record?.is_zatca && record?.disable_odoo_invoices && (
                    ["out_invoice", "out_refund"].includes(context?.default_move_type) ||
                    (("in_invoice").includes(context?.default_move_type) && record?.l10n_is_self_billed_invoice))) {
                    const unwantedNames = ["Invoices without Payment", "Invoices", 'الفواتير غير المدفوعة ', 'فواتير العملاء '];
                    ret_dict.items.print = ret_dict.items.print.filter(item => !unwantedNames.includes(item.name));
                }
            }

            return ret_dict;
        },
    })
})
