{
    'name': 'HR Administrative Circulars And Decitions',
    'category': 'Odex25-HR/Odex25-HR',
    'summary': 'Manages both Internaal and External Administrative Circulars And Decitions',
    'version': '1.0',
    'sequence': 4,
    'website': 'http://exp-sa.com',
    'license': 'GPL-3',
    'author': 'Expert Co. Ltd.',
    'depends': ['hr_base'],
    'data': [

        'security/ir.model.access.csv',
        'security/administrative_security.xml',
        'report/administrative_circular_decision_templates.xml',
        'views/administrative_circular_decision_report.xml',
        'views/administrative_circular_view.xml',
        'data/mail_template_data.xml',
    ],
    'installable': True,
    'application': True,
 }

