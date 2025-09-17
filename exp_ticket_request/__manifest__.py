{
    'name': 'HR Ticket Request',
    'category': 'HR-Odex',
    'summary': 'Employee Ticket Request',
    'version': '1.0',
    'sequence': 4,
    'website': 'http://exp-sa.com',
    'license': 'GPL-3',
    'author': 'Expert Co. Ltd.' ,
    'depends': ['base','hr','hr_base','mail','account','exp_payroll_custom'],
    'data': [

        'security/exp_ticket_request_security.xml',
        'security/ir.model.access.csv',

        'views/hr_ticketing_view.xml',

    ],

    'installable': True,
    'application': True,
}
