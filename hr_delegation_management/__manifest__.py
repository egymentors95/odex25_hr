# -*- coding: utf-8 -*-
{
    'name': 'HR Delegation Management',
    'version': '1.0',
    'category': 'Odex25-HR/Odex25-HR',
    'summary': """HR Delegation Management""",
    'depends': ['hr_base'],
    'author': 'Expert Co. Ltd.' ,
    'website': 'http://exp-sa.com',
    'data': [
        'security/hr_base_security.xml',
        'security/ir.model.access.csv',
        'data/cron_assign_groups.xml',
        'views/authority_delegation.xml',
        'views/model_configuration.xml',
    ],
}
