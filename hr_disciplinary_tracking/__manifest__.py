# -*- coding: utf-8 -*-
{
    'name': 'HR Penalty',
    'version': '1.0',
    'category': 'Odex25-HR/Odex25-HR',
    'summary': """Employee Violations and Penalties Management""",
    'depends': ['base', 'mail', 'hr_termination', 'exp_payroll_custom'],
    'author': 'Expert Co. Ltd.' ,
    'website': 'http://exp-sa.com',
    'data': [
        # data
        'data/data.xml',
        # actions and views
        'security/ir.model.access.csv',
        'security/security.xml',
        'views/penalty_register.xml',
        # 'views/employee_deductions.xml',
        'views/penalty.xml',
        'views/punishment_view.xml',
        # menu items
        'views/penalty_deductions_menus.xml',
        'wizard/hr_penalty_report_view.xml',
        'report/hr_penalty_report.xml',
    ],
    'demo': [],
    'license': 'AGPL-3',
    'installable': True,
    'auto_install': False,
    'application': True,
}
