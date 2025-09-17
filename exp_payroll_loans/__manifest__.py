# -*- coding: utf-8 -*-
{
    'name': 'HR Advance Payroll And Loans',
    'version': '1.0',
    'category': 'Odex25-HR/Odex25-HR',
    'sequence': 4,
    'website': 'http://exp-sa.com',
    'license': 'GPL-3',
    'author': 'Expert Co. Ltd.',
    'summary': 'Advance Payroll And Loans In HR',
    'description': """
      link between Payroll and loans
        """,
    'depends': [
        # 'exp_hr_payroll', 'hr_holidays', 'hr', 'account', 'hr_contract',
        'hr_base',
        'exp_payroll_custom', 'hr_loans_salary_advance',
    ],
    'data': [

        'security/exp_payroll_loans_security.xml',
        'security/ir.model.access.csv',
        'views/reconcile_leaves_view.xml',
        'views/loans.xml',

    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
