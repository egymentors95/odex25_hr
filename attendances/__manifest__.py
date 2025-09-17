{
    'name': 'HR Attendance customizations',
    'category': 'Odex25-HR/Odex25-HR',
    'summary': 'HR Management Attendance config module',
    'description': """It is a procedure that Record all Employee attendance """,
    'version': '1.0',
    'sequence': 4,
    'website': 'http://exp-sa.com',
    'license': 'GPL-3',
    'author': 'Expert Co. Ltd.' ,
    'depends': ['base', 'hr_attendance', 'report_xlsx','hr_base','exp_payroll_custom',],
    # hr_holidays_public
    'data': [
        'security/attendance_security.xml',
        'security/ir.model.access.csv',
        'data/ir_cron.xml',
        'data/mail_template.xml',
        'views/hr_attendance_report.xml',
        'views/hr_attendance_transactions.xml',
        'views/hr_lateness_reasons.xml',
        'views/hr_attendance_register_view.xml',
        'views/hr_attendance_view.xml',
        'wizard/attendance_wizard_view.xml',
        'wizard/attendances_report_view.xml',
        'views/attendance_menu_item_view.xml',
        'views/hr_employee_view.xml',
        'report/employee_attendances_report_template.xml',
        'views/email.xml',

    ],

    'installable': True,
    'application': True,
}
