# -*- coding: utf-8 -*-

{
    'name': 'EXP HR Holidays Public Workflow',
    'version': '1.0',
    'license': 'AGPL-3',
    'category': 'Odex25-HR/Odex25-HR',
    'author': 'Expert Co. Ltd.',
    'website': 'http://exp-sa.com',
    'summary': "Manage Public Holidays workflow",
    'depends': ['hr_holidays_public',
                ],
    'data': [
        'security/ir.model.access.csv',
        'views/hr_holidays_status_views.xml',
        'views/hr_holidays_view.xml',
        'views/holidays_workflow_view.xml',
        'data/holiday_status_data.xml',

    ],
    'installable': True,
    'application': False,
}
