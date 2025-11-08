# -*- coding: utf-8 -*-
{
    'name': "Attendance system",

    'summary': """
        Short (1 phrase/line) summary of the module's purpose, used as
        subtitle on modules listing or apps.openerp.com""",

    'description': """
        Long description of module's purpose
    """,

    'author': "Expert",
    'website': "http://www.exp-sa.com",

    'category':'Odex25-HR/Odex25-HR',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/views.xml',
        # 'wizard/attendaces_wizard.xml',
        'data/scheduler_data.xml',
    ]
}
