# -*- coding: utf-8 -*-

{
    'name': 'EXP HR Holidays Public',
    'version': '1.0',
    'license': 'AGPL-3',
    'category': 'Odex25-HR/Odex25-HR',
    'author': 'Expert Co. Ltd.',
    'website': 'http://exp-sa.com',
    'summary': "Manage Public Holidays",
    'depends': ['hr_base', 'hr_government_relations', 'hr_holidays_community', 'exp_payroll_custom',
                'attendances', 'exp_ticket_request', 'report_xlsx'
                ],
    'data': [

        'security/hr_holidays_public_security.xml',
        'security/ir.model.access.csv',
        'data/crons.xml',

        'views/hr_holidays_public_view.xml',
        'views/hr_holidays_status_views.xml',
        # 'views/hr_holidays_public_view.xml',
        'views/hr_holidays_view.xml',
        'views/mail_template.xml',
        'views/leave_cancellation.xml',
        'views/leaves_balance.xml',
        'views/return_from_leave.xml',
        'views/hr_employee_customize.xml',
        'views/hr_government_exit_return_custom.xml',
        'views/hr_clearance_form_custom.xml',
        'views/hr_ticketing_custom.xml',
        'views/attendance_view.xml',
        'views/hr_holidays_restriction_view.xml',
        'views/leaves_menus_actions.xml',
        'views/hr_buy_vacation_view.xml',

        'wizards/holidays_public_next_year_wizard.xml',
        'wizards/holiday_public_leave_report_view.xml',

        'report/public_leave_report_template.xml',
        'report/public_leave_cost_template.xml',

    ],
    'installable': True,
    'application': True,
}
