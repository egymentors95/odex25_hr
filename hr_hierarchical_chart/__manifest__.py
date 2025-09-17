# -*- coding: utf-8 -*-
{
    'name': "Hr Hierarchy Chart",



    'description': """
        add hierarchy view to odoo
    """,

    'category': 'Odex25-HR/Odex25-HR',
    'author': "Expert Co. Ltd.",
    'website': "http://www.exp-sa.com",
    # any module necessary for this one to work correctly
    'depends': ['web','exp_payroll_custom','hr_org_chart'],

    # always loaded
    'data': [
        'views/chart_view.xml',
        'views/views.xml',

    ],
    'qweb': ["static/src/xml/hierarchical_chart_templates.xml","static/src/xml/department_template.xml"],


}
