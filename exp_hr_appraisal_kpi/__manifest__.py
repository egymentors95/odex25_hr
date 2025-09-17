# -*- coding: utf-8 -*-
###################################################################################

{
    'name': 'Appraisal KPI',
    'version': '11.0.1.0.0',
    'category': 'HR-Odex',
    'summary': 'Manage Appraisal KPI',
    'description': """
        Helps you to manage Appraisal of your company's staff.
        """,
    'author': 'Expert Co. Ltd.',
    'company': 'Exp-co-ltd',
    'maintainer': 'Cybrosys Techno Solutions',
    'website': 'http://exp-sa.com',
    'depends': [

       'exp_hr_appraisal', 'base','kpi_scorecard', 'hr','kpi_scorecard', 'account', 'exp_hr_payroll', 'mail', 'hr_base', 'hr_contract', 'hr_contract_custom'

    ],
    'data': [
        'security/group.xml',
        'security/ir.model.access.csv',
        'views/kpi_category.xml',
        'views/kpi_item.xml',
        'views/kpi_period.xml',
        'views/kpi_skills.xml',
        'views/skill_appraisal.xml',
        'views/years_employee_goals.xml',
        'views/employee_performance_evaluation.xml',
        'views/appraisal_percentage.xml',
        'views/employee_apprisal.xml',
    


    ],
    'installable': True,
    'auto_install': False,
}
