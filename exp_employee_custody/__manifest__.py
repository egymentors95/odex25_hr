# -*- coding: utf-8 -*-
{
    'name': 'HR Custody',
    'category': 'Odex25-HR/Odex25-HR',
    'summary': 'Custody and receiving Employee custody',
    'version': '1.0',
    'sequence': 4,
    'website': 'http://exp-sa.com',
    'license': 'GPL-3',
    'author': 'Expert Co. Ltd.',

    'depends': ['base','hr_base','employee_requests'],

    'data': [
        'security/ir.model.access.csv',
        'security/custody_security.xml',
        'views/employee_custody_views.xml',
        'views/receiving_employee_custody.xml',
    ],
 }
