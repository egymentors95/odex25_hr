# -*- coding: utf-8 -*-
{
    "name": "Attendance Custom Widget",
    "version": "14.0",
    "summary": "",
    "author": "ronozoro",
    "category": "Extra",
    'depends': ['base', 'hr_attendance','attendances'],
    'data': [
        "views/assets.xml",
    ],

    'qweb': [
        "static/xml/attendance.xml",
    ],
    "installable": True,
    "auto_install": False,

}
