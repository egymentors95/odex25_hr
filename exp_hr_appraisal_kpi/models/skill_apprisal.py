from odoo import fields, models,exceptions, api,_
from odoo.exceptions import UserError,ValidationError
from lxml import etree
import json
class SkillAppraisal(models.Model):
    _name = 'skill.appraisal'
    _inherit = ['mail.thread']
    _rec_name = 'employee_id'
    _description = 'Skill Appraisal'
    name= fields.Char(string='Name',tracking=True,)
    recommendations= fields.Text(string='Recommendations',tracking=True,required=False)
    date_apprisal = fields.Date(default=lambda self: fields.Date.today(),string='Apprisal Date',tracking=True,)
    employee_id = fields.Many2one('hr.employee', string='Employee',tracking=True,required=True)
    manager_id = fields.Many2one('hr.employee', string='Manager',readonly=False,tracking=True,required=True,default=lambda item: item.get_user_id())
    period = fields.Many2one('kpi.period.notes',string='Period',tracking=True,)
    department_id = fields.Many2one('hr.department',readonly=True,store=True,compute='compute_depart_job', tracking=True,string='Department')
    job_id = fields.Many2one('hr.job',readonly=False,store=True, string='Job Title',tracking=True,)
    year_id = fields.Many2one(comodel_name='kpi.period',string='Year')

    @api.constrains('employee_id', 'year_id', 'period')
    def check_unique_employee_year_period_skills(self):
        for record in self:
            if self.search_count([
                ('employee_id', '=', record.employee_id.id),
                ('year_id', '=', record.year_id.id),
                ('period', '=', record.period.id),
                ('id', '!=', record.id),
            ]) > 0:
                raise exceptions.ValidationError(_("Employee Skill Apprisal must be unique per Employee, Year, and Period!"))


    state = fields.Selection([
        ('draft', 'Draft'),('dir_manager', 'Wait Employee Accept'),
        ('wait_dir_manager', 'Wait Manager Accept'),
        ('wait_hr_manager', 'Wait HR Manager Accept'),
        ('approve', 'Accept'),
        ('refuse', 'Refused')
    ], string='State',tracking=True,default='draft')
    avarage = fields.Float(string='Result',readonly=True,store=True,tracking=True,compute='calc_avg')
    items_ids = fields.One2many(comodel_name='skill.item.table',inverse_name='skill_appraisal_id',string='Items',copy=True)
    @api.model
    def fields_view_get(self, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        res = super(SkillAppraisal, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar,
                                                                         submenu=submenu)
        doc = etree.XML(res['arch'])
        emp_group = self.env.ref('exp_hr_appraisal.group_appraisal_employee').id
        user_group = self.env.ref('exp_hr_appraisal.group_appraisal_user').id
        manager_group = self.env.ref('exp_hr_appraisal.group_appraisal_manager').id
        current_user_gids = self.env.user.groups_id.mapped('id')
        if  ((emp_group in current_user_gids) and (user_group not in current_user_gids )and(manager_group not in current_user_gids)):
            if view_type=='tree' or view_type=='form':
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
        elif  ((user_group in current_user_gids or manager_group in current_user_gids)):
            if view_type=='tree' or view_type=='form':
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
        elif  (user_group in current_user_gids and  manager_group in current_user_gids and  emp_group in current_user_gids):
            if view_type=='tree' or view_type=='form':
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
                rec.job_id = rec.employee_id.job_id.id

    @api.depends('items_ids.mark')
    def calc_avg(self):
        sum = 0
        for rec in self.items_ids:
            if rec.mark and len(self.items_ids)!=0:
                sum = sum+int(rec.mark)
                self.avarage = sum/len(self.items_ids)
    def send(self):
        self.state = 'dir_manager'
    def reset_draft(self):
        self.state = 'draft'
    def action_approval(self):
        if self.state=='dir_manager':
            self.state='wait_dir_manager'
        elif self.state=='wait_dir_manager':
            self.state='wait_hr_manager'
        else:
            self.state='approve'

    def action_refuse(self):
        self.state = 'refuse'
        
    @api.onchange('job_id','employee_id')
    def onchange_emp(self):
        item_lines=[(5,0,0)]
        for line in  self.job_id.item_job_ids:
            line_item = {'item_id':line.item_id.id,'name':line.name,'level':line.level}
            item_lines.append((0,0,line_item))
            self.items_ids = item_lines
            
    def unlink(self):
        for rec in self:
            if rec.state != 'draft':
                raise ValidationError(_("You can't delete a Skill apprisal not in Draft State , archive it instead."))
        return super().unlink()
