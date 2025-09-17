{
    'name': "HR Payroll Promotion",
    'category': 'Odex25-HR/Odex25-HR',
    'summary': '''Add Promotion processes to allow employee's annual raises and promotions''',
    'version': '1.0',
    'sequence': 40,
    'website': 'http://exp-sa.com',
    'license': 'GPL-3',
    'author': 'Expert Co. Ltd.',
    'depends': [
        'exp_payroll_custom',
        'hr_job_career_path',
        'hr_disciplinary_tracking',
        'hr_holidays_public',
        'exp_official_mission'],
    'data': [
        'security/ir.model.access.csv',

        'views/hr_employee_view.xml',
        'views/hr_payroll_structure_view.xml',
        'views/hr_payroll_raise_view.xml',
        'views/hr_penalty_register_view.xml',
        'views/hr_payroll_promotion_view.xml',
        'views/hr_payroll_promotion_setting_view.xml',
        'views/hr_payroll_nomination_view.xml',
        'views/hr_official_mission_view.xml',
        'views/hr_holidays_view.xml',

    ],
    'installable': True,
    'application': False,
}
