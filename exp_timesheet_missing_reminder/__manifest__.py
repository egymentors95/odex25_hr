# -*- coding: utf-8 -*-
##############################################################################
#
#    Odex - Communications Management System.
#    Copyright (C) 2019 Expert Co. Ltd. (<http://exp-sa.com>).
#
##############################################################################
{
    'name': 'Timesheet Reminder Employees',
    'version': '1.0',
    'sequence': 10,
    'author': 'Expert Co. Ltd. ---sudan team',
    'category': 'Odex25-HR/Odex25-HR',
    'website': 'http://exp-sa.com',
    'summary': 'Timesheet Missing Reminder to Employees',
    'description': """
Timesheet Missing Reminder to Employees By sending Email per Day or Week and Month
========================================""",
    'website': 'http://www.exp-sa.com',
    'depends': ['mail', 'hr_timesheet_sheet', 'exp_official_mission', 'hr_holidays_public', 'attendances'],
    'data': [
        'data/corn_timesheet_reminder.xml',
        'data/timesheet_email_template.xml',
        'security/ir.model.access.csv',
        'views/extend_hr_employee.xml',
        'views/hr_employee_reminder_history.xml',
        'report/report_action.xml',
        'report/report_template.xml',
        'wizard/timesheet_reminder_report.xml',
        'views/wizard_approve.xml',
    ],
    'qweb': [
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
