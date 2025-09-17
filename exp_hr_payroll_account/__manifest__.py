# -*- coding:utf-8 -*-

{
    'name': 'Payroll Accounting',
    'category': 'Odex25-HR/Odex25-HR',
    'description': """
    Generic Payroll system Integrated with Accounting.
    ==================================================

        * Expense Encoding
        * Payment Encoding
        * Company Contribution Management
        """,
    'depends': [
        'exp_hr_payroll',
        'account'
    ],
    'data': [
        'views/hr_payroll_account_views.xml'
    ],
    'demo': [],
    'test': ['../account/test/account_minimal_test.xml'],
    'images': ['static/description/banner.png'],
    'application': True,
}
