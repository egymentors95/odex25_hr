# -*- coding: utf-8 -*-
{
    'name': 'HR Holiday Permission',
    'version': '1.0',
    'summary': """HR Holiday Permission""",
    'description': """HR Holiday Permission.
    This module gives Feature  of deduct Permissions from holidays""",
    'category': 'HR-Odex',
    'author': 'Expert Co. Ltd.',
    'website': 'http://exp-sa.com',
    'depends': ['hr_holidays_public', 'employee_requests'],
    'license': 'LGPL-3',
    'data': [
        'views/permission_view.xml',
        'views/hr_holiday_view.xml',
    ],
    'demo': [],
    'installable': True,
    'auto_install': False,
    'application': True,
}
