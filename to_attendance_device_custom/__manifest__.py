{
    'name': "Biometric Attendance Device custom",
    'name_vi_VN': "Tích hợp Máy chấm công Sinh trắc học",

    'summary': """ linking device checking with custom attendance""",

    'description': """ linking device checking with custom attendance """,

    'author': "EXP",
    'website': 'https://www.tvtmarine.com',
    'live_test_url': 'https://v12demo-int.erponline.vn',
    'support': 'support@ma.tvtmarine.com',

    'category': 'Odex25-HR/Odex25-HR',
    'version': '1.1.1',

    # any module necessary for this one to work correctly
    'depends': ['hr_attendance', 'attendances', 'to_attendance_device'],

    # always loaded
    'data': [
        'views/hr_attendance_views.xml',
    ],
    'images': ['static/description/main_screenshot.png'],
    'installable': True,
    'application': True,
    'auto_install': False,

}
