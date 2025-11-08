# -*- coding: utf-8 -*-
from odoo import http

# class ToAttendanceSystem(http.Controller):
#     @http.route('/to_attendance_system/to_attendance_system/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/to_attendance_system/to_attendance_system/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('to_attendance_system.listing', {
#             'root': '/to_attendance_system/to_attendance_system',
#             'objects': http.request.env['to_attendance_system.to_attendance_system'].search([]),
#         })

#     @http.route('/to_attendance_system/to_attendance_system/objects/<model("to_attendance_system.to_attendance_system"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('to_attendance_system.object', {
#             'object': obj
#         })
