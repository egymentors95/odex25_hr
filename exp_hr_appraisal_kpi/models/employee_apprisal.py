from odoo import models, fields,_,api,exceptions

class EmployeeApprisal(models.Model):
    _inherit = 'hr.group.employee.appraisal'
    year_id = fields.Many2one(comodel_name='kpi.period',string='Year',required=True)
    appraisal_ids = fields.One2many('hr.employee.appraisal', 'employee_appraisal2')

    def gen_appraisal(self):
        for item in self:
            if item.employee_ids:
                appraisal_lines_list = []
                # Fill employee appraisal
                for element in item.employee_ids:
                    standard_appraisal_list, manager_appraisal_list = [], []
                    year_goal_obj = self.env['years.employee.goals'].search([('employee_id','=',element.id),('year_id','=',self.year_id.id)])
                    print('year = ',year_goal_obj)
                    goal_ids = year_goal_obj.ids if year_goal_obj else []
                    appraisal_line = {
                        'employee_id': element.id,
                        'manager_id': item.manager_id.id,
                        'year_id': item.year_id.id,
                        'department_id': item.department_id.id,
                        'job_id': element.job_id.id,
                        'appraisal_date': item.date,
                        'goal_ids':  [(6, 0, goal_ids)],
                    }
                    line_id = self.env['hr.employee.appraisal'].create(appraisal_line)
                    line_id.compute_apprisal()
                    appraisal_lines_list.append(line_id.id)

                item.appraisal_ids = self.env['hr.employee.appraisal'].browse(appraisal_lines_list)

            else:
                 raise exceptions.Warning(_('Please select at least one employee to make appraisal.'))
            item.state = 'gen_appraisal'
    def draft(self):
        print('draft ..............')
        # Delete all appraisals when re-draft
        if self.appraisal_ids:
            print('if appr line.............')
            for line in self.appraisal_ids:
                print('for..................')
                if line.state == 'draft':
                    print('state...........')
                    line.unlink()
                    self.state = 'draft'

                elif line.state == 'closed':
                    line.state = 'state_done'
                    self.state = 'start_appraisal'

                elif line.state == 'state_done':
                    self.state = 'start_appraisal'
        # Call the original draft method using super()

class EmployeeApprisal(models.Model):
    _inherit = 'hr.employee.appraisal'

    employee_appraisal2 = fields.Many2one('hr.group.employee.appraisal')  # Inverse field

    employee_id = fields.Many2one('hr.employee', string='Employee',tracking=True,required=True)
    manager_id = fields.Many2one('hr.employee', string='Manager',readonly=False,tracking=True,required=True,default=lambda item: item.get_user_id())
    year_id = fields.Many2one(comodel_name='kpi.period',string='Year',required=True)
    period_goals_id = fields.Many2one('kpi.period.notes',force_save=1,string='Period',tracking=True,)
    department_id = fields.Many2one('hr.department',required=True,readonly=False,store=True,compute='compute_depart_job', tracking=True,string='Department')
    job_id = fields.Many2one('hr.job',force_save=1,readonly=True,store=True, string='Job Title',related='employee_id.job_id',tracking=True,)

    goals_mark = fields.Float(store=True,string='Goals Apprisal Mark',readonly=True,tracking=True)
    skill_mark = fields.Float(store=True,string='Skills Apprisal Mark',readonly=True,tracking=True)
    total_score = fields.Float(string='Total Mark',store=True,readonly=True,compute='compute_total_score',tracking=True)
    apprisal_result = fields.Many2one('appraisal.result',string='Apprisal Result',store=True,tracking=True)

    notes= fields.Text(string='Notes',required=False)
    goal_ids = fields.One2many('years.employee.goals', 'employee_apprisal_id', string='Goals')
    skill_ids = fields.One2many('skill.item.employee.table', 'employee_apprisal_id', string='Skills')    
    
    @api.constrains('employee_id', 'year_id')
    def check_unique_employee_year_period_goals(self):
        for record in self:
            if self.search_count([
                ('employee_id', '=', record.employee_id.id),
                ('year_id', '=', record.year_id.id),
                ('id', '!=', record.id),
            ]) > 0:
                raise exceptions.ValidationError(_("Employee  Apprisal must be unique per Employee, Year, and Period!"))
    @api.depends('skill_mark','goals_mark',)
    def compute_total_score(self):
        appraisal_result_list = []
        for rec in self:
            if rec.skill_mark and rec.goals_mark and rec.job_id.appraisal_percentages_id.percentage_kpi>0.0 and rec.job_id.appraisal_percentages_id.percentage_skills>0.0:
                skill_mark_precentage = rec.skill_mark*rec.job_id.appraisal_percentages_id.percentage_skills
                goal_mark_precentage = rec.goals_mark*rec.job_id.appraisal_percentages_id.percentage_kpi

                rec.total_score =  (skill_mark_precentage+goal_mark_precentage)
            appraisal_result = self.env['appraisal.result'].search([
                    ('result_from', '<', rec.total_score),
                    ('result_to', '>=', rec.total_score)])
            if rec.total_score and len(appraisal_result) > 1:
                for line in appraisal_result:
                    appraisal_result_list.append(line.name)
                raise exceptions.Warning(
                    _('Please check appraisal result configuration , there is more than result for '
                      'percentage %s  are %s ') % (
                        round(rec.total_score, 2), appraisal_result_list))
            else:
                rec.appraisal_result = appraisal_result.id
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
    def compute_apprisal(self):
        year_goal_obj = self.env['years.employee.goals'].search([('employee_id','=',self.employee_id.id),('year_id','=',self.year_id.id)])
        if year_goal_obj:
            print('if goal...........')
            self.goal_ids = year_goal_obj.ids
        #
        sum2 = 0
        for rec in self.goal_ids:
            sum2 = sum2+ ((rec.weight*int(rec.choiec))/100)
        self.goals_mark = sum2
        #
        item_lines=[(5,0,0)]
        skill_apprisal = self.env['skill.appraisal'].search([('employee_id','=',self.employee_id.id),('year_id','=',self.year_id.id),('job_id','=',self.job_id.id)])
        dic_item = {}
        print('s a = ',skill_apprisal)
        for obj in skill_apprisal:
            for rec in obj.items_ids:
                if rec.mark and  rec.item_id:
                    if rec.item_id.name in dic_item:
                        dic_item[rec.item_id.name].append(rec.mark)
                    else:
                        dic_item.update({rec.item_id.name:[rec.mark]})
        print('dic_item =  ',dic_item)
        averages = {}
        for key, values in dic_item.items():
            # Convert values to integers and calculate sum
            total = sum(int(value) for value in values)
            # Calculate average
            avg = total / len(values)
            # Store the average in the dictionary
            averages[key] = avg

        if self.job_id:
            for line in  self.job_id.item_job_ids:

                line_item = {'item_id':line.item_id.id,'name':line.name,'level':line.level,}
                if line.item_id.name in averages:
                    line_item.update({'mark_avg':averages[line.item_id.name]})
                item_lines.append((0,0,line_item))
        self.skill_ids = item_lines
        # Calculate the average of averages
        if len(averages)!=0:
            average_of_averages = sum(averages.values()) / len(averages)
            self.skill_mark = average_of_averages
