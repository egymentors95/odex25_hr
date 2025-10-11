odoo.define('ksa_zatca_integration.ListController', function (require) {
    "use strict";

    var ListController = require('web.ListController');

    ListController.include({
        _getActionMenuItems: function (state) {
            var ret_dict = this._super.apply(this, arguments);
            var record = this.getSelectedRecords()[0]?.data;
            var context = ret_dict?.context;

            if (state.model === 'account.move') {
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
