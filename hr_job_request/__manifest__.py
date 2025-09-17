{
    'name': 'HR Job Request',
    'category': 'Odex25-HR/Odex25-HR',
    'summary': 'Add new feauture to hr recruitment',
    'version': '1.0',
    'sequence': 4,
    'website': 'http://exp-sa.com',
    'license': 'GPL-3',
    'author': 'Expert Co. Ltd.',

    'depends': ['hr_base', 'hr_recruitment'],

    'data': [
        'security/hr_base_security.xml',
        'security/ir.model.access.csv',
        'views/hr_base_view.xml',
        'views/job_request_view.xml',
        'views/hr_applicant.xml',
        'views/menus_view.xml',

    ],
    'installable': True,
    'application': False,
}
