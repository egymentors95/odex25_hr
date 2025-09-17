# -*- coding: utf-8 -*-
{
    'name': "hr_custom_report",

    'summary': """
        Short (1 phrase/line) summary of the module's purpose, used as
        subtitle on modules listing or apps.openerp.com""",

    'description': """
        Long description of module's purpose
        this module hr coustom report
    """,

    'author': "My Company",
    'website': "http://www.yourcompany.com",

    'category': 'Odex25-HR/Odex25-HR',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['odex_fleet', 'hr'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'reports/report.xml',
        'reports/Know_the_salary_without_details.xml',
        'reports/salary_definition.xml',
        'reports/report_traffic.xml',
        'reports/profession_oriented_modification_tide_condition.xml',
        'reports/engineers_authority.xml',
        'reports/cultural_attache.xml',
        'reports/submitted_embassy.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}
