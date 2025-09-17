# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


# TimeSheet Reminder Wizard


class TimesheetReminderWizard(models.TransientModel):
	_name = 'timesheet.reminded'

	date_from = fields.Date()
	date_to = fields.Date()
	department_ids = fields.Many2many('hr.department')

	def print_report(self):
		if self.date_to <= self.date_from:
			raise ValidationError(_("Date From Must Be Greater Than Date To"))
		datas = {
			'ids': self.ids,
			'model': self._name,
			# 'form': {
			'department': self.department_ids.ids,
			'date_from': self.date_from,
			'date_to': self.date_to,
			# },
		}
		return self.env.ref('exp_timesheet_missing_reminder.action_report_reminded').report_action(self, data=datas)


class TimesheetReminderWizardAbstract(models.AbstractModel):
	_name = "report.exp_timesheet_missing_reminder.reminded_report_template"

	@api.model
	def _get_report_values(self, docids, data):
		departments = data['department']
		date_from = data['date_from']
		date_to = data['date_to']
		employees = self.env['hr.employee.history.reminder'].search([
			('date', '>=', date_from),
			('date', '<=', date_to),
			('is_completed_timesheet', '=', False)
		]).mapped('employee_id')
		reminders = self.env['hr.employee.history.reminder'].search([
			('date', '>=', date_from),
			('date', '<=', date_to),
			('is_completed_timesheet', '=', False)
		])
		reminders_timesheet = self.env['hr.employee.history.reminder'].search([
			('date', '>=', date_from),
			('date', '<=', date_to),
			('is_completed_timesheet', '=', True)
		])
		recordsets = []
		timesheet_record = []
		sheet_data = {}
		remove_hour = {}
		for employee in employees:
			recordsets.append(reminders.filtered(lambda r: r.employee_id.id == employee.id))
			timesheet_record.append(reminders_timesheet.filtered(lambda r: r.employee_id.id == employee.id).mapped('id'))
		for rec in timesheet_record:
			history_ids = self.env['hr.employee.history.reminder'].browse(rec)
			emp_id = history_ids.mapped('employee_id')
			enterd_hour = sum(history_ids.mapped('entered_hour'))
			sheet_data[emp_id.id] = enterd_hour
		data = []
		content = []
		for recordset in recordsets:
			mission_hour = 0.0
			permission_hour = 0.0
			mission_emp_id = ''
			for record in recordset:
				mission_emp_id = record.employee_id.id
				mission_id = self.env['hr.official.mission'].search(
					[('state', '=', 'approve'), ('date', '<=', record.date), ('date', '>=', record.date)])
				mission = mission_id.filtered(lambda r: r.mission_type.duration_type == 'hours')
				days_mission = mission_id.filtered(lambda r: r.mission_type.duration_type == 'days')
				mission_employee = mission.employee_ids.filtered(
					lambda r: r.employee_id.id == emp.id)
				if mission_employee:
					mission_hour += sum(mission_employee.mapped('hours'))
				permission_ids = self.env['hr.personal.permission'].search(
					[('employee_id', '=', record.employee_id.id), ('date', '=', record.date)])
				if permission_ids:
					permission_hour += sum(permission_ids.mapped('duration'))
				holiday_id = self.env['hr.holidays'].search(
					[('date_from', '<=', record.date), ('date_to', '>=', record.date),
					('state', '=', 'validate1'), ('type', '=', 'remove'), ('employee_id', '=', record.employee_id.id)])
				official_holiday_id = self.env['hr.holiday.officials'].search(
					[('date_from', '<=', record.date), ('date_to', '>=', record.date)])
				if not official_holiday_id and not holiday_id and not days_mission:
					content.append(record)
			total_hour = permission_hour+mission_hour
			if mission_emp_id:
				remove_hour[mission_emp_id] = total_hour
			data.append(content)
			content = []
		docs = []
		for reminder in data:
			history_ids = [re.id for re in reminder]
			history_ids = self.env['hr.employee.history.reminder'].browse(history_ids)
			miss_hour = sum(history_ids.mapped('miss_hour'))
			permission_mission_hour = remove_hour.get(reminder[0]['employee_id'].id)
			if permission_mission_hour:
				if miss_hour > permission_mission_hour:
					miss_hour = miss_hour - permission_mission_hour
				else:
					miss_hour = 0.0
			enterd_hour = sum(history_ids.mapped('entered_hour'))
			timesheet_entered = sheet_data.get(reminder[0]['employee_id'].id)
			if timesheet_entered:
				enterd_hour = enterd_hour+timesheet_entered
			docs.append({
				'employee_id': reminder[0]['employee_id'],
				'name': reminder[0]['employee_id'].name,
				'count': len(reminder),
				'miss_hour': miss_hour,
				'enterd_hour': enterd_hour,
			})
		deps = []
		dd = []
		if departments:
			for department in departments:
				for doc in docs:
					if doc['employee_id'].department_id.id == department:
						deps.append(doc)
				if len(deps) != 0:
					dd.append({'dep_name': self.env['hr.department'].search([('id', '=', department)]).name, 'data': deps})
				deps = []
		else:
			for doc in docs:
				deps.append(doc)
			dd.append({'dep_name': 'All', 'data': deps})
		docargs = {
			'doc_ids': [],
			'doc_model': ['hr.employee.history.reminder'],
			'date_from': date_from,
			'date_to': date_to,
			'departments': departments,
			'docs': dd,
		}
		return docargs
