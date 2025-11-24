# -*- coding:utf-8 -*-

{
    'name': 'Payroll',
    'category': 'Odex25-HR/Odex25-HR',
    'sequence': 38,
    'summary': 'Manage your employee payroll records',
    'description': "",
    'website': 'https://www.odoo.com/page/employees',
    'depends': [
        'hr_contract',
        'hr_holidays_community',
    ],
    'data': [
        'security/hr_payroll_security.xml',
        'security/ir.model.access.csv',
        'data/hr_payroll_sequence.xml',
        'wizard/hr_payroll_payslips_by_employees_views.xml',
        'wizard/hr_payroll_contribution_register_report_views.xml',
        'views/hr_contract_views.xml',
        'views/hr_salary_rule_views.xml',
        'views/hr_payslip_views.xml',
        'views/hr_employee_views.xml',
        'views/hr_payroll_report.xml',
        'views/res_config_settings_views.xml',
        'views/report_contribution_register_templates.xml',
        'views/report_payslip_templates.xml',
        'views/report_payslip_details_templates.xml',
        'data/hr_payroll_data.xml',
    ],
    'images': ['static/description/banner.png'],
    'application': True,
}
