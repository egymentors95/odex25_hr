odoo.define('attendance_custom_widget.attendance', function (require) {
    var MyAttendance = require('hr_attendance.my_attendances');
    MyAttendance.include({
        update_attendance: function () {
            var self = this;
            var selected_action = this.$el.find('.o_sign_in_out_selection').val();
            this._rpc({
                model: 'hr.employee',
                method: 'attendance_manual',
                args: [[self.employee.id], 'hr_attendance.hr_attendance_action_my_attendances'],
                kwargs: {selected_action: selected_action},
            })
                .then(function (result) {
                    console.log(result.action);
                    if (result.action) {
                        self.do_action(result.action);
                    } else if (result.warning) {
                        self.do_warn(result.warning);
                    }
                });
        },
    });

    return MyAttendance;
});
