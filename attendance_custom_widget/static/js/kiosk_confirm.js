odoo.define('attendance_custom_widget.kiosk_confirm', function (require) {
    var KioskConfirm = require('hr_attendance.kiosk_confirm');
    KioskConfirm.include({
        events: _.extend({}, KioskConfirm.prototype.events, {
            "click .o_hr_attendance_sign_in_out_icon": _.debounce(function () {
                var self = this;
                var selected_action = this.$el.find('.o_sign_in_out_selection').val();
                this._rpc({
                    model: 'hr.employee',
                    method: 'attendance_manual',
                    args: [[this.employee_id], this.next_action],
                    kwargs: {selected_action: selected_action},
                })
                    .then(function (result) {
                        if (result.action) {
                            self.do_action(result.action);
                        } else if (result.warning) {
                            self.do_warn(result.warning);
                        }
                    });
            }, 200, true)
        }),
    });

    return KioskConfirm;
});
