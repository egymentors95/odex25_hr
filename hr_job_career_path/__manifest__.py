{
    'name': "HR Career Path",
    'category': 'Odex25-HR/Odex25-HR',
    'summary': '''Add new features to the Job and plan the career path''',
    'version': '1.0',
    'sequence': 40,
    'website': 'http://exp-sa.com',
    'license': 'GPL-3',
    'author': 'Expert Co. Ltd.',
    'depends': ['hr_base',
                'employee_requests',
                'hr_job_request',
                'exp_payroll_custom',
                'exp_official_mission'],

    'data': [
        'security/ir.model.access.csv',
        'views/hr_job_view.xml',
        'views/hr_payroll_structure_view.xml',
        'views/employee_department_job_view.xml',

    ],
    'installable': True,
    'application': False,
}
