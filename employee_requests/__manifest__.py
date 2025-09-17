{
    'name': 'Employee  Requests',
    'category': 'Odex25-HR/Odex25-HR',
    'summary': 'HR Management Employee Requests and self service',
    'version': '1.0',
    'sequence': 4,
    'website': 'http://exp-sa.com',
    'license': 'GPL-3',
    'author': 'Expert Co. Ltd.',

    'depends': ['base', 'account', 'hr_loans_salary_advance', 'exp_payroll_custom',
                'attendances'],

    'data': [
        'security/employee_requests_security.xml',
        'security/ir.model.access.csv',

        'data/hr_personal_permission_type_data.xml',

        'views/employee_effective_form.xml',
        'views/employee_overtime_request.xml',
        'views/hr_clearance_form.xml',
        'views/hr_personal_permission.xml',
        'views/hr_personal_permission_type_views.xml',
        'views/customize_hr_employee.xml',
        'views/employee_department_jobs_view.xml',

        'views/other_request.xml',
        'views/attendance_view.xml',

        'report/employee_clearance_report/employee_clearance_form_reports.xml',
        'report/employee_clearance_report/employee_clearance_form_template1.xml',
        'report/employee_clearance_report/employee_clearannce_detailes_template.xml',
        'report/clearance_employee_report_template.xml',
        'report/employee_department_jobs_template.xml',
        'report/employee_appointment_report_template.xml',
        'report/disclaimer_certificate.xml',
        'report/report_employee_identify.xml',
        'report/report_employee_identify_2.xml',
        'report/report_employee_identify_3.xml',
        'report/salary_confirmation.xml',

        # menu items
        'views/employee_request_menu.xml',
    ],
    # 'qweb': ['static/src/xml/base_template.xml'],
    'installable': True,
    'application': True,
}
