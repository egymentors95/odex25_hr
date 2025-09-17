# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api,exceptions,_


class Period(models.Model):
    _name = 'period.goals'
    
    period_goals_id = fields.Many2one('kpi.period.notes', domain=[('kpi_period_id','=',False)], string='Period Of Goals', tracking=True)
    employee_goals_id = fields.Many2one('years.employee.goals')
    target = fields.Float(string='Target', store=True)
    done = fields.Float(string='Done')
    kpi_id = fields.Many2one(comodel_name='kpi.item', string='KPI', related='employee_goals_id.kpi_id')
    employee_eval_id = fields.Many2one(comodel_name='employee.performance.evaluation', string='KPI')
    weight = fields.Float(string='Weight', related='employee_goals_id.weight')
    mark_evaluation = fields.Integer(string='Evaluation Mark', store=True, compute='_compute_mark_evaluation')
    year_id = fields.Many2one(comodel_name='kpi.period', related='employee_goals_id.year_id')
    employee_id = fields.Many2one(comodel_name='hr.employee', related='employee_goals_id.employee_id')
    
    @api.depends('done', 'target', 'kpi_id')
    def _compute_mark_evaluation(self):
        sum = 0
        for record in self:
            if record.done!=0.0 and record.target!=0.0 and record.kpi_id:
                done_percentage = (record.done / record.target) * 100
                marks = self.env['mark.mark'].search([('kip_id', '=', record.kpi_id.id)])
                if marks:
                    # Finding the closest mark where the done_percentage fits into the target-to range
                    closest_mark = min(
                        marks,
                        key=lambda x: abs(done_percentage - ((x.target + x.to) / 2))
                    )
                    if closest_mark.target <= done_percentage <= closest_mark.to:
                        record.mark_evaluation = int(closest_mark.choiec)
                    closest_mark = None
                    for mark in marks:
                        if mark.target <= done_percentage <= mark.to:
                            record.mark_evaluation = mark.choiec
                            break
            else:
                record.mark_evaluation = 0  # Or any other default value if fields are empty
            sum = sum+ ((record.weight*record.mark_evaluation)/100)
            record.employee_eval_id.mark_apprisal = sum

class YearEmployeeGoals(models.Model):
    _name = 'years.employee.goals'
    _inherit = ['mail.thread']
    _description = 'years employee goals'
    _rec_name = 'employee_id'
    
    employee_id = fields.Many2one('hr.employee', string='Employee',tracking=True,required=True)
    year_id = fields.Many2one(comodel_name='kpi.period',string='Year')
    category_id = fields.Many2one(comodel_name='kpi.category',string='Category')
    kpi_id = fields.Many2one(comodel_name='kpi.item',string='KPI',)
    method_of_calculate = fields.Selection(related='kpi_id.method_of_calculate')
    responsible_item_id = fields.Many2one(comodel_name='hr.employee',related='kpi_id.responsible_item_id',store=True,string='Responsible')
    user_id = fields.Many2one(comodel_name='res.users',related='responsible_item_id.user_id',store=True,string='Responsible')
    department_id = fields.Many2one('hr.department',readonly=True,store=True,compute='compute_depart_job', tracking=True,string='Department')
    job_id = fields.Many2one('hr.job',readonly=True,store=True,compute='compute_depart_job', string='Job Title',tracking=True,)
    year_target = fields.Float(string='Year Target')
    weight = fields.Float(string='Weight')
    goals_period_ids = fields.One2many(comodel_name='period.goals',inverse_name='employee_goals_id',string='Period',copy=False)
    done = fields.Float(string='Done',store=True,compute='total_done')
    state = fields.Selection([('draft', 'Draft'),('apprisal', 'Apprisal'),('close', 'Close')], string='State',tracking=True,default='draft')
    choiec = fields.Integer(string='Choiec',store=True,compute='compute_choice')
    employee_apprisal_id = fields.Many2one(comodel_name='hr.employee.appraisal')
    first_period_traget = fields.Float(compute='_compute_first_period_traget', string='First Period Traget',
                                    inverse='_inverse_first_period_traget')
    second_period_traget = fields.Float(compute='_compute_second_period_traget', string='Second Period Traget',
                                    inverse='_inverse_second_period_traget')
    third_period_traget = fields.Float(compute='_compute_third_period_traget', string='Third Period Traget',
                                    inverse='_inverse_third_period_traget')
    fourth_period_traget = fields.Float(compute='_compute_fourth_period_traget', string='Fourth Period Traget',
                                    inverse='_inverse_fourth_period_traget')
                                    
    def _compute_first_period_traget(self):
        for rec in self:
            rec.first_period_traget = 0.0
            first_period = rec.goals_period_ids.filtered(lambda period: period.period_goals_id.sequence == '1')
            if first_period:
               rec.first_period_traget = first_period.target

    def _inverse_first_period_traget(self):
        for rec in self:
            first_period = rec.goals_period_ids.filtered(lambda period: period.period_goals_id.sequence == '1')
            if first_period:
                first_period.sudo().target = rec.first_period_traget
            else:
                if rec.year_id:
                    first_period = rec.year_id.kpi_goals_periods_ids.filtered(lambda period: period.sequence == '1')
                    if first_period:
                        rec.goals_period_ids = [(0, 0, {'period_goals_id':first_period.id,'target':rec.first_period_traget})]
               
               
    def _compute_second_period_traget(self):
        for rec in self:
            rec.second_period_traget = 0.0
            second_period = rec.goals_period_ids.filtered(lambda period: period.period_goals_id.sequence == '2')
            if second_period:
               rec.second_period_traget = second_period.target
            
    def _inverse_second_period_traget(self):
        for rec in self:
            second_period = rec.goals_period_ids.filtered(lambda period: period.period_goals_id.sequence == '2')
            if second_period:
                second_period.sudo().target = rec.second_period_traget
            else:
                if rec.year_id:
                    second_period = rec.year_id.kpi_goals_periods_ids.filtered(lambda period: period.sequence == '2')
                    if second_period:
                        rec.goals_period_ids = [(0, 0, {'period_goals_id':second_period.id,'target':rec.second_period_traget})]

    def _compute_third_period_traget(self):
        for rec in self:
            rec.third_period_traget = 0.0
            third_period = rec.goals_period_ids.filtered(lambda period: period.period_goals_id.sequence == '3')
            if third_period:
               rec.third_period_traget = third_period.target
            
    def _inverse_third_period_traget(self):
        for rec in self:
            third_period = rec.goals_period_ids.filtered(lambda period: period.period_goals_id.sequence == '3')
            if third_period:
                third_period.sudo().target = rec.third_period_traget
            else:
                if rec.year_id:
                    third_period = rec.year_id.kpi_goals_periods_ids.filtered(lambda period: period.sequence == '3')
                    if third_period:
                        rec.goals_period_ids = [(0, 0, {'period_goals_id':third_period.id,'target':rec.third_period_traget})]
                                           
    def _compute_fourth_period_traget(self):
        for rec in self:
            rec.fourth_period_traget = 0.0
            fourth_period = rec.goals_period_ids.filtered(lambda period: period.period_goals_id.sequence == '4')
            if fourth_period:
               rec.fourth_period_traget = fourth_period.target
            
    def _inverse_fourth_period_traget(self):
        for rec in self:
            fourth_period = rec.goals_period_ids.filtered(lambda period: period.period_goals_id.sequence == '4')
            if fourth_period:
                fourth_period.sudo().target = rec.fourth_period_traget
            else:
                if rec.year_id:
                    fourth_period = rec.year_id.kpi_goals_periods_ids.filtered(lambda period: period.sequence == '4')
                    if fourth_period:
                        rec.goals_period_ids = [(0, 0, {'period_goals_id':fourth_period.id,'target':rec.fourth_period_traget})]                        
                    
    @api.model
    def search(self, args, offset=0, limit=None, order=None, count=False):
        #                 add domain filter to only show records related to login responsible_item_id employee
        if self.env.user.has_group("exp_hr_appraisal_kpi.group_appraisal_responsabil") and not self.env.user.has_group("exp_hr_appraisal.group_appraisal_manager") and not self.env.user.has_group("exp_hr_appraisal.group_appraisal_user") :
            args += [('user_id','=',self.env.user.id)]
        return super (YearEmployeeGoals,self).search(args,offset,limit,order,count)
        
    @api.depends('goals_period_ids.done','goals_period_ids.target','method_of_calculate')
    def total_done(self):
        for rec in self:
            if rec.method_of_calculate=='accumulative':
                sum=0
                for record in rec.goals_period_ids:
                    sum = sum+record.done

                rec.done = sum
            elif rec.method_of_calculate=='avrerage':
                sum=0
                for record in rec.goals_period_ids:
                    sum = (sum+record.done)
                rec.done = sum/len(rec.goals_period_ids)
            else:
                rec.done=0.0


    @api.depends('goals_period_ids.done','done','goals_period_ids.target','method_of_calculate')
    def compute_choice(self):
        for rec in self:
            choice = 0
            if rec.done!=0.0 and rec.year_target!=0.0 and rec.kpi_id:
                done_percentage = (rec.done / rec.year_target) * 100
                marks = self.env['mark.mark'].search([('kip_id', '=', rec.kpi_id.id),('target','<=',done_percentage),('to','>=',done_percentage)],limit=1)
                if marks:
                    choice = marks.choiec
            rec.choiec = int(choice)
            
    def apprisal(self):
        self.state='apprisal'
        
    def action_close(self):
        self.state='close'
        
    def action_set_to_dratt(self):
        self.state='draft'
        
    @api.constrains('employee_id', 'year_id', 'kpi_id')
    def check_unique_employee_year_period_goals(self):
        for record in self:
            if self.search_count([
                ('employee_id', '=', record.employee_id.id),
                ('year_id', '=', record.year_id.id),
                ('kpi_id', '=', record.kpi_id.id),
                ('id', '!=', record.id),
            ]) > 0:
                raise exceptions.ValidationError(_("Employee Goals  must be unique per Employee, Year, and kpi!"))
                
    @api.depends('employee_id')
    def compute_depart_job(self):
        for rec in self:
            if rec.employee_id:
                rec.department_id = rec.employee_id.department_id.id
                rec.job_id = rec.employee_id.job_id.id
                
    @api.onchange('year_id')
    def onchange_emp(self):
        goals_lines=[(5,0,0)]
        if self.year_id:
            for line in  self.year_id.kpi_goals_periods_ids:
                line_item = {'period_goals_id':line.id}
                goals_lines.append((0,0,line_item))
        self.goals_period_ids = goals_lines
