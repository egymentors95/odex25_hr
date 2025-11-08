# -*- coding: utf-8 -*-

from datetime import datetime, timedelta

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from .helper import httpHelper, is_valid_port, is_valid_ip, ParsedRequest


class SystemAttendance(models.Model):
    _name = 'finger.system_attendance'

    punch_state = fields.Char("Punch state", readonly=True)
    area_alias = fields.Char("Area", readonly=True)
    crc = fields.Char("CRC", readonly=True)
    verify_type = fields.Integer("Verify type", readonly=True)
    emp = fields.Integer("Empolyee code", readonly=True)
    is_attendance = fields.Integer("Is attendance", readonly=True)
    attendance_id = fields.Integer("Attendance id", readonly=True)
    upload_time = fields.Datetime(string='Upload time', readonly=True)
    punch_time = fields.Datetime(string="Punch time", readonly=True)
    emp_code = fields.Many2one('finger.employee.employee', string='System Employee Name', readonly=True)
    terminal_id = fields.Many2one('finger.terminal', string='Terminal', readonly=True)
    server_id = fields.Many2one('finger.biotime_api', string='server', readonly=True)
    hr_comployee_id = fields.Many2one('hr.employee', string='Empolyee Name', readonly=True)
    state = fields.Selection(
        [('draft', _('Draft')),
         ('confirmed', _('Confirmed'))], default="draft", readonly=True)


class SystemTerminal(models.Model):
    _name = 'finger.terminal'

    name = fields.Char("Terminal name")
    terminal_id = fields.Integer("Termainl id")
    sn = fields.Char("SN")
    area_name = fields.Char("Area name")
    last_activity = fields.Char("Last activity")
    ip_address = fields.Char("ip address")
    alias = fields.Char("Alias")
    server_id = fields.Many2one('finger.biotime_api', string='server')


class SystemEmployee(models.Model):
    _name = 'finger.employee.employee'

    name = fields.Char("System Employee Name")
    code = fields.Char("System employee Code")
    emp_system_id = fields.Integer("Employee id")
    email = fields.Char("email")
    department_id = fields.Many2one('finger.employee.department', string='System Deparment')
    position_id = fields.Many2one('finger.employee.position', string='System Position')
    hr_employee = fields.Many2one('hr.employee', string='Empolyee Name')
    server_id = fields.Many2one('finger.biotime_api', string='Hr empolyee')


class SystemEmployeePosition(models.Model):
    _name = 'finger.employee.position'

    name = fields.Char("Name")
    code = fields.Char("Code")
    position_id = fields.Integer("Position id")
    server_id = fields.Many2one('finger.biotime_api', string='server')


class SystemArea(models.Model):
    _name = 'finger.area'

    name = fields.Char("Name")
    code = fields.Char("Code")
    area_id = fields.Integer("Area id")
    server_id = fields.Many2one('finger.biotime_api', string='server')


class SystemDepartments(models.Model):
    _name = 'finger.employee.department'

    name = fields.Char("Name")
    code = fields.Char("Code")
    department_id = fields.Integer("Department id")
    server_id = fields.Many2one('finger.biotime_api', string='server')


class BiotimeAPI(models.Model):
    _name = 'finger.biotime_api'

    name = fields.Char()
    serverUrl = fields.Char(string="IP / Domain Name")
    port = fields.Char(default="80")
    username = fields.Char()
    password = fields.Char()
    token = fields.Char()
    description = fields.Text()
    loaded_employees = fields.Boolean(default=False)

    terminals_ids = fields.One2many(
        string='terminals',
        comodel_name='finger.terminal',
        inverse_name='server_id',
    )

    attendance_ids = fields.One2many(
        string='Attendances',
        comodel_name='finger.system_attendance',
        inverse_name='server_id',
    )
    employee_ids = fields.One2many(
        string='Employees',
        comodel_name='finger.employee.employee',
        inverse_name='server_id',
    )

    state = fields.Selection(
        [('authentic', _('Authentic')),
         ('unauthentic', _('Not authentic'))], default="unauthentic")

    @api.model
    def _calc_urls(self):
        serverIP = self.serverUrl + ":" + self.port
        loginUrl = serverIP + "/jwt-api-token-auth/"
        refreshUrl = serverIP + "/jwt-api-token-refresh/"
        employeeUrl = serverIP + "/personnel/api/employee/"
        departmentsUrl = serverIP + "/personnel/api/departments/"
        terminalsUrl = serverIP + "/iclock/api/terminals/"
        areasUrl = serverIP + "/personnel/api/areas/"
        positionsUrl = serverIP + "/personnel/api/positions/"
        transctionsUrl = serverIP + "/iclock/api/transactions/"
        return loginUrl, refreshUrl, employeeUrl, departmentsUrl, positionsUrl, is_valid_ip, areasUrl, terminalsUrl, ParsedRequest, transctionsUrl

    @api.depends('token')
    def depends_token(self):
        for srv in self:
            if srv.token:
                srv.state = 'authentic'

    @api.onchange('token')
    def onchange_token(self):
        for srv in self:
            if srv.token:
                srv.state = 'authentic'

    @api.constrains('serverUrl')
    def check_is_valid_ip(self):
        for srv in self:
            if not is_valid_ip(srv.serverUrl):
                raise ValidationError(_("Invalid server url"))

    @api.constrains('port')
    def check_is_valid_ip(self):
        for srv in self:
            if not is_valid_port(srv.port):
                raise ValidationError(_("Invalid port number"))

    def process_attendance_scheduler(self):
        for tx in self.attendance_ids:
            print(tx)

    def login(self):
        res = httpHelper.login(self.username, self.password)

        if res.status_code == 200:
            data = res.json()
            token = data.get('token', False)
            if token:
                self.token = token
                self.state = 'authentic'
        else:
            data = res.json()
            err = ""
            for key in data:
                err += ' '.join(data[key])
            raise ValidationError(err)

    def refresh(self):
        res = httpHelper.refresh(self.token)
        if res.status_code == 200:
            data = res.json()
            token = data.get('token', False)
            if token:
                self.token = token
        else:
            data = res.json()
            err = ""
            for key in data:
                err += ' '.join(data[key])
            raise ValidationError(err)

    def logout(self):
        self.token = False
        self.state = 'unauthentic'

    def to_attendace(self):
        Attend = self.env['finger.system_attendance']
        attendance = self.env['attendance.attendance']
        HR = self.env['hr.employee']
        attens = Attend.search([('server_id', '=', self.id), ('state', '=', 'draft')])
        for tx in attens:
            if tx.emp_code and tx.emp_code.hr_employee:
                attendance.create({
                    'employee_id': tx.emp_code.hr_employee.id,
                    'name': tx.punch_time,
                    'action': 'sign_in' if tx.punch_state in ["0", "2", "4"] else 'sign_out',
                    'action_date': tx.punch_time,
                })
                tx.write({
                    'state': 'confirmed'
                })

    def sync_employees(self):
        if not self.token:
            self.refresh()
        res = httpHelper.fetch_employees({}, self.token)
        _, _, employeeUrl, _, _, _, _, _, _, _ = self._calc_urls()
        if res.status_code == 200:
            da = ParsedRequest(res.content)
            self.create_employee(da.data)
            next = 2
            while da.next:
                r = httpHelper.fetch_employees(
                    {}, self.token, employeeUrl + "?page=" + str(next))
                if r.status_code == 200:
                    da = ParsedRequest(r.content)
                    self.create_employee(da.data)
                else:
                    da.next = None
                next = next + 1
            self.loaded_employees = True
        else:
            self.errorHandler(res)

    def errorHandler(self, res):
        if res.status_code == 401:
            self.logout()
        else:
            data = res.json()
            err = ""
            for key in data:
                err += ' '.join(data[key])
            raise ValidationError(err)

    def sync_terminals(self):
        if not self.token:
            self.refresh()
        res = httpHelper.fetch_terminals({}, self.token)
        _, _, _, _, _, _, _, terminalsUrl, _, _ = self._calc_urls()
        if res.status_code == 200:
            da = ParsedRequest(res.content)
            self.create_termainl(da.data)
            next = 2
            while da.next:
                r = httpHelper.fetch_terminals(
                    {}, self.token, terminalsUrl + "?page=" + str(next))
                if r.status_code == 200:
                    da = ParsedRequest(r.content)
                    self.create_termainl(da.data)
                else:
                    da.next = None
                next = next + 1
        else:
            self.errorHandler(res)

    def sync_departments(self):
        if not self.token:
            self.refresh()
        res = httpHelper.fetch_departments({}, self.token)
        _, _, _, departmentsUrl, _, _, _, _, _, _ = self._calc_urls()

        if res.status_code == 200:
            da = ParsedRequest(res.content)
            self.create_department(da.data)
            next = 2
            while da.next:
                r = httpHelper.fetch_departments(
                    {}, self.token, departmentsUrl + "?page=" + str(next))
                if r.status_code == 200:
                    da = ParsedRequest(r.content)
                    self.create_department(da.data)
                else:
                    da.next = None
                next = next + 1
        else:
            self.errorHandler(res)

    def sync_areas(self):
        if not self.token:
            self.refresh()
        res = httpHelper.fetch_areas({}, self.token)
        _, _, _, _, _, _, areasUrl, _, _, _ = self._calc_urls()
        try:
            if res.status_code == 200:
                da = ParsedRequest(res.content)
                self.create_area(da.data)
                next = 2
                while da.next:
                    res = httpHelper.fetch_areas(
                        {}, self.token, url=areasUrl + "?page=" + str(next))
                    if res.status_code == 200:
                        da = ParsedRequest(res.content)
                        self.create_area(da.data)
                    else:
                        da.next = None
                    next = next + 1
            else:
                self.errorHandler(res)
        except Exception as e:
            ValidationError(str(e))

    def sync_positions(self):
        if not self.token:
            self.refresh()
        res = httpHelper.fetch_positions({}, self.token)
        _, _, _, _, positionsUrl, _, _, _, _, _ = self._calc_urls()

        try:
            if res.status_code == 200:
                da = ParsedRequest(res.content)
                self.create_position(da.data)
                next = 2
                while da.next:
                    res = httpHelper.fetch_positions(
                        {}, self.token, url=positionsUrl + "?page=" + str(next))
                    if res.status_code == 200:
                        da = ParsedRequest(res.content)
                        self.create_position(da.data)
                    else:
                        da.next = None
                    next = next + 1
            else:
                self.errorHandler(res)
        except Exception as e:
            ValidationError(str(e))

    def sync_employee_attenence(self, url):
        if not self.token:
            self.refresh()
        res = httpHelper.fetch_empl_transctions({}, self.token, url)

        try:
            if res.status_code == 200:
                da = ParsedRequest(res.content)
                next = 2
                self.create_attendance(da.data)
                while da.next:
                    # res = httpHelper.fetch_empl_transctions(
                    # {}, self.token, url=transctionsUrl + "?page=" + str(next))
                    res = httpHelper.fetch_empl_transctions({}, self.token, da.next)
                    if res.status_code == 200:
                        da = ParsedRequest(res.content)
                        self.create_attendance(da.data)
                    else:
                        da.next = None
                    next = next + 1
                    # print('&&&&&&&&&&&&&&&&&&&&& pages &&&&&&&&&&&&&&&&&&&',da.next)
            else:
                self.errorHandler(res)
                if res.status_code == 401:
                    self.refresh()
                    if self.token:
                        self.sync_employee_attenence(url)
        except Exception as e:
            ValidationError(str(e))

    def sync_attenence(self):
        self.login()
        if not self.token:
            self.refresh()
        res = httpHelper.fetch_empl_transctions({}, self.token)
        if not self.loaded_employees:
            self.sync_employees()
        _, _, _, _, _, _, _, _, _, transctionsUrl = self._calc_urls()
        try:
            if res.status_code == 200:
                da = ParsedRequest(res.content)
                next = 2
                self.create_attendance(da.data)
                while da.next:
                    res = httpHelper.fetch_empl_transctions(
                        {}, self.token, url=transctionsUrl + "?page=" + str(next))
                    if res.status_code == 200:
                        da = ParsedRequest(res.content)
                        self.create_attendance(da.data)
                    else:
                        da.next = None
                    next = next + 1
                    # print('&&&&&&&&&&&&&&&&&&&&& pages 222 &&&&&&&&&&&&&&&&&&&',next)
            else:
                self.errorHandler(res)
        except Exception as e:
            ValidationError(str(e))

    def create_termainl(self, termainls):
        TerminalsModel = self.env['finger.terminal']
        for tx in termainls:
            tirm = TerminalsModel.search([('terminal_id', '=', tx['id'])])
            data = {
                'terminal_id': tx['id'],
                'name': tx['terminal_name'],
                'sn': tx['sn'],
                'area_name': tx['area_name'],
                'last_activity': tx['last_activity'],
                'ip_address': tx['ip_address'],
                'alias': tx['alias'],
                'server_id': self.id
            }
            if not tirm:
                TerminalsModel.create(data)
            else:
                tirm.update(data)

    def create_area(self, areas):
        TerminalsModel = self.env['finger.area']
        for tx in areas:
            tirm = TerminalsModel.search([('area_id', '=', tx['id'])])
            data = {
                'area_id': tx['id'],
                'name': tx['area_name'],
                'code': tx['area_code'],
                'server_id': self.id
            }
            if not tirm:
                TerminalsModel.create(data)
            else:
                tirm.update(data)

    def create_department(self, departments):
        TerminalsModel = self.env['finger.employee.department']
        for tx in departments:
            tirm = TerminalsModel.search([('department_id', '=', tx['id'])])
            data = {
                'department_id': tx['id'],
                'name': tx['dept_name'],
                'code': tx['dept_code'],
                'server_id': self.id
            }
            if not tirm:
                TerminalsModel.create(data)
            else:
                tirm.update(data)

    def create_position(self, positions):
        PostionModel = self.env['finger.employee.position']
        for tx in positions:
            tirm = PostionModel.search([('position_id', '=', tx['id'])])
            data = {
                'position_id': tx['id'],
                'name': tx['position_name'],
                'code': tx['position_code'],
                'server_id': self.id
            }
            if not tirm:
                PostionModel.create(data)
            else:
                tirm.update(data)

    def create_employee(self, employees):
        EmployeeModel = self.env['finger.employee.employee']
        DepartmentModel = self.env['finger.employee.department']
        PositionModel = self.env['finger.employee.position']
        HR = self.env['hr.employee']

        for tx in employees:
            tirm = EmployeeModel.search([('emp_system_id', '=', tx['id'])])
            dep = None
            pos = None
            hrEmp = None
            if tx['position']:
                pos = PositionModel.search([('position_id', '=', tx['position'])], limit=1)

            if tx['department']:
                dep = DepartmentModel.search([('department_id', '=', tx['department'])], limit=1)

            if tx['emp_code']:
                hrEmp = HR.search([('emp_no', '=', tx['emp_code'])])

            data = {
                'emp_system_id': tx['id'],
                'name': tx['first_name'],
                'code': tx['emp_code'],
                'department_id': dep.id if dep else False,
                'position_id': pos.id if pos else False,
                'hr_employee': hrEmp.id if hrEmp else False,
                'server_id': self.id,
            }

            if not tirm and hrEmp:
                EmployeeModel.create(data)
            elif hrEmp and tirm:
                tirm.update(data)

    def create_attendance(self, attendaces):
        AttendanceModel = self.env['finger.system_attendance']
        TerminalModel = self.env['finger.terminal']
        EmployeeModel = self.env['finger.employee.employee']
        for tx in attendaces:
            tirm = AttendanceModel.search([('attendance_id', '=', tx['id'])])
            empe = None
            pos = None
            # "2020-08-09 10:23:20"
            new_punch_time = datetime.strptime(tx['punch_time'], "%Y-%m-%d %H:%M:%S") + timedelta(hours=-3)
            new_upload_time = datetime.strptime(tx['upload_time'], "%Y-%m-%d %H:%M:%S") + timedelta(hours=-3)
            # datetime_format = "%Y-%m-%d %H:%M:%S"

            if tx['emp_code']:
                empe = EmployeeModel.search([('code', '=', tx['emp_code'])], limit=1)

            if tx['terminal_alias']:
                dep = TerminalModel.search([('sn', '=', tx['terminal_sn'])], limit=1)
            data = {
                'attendance_id': tx['id'],
                'punch_state': tx['punch_state'],
                'area_alias': tx['area_alias'],
                # 'crc': tx['crc'],
                'crc': tx['emp'],
                'verify_type': tx['verify_type'],
                # 'is_attendance': tx['is_attendance'],
                'upload_time': new_upload_time,
                'punch_time': new_punch_time,
                'emp_code': empe.id if empe else None,
                'terminal_id': dep.id if dep else None,
                'server_id': self.id,
                'hr_comployee_id': empe.hr_employee.id if empe and empe.hr_employee else None,
                'emp': empe.code if empe else None
            }

            if not tirm and empe:
                # print('9999999999999999999999999999999999999999999999999',tirm)
                AttendanceModel.create(data)
            elif empe and tirm:
                tirm.update(data)

    def action_attendance_download(self):
        now = datetime.now()
        yesterday = datetime.now() - timedelta(hours=48)
        now = now.strftime("%Y-%m-%d %H:%M:%S")
        yesterday = yesterday.strftime("%Y-%m-%d %H:%M:%S")
        _, _, _, _, _, _, _, _, _, transctionsUrl = self._calc_urls()
        for r in self:
            for xm in r.employee_ids:
                # url = "{}?start_time={}&end_time={}&emp_code={}".format(transctionsUrl,yesterday,now, xm.code )
                url = "{}?punch_time={}&punch_time={}&emp_code={}".format(transctionsUrl, yesterday, now, xm.code)
                # print('################################# New Employee',url)
                r.sync_employee_attenence(url)