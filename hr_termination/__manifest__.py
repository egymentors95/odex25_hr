# -*- coding: utf-8 -*-

{
    'name': 'Employee Termination',
    'category': 'Odex25-HR/Odex25-HR',
    'version': '14.0.1.0.0',
    'author': 'Expert Co. Ltd.',
    'summary': 'Create Contract Termination Requests for Employees',
    'description': """It is a procedure that calculates all Employee end-of-service Benefits according to the labor 
    laws """,

    'depends': ['base', 'hr', 'account', 'employee_requests', 'hr_loans_salary_advance', 'exp_payroll_custom','hr_holidays_public'],


    'demo': [],
    'data': [

        'security/security.xml',
        'security/ir.model.access.csv',
        'views/termination_resignation_eos.xml',
        'views/eos_patch.xml',
        'views/hr_termination_type_view.xml',
        'views/hr_allowance_deduction_view.xml',
        'data/hr_termiation_data.xml',
        # menu items
        'views/hr_termination_menu.xml',
        # report & wizard
        'report/termination_report_template.xml',
        'wizard/termination_allowan_report_view.xml',
        'wizard/hr_termination_report_view.xml',
        'report/employee_termination_report.xml',
        'report/hr_termination_report.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'AGPL-3',
}
