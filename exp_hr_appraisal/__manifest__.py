# -*- coding: utf-8 -*-
###################################################################################

{
    'name': 'Appraisal',
    'version': '11.0.1.0.0',
    'category': 'Odex25-HR/Odex25-HR',
    'summary': 'Manage Appraisal',
    'description': """
        Helps you to manage Appraisal of your company's staff.
        """,
    'author': 'Expert Co. Ltd.',
    'company': 'Exp-co-ltd',
    'maintainer': 'Cybrosys Techno Solutions',
    'website': 'http://exp-sa.com',
    'depends': [

        'base', 'hr', 'account', 'exp_hr_payroll', 'mail', 'hr_base', 'hr_contract', 'hr_contract_custom'

    ],
    'data': [
        'security/hr_appraisal_security.xml',
        'security/ir.model.access.csv',
        'views/appraisal_for_employees_view.xml',
        'views/employee_appraisal_view.xml',
        'views/appraisal_plan_view.xml',
        'views/appraisal_view.xml',
        'views/appraisal_degree_view.xml',
        'views/appraisal_result_view.xml',
        'views/manager_appraisal_complete_line_view.xml',
        'views/customize_contract_view.xml',
        'views/hr_contract_extension_view.xml',
        'views/appraisal_setting_view.xml',
        'data/cron_appraisal.xml',
    ],
    'installable': True,
    'auto_install': False,
}
