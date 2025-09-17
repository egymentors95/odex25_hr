from odoo import fields, models, exceptions, api, _
from odoo.exceptions import UserError, ValidationError
from lxml import etree
import json


class EmployeePerformanceEvaluation(models.Model):
    _name = 'employee.performance.evaluation'
    _rec_name = 'employee_id'
    _inherit = ['mail.thread']
    _description = "Employee performance evaluation"
    recommendations = fields.Text(string='Recommendations', tracking=True, required=False)
    total = fields.Float(string='Total Mark', readonly=True, store=True, tracking=True, )
    mark_apprisal = fields.Float(string='Mark Apprisal', readonly=False, store=True, tracking=True,
                                 compute='total_mark')
    date_apprisal = fields.Date(default=lambda self: fields.Date.today(), string='Apprisal Date', tracking=True, )
    employee_id = fields.Many2one('hr.employee', string='Employee', tracking=True, required=True)
    manager_id = fields.Many2one('hr.employee', string='Employee m', readonly=False, tracking=True, required=False,
                                 default=lambda item: item.get_user_id())
    year_id = fields.Many2one(comodel_name='kpi.period', string='Year')
    period_goals_id = fields.Many2one('kpi.period.notes', force_save=1, string='Period', tracking=True, )
    department_id = fields.Many2one('hr.department', readonly=False, store=True, compute='compute_depart_job',
                                    tracking=True, string='Department')
    job_id = fields.Many2one('hr.job', force_save=1, readonly=True, store=True, string='Job Title',
                             related='employee_id.job_id', tracking=True, )
    state = fields.Selection([
        ('draft', 'Draft'), ('dir_manager', 'Wait Employee Accept'),
        ('wait_dir_manager', 'Wait Manager Accept'),
        ('wait_hr_manager', 'Wait HR Manager Accept'),
        ('approve', 'Accept'),
        ('refuse', 'Refused')
    ], string='State', tracking=True, default='draft')
    emp_goal_ids = fields.One2many(comodel_name='period.goals', inverse_name='employee_eval_id',
                                   string='Employee Goals', copy=True)

    @api.constrains('employee_id', 'year_id', 'period_goals_id')
    def check_unique_employee_year_period_goals(self):
        for record in self:
            if self.search_count([
                ('employee_id', '=', record.employee_id.id),
                ('year_id', '=', record.year_id.id),
                ('period_goals_id', '=', record.period_goals_id.id),
                ('id', '!=', record.id),
            ]) > 0:
                raise exceptions.ValidationError(
                    _("Employee Goals Apprisal must be unique per Employee, Year, and Period!"))

    def get_user_id(self):
        employee_id = self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)
        if employee_id:
            return employee_id.id
        else:
            return False

    @api.depends('employee_id')
    def compute_depart_job(self):
        for rec in self:
            if rec.employee_id:
                rec.department_id = rec.employee_id.department_id.id

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        res = super(EmployeePerformanceEvaluation, self).fields_view_get(view_id=view_id, view_type=view_type,
                                                                         toolbar=toolbar,
                                                                         submenu=submenu)
        doc = etree.XML(res['arch'])
        emp_group = self.env.ref('exp_hr_appraisal.group_appraisal_employee').id
        user_group = self.env.ref('exp_hr_appraisal.group_appraisal_user').id
        manager_group = self.env.ref('exp_hr_appraisal.group_appraisal_manager').id
        current_user_gids = self.env.user.groups_id.mapped('id')
        if ((emp_group in current_user_gids) and (user_group not in current_user_gids) and (
                manager_group not in current_user_gids)):
            if view_type == 'tree' or view_type == 'form':
                print('if node1.....')

                # if view_type == 'tree':
                for node in doc.xpath("//tree"):
                    print('if node.....')

                    node.set('create', 'false')
                    node.set('delete', 'false')
                    node.set('edit', 'false')
                for node in doc.xpath("//form"):
                    node.set('create', 'false')
                    node.set('delete', 'false')
                    node.set('edit', 'false')

            res['arch'] = etree.tostring(doc)
        elif ((user_group in current_user_gids or manager_group in current_user_gids)):
            if view_type == 'tree' or view_type == 'form':
                print('if node2.....')
                # if view_type == 'tree':
                for node in doc.xpath("//tree"):
                    print('for..node')
                    node.set('create', 'true')
                    node.set('edit', 'true')
                for node in doc.xpath("//form"):
                    node.set('create', 'true')
                    node.set('edit', 'true')
            res['arch'] = etree.tostring(doc)
        elif (
                user_group in current_user_gids and manager_group in current_user_gids and emp_group in current_user_gids):
            if view_type == 'tree' or view_type == 'form':
                print('if node3.....')
                # if view_type == 'tree':
                for node in doc.xpath("//tree"):
                    print('for..node')
                    node.set('create', 'true')
                    node.set('edit', 'true')
                for node in doc.xpath("//form"):
                    node.set('create', 'true')
                    node.set('edit', 'true')

            res['arch'] = etree.tostring(doc)
        return res

    def send(self):
        self.state = 'wait_dir_manager'

    def reset_draft(self):
        self.state = 'draft'

    def action_approval(self):
        if self.state == 'dir_manager':
            self.state = 'wait_dir_manager'
        elif self.state == 'wait_dir_manager':
            self.state = 'wait_hr_manager'
        else:
            self.state = 'approve'

    def action_refuse(self):
        self.state = 'refuse'

    def onchange_emp_goal_ids(self):
        goals_lines = [(5, 0, 0)]
        sum = 0
        period_goal_obj = self.env['period.goals'].search(
            [('period_goals_id', '=', self.period_goals_id.id), ('employee_id', '=', self.employee_id.id),
             ('year_id', '=', self.year_id.id)])
        self.emp_goal_ids = period_goal_obj.ids
        for rec in self.emp_goal_ids:
            sum = sum + ((rec.weight * rec.mark_evaluation) / 100)
        self.mark_apprisal = sum

    def unlink(self):
        for rec in self:
            if rec.state != 'draft':
                raise ValidationError(_("You can't delete a Goal apprisal not in Draft State , archive it instead."))
        return super().unlink()
