from odoo import fields, models, api
class Skill(models.Model):
    _name = 'skill.skill'
    _inherit = ['mail.thread']

    name = fields.Char(string='Name', required=True,tracking=True,)
    description = fields.Text(string='Description',tracking=True,)
    items_ids = fields.One2many('skill.item', 'skill_id', string='Items',tracking=True,)
class SkillItems(models.Model):
    _name = 'skill.item'

    skill_id = fields.Many2one('skill.skill', string='Skill',ondelete='cascade')
    skill_appraisal_id  = fields.Many2one(comodel_name='skill.appraisal')
    name = fields.Char(string='Description')
    level = fields.Selection([('beginner', '1'),('intermediate', '2'),('advanced', '3')],string='Level', default='beginner')
    mark = fields.Selection([('1', '1'),('2', '2'),('3', '3'),('4', '4'),('5', '5')],string='Mark',Ccopy=False)
    mark_avg = fields.Float(string='Mark',Ccopy=False)
    item_id = fields.Many2one(comodel_name='item.item',string='Item')
    display_type = fields.Selection([
        ('line_section', "Section"),
        ('line_note', "Note")],default=False, help="Technical field for UX purpose.")
    employee_apprisal_id = fields.Many2one(
        comodel_name='hr.employee.appraisal')
    sequence = fields.Integer(string='Sequence', default=10)
    
class SkillItems(models.Model):
    _name = 'skill.item.table'

    skill_id = fields.Many2one('skill.skill', string='Skill')
    skill_appraisal_id  = fields.Many2one(comodel_name='skill.appraisal',ondelete='cascade')
    name = fields.Char(string='Description')
    level = fields.Selection([('beginner', '1'),('intermediate', '2'),('advanced', '3')],string='Level', default='beginner')
    mark = fields.Selection([('1', '1'),('2', '2'),('3', '3'),('4', '4'),('5', '5')],string='Mark',Ccopy=False)
    mark_avg = fields.Float(string='Mark',Ccopy=False)
    item_id = fields.Many2one(comodel_name='item.item',string='Item')
    employee_apprisal_id = fields.Many2one(
        
        comodel_name='hr.employee.appraisal')
class SkillItems(models.Model):
    _name = 'skill.item.employee.table'

    skill_id = fields.Many2one('skill.skill', string='Skill')
    skill_appraisal_id  = fields.Many2one(comodel_name='skill.appraisal',ondelete='cascade')
    name = fields.Char(string='Description')
    level = fields.Selection([('beginner', '1'),('intermediate', '2'),('advanced', '3')],string='Level', default='beginner')
    mark = fields.Selection([('1', '1'),('2', '2'),('3', '3'),('4', '4'),('5', '5')],string='Mark',Ccopy=False)
    mark_avg = fields.Float(string='Mark',Ccopy=False)
    item_id = fields.Many2one(comodel_name='item.item',string='Item')
    employee_apprisal_id = fields.Many2one(
        comodel_name='hr.employee.appraisal')


class SkillItem(models.Model):
    _name = 'item.item'
    name = fields.Char(string='Name')

class SkillJob(models.Model):
    _inherit = 'hr.job'
    item_job_ids = fields.Many2many('skill.item', 'merge_item_skill1_rel', 'merge1_id', 'item1_id', string='Skills')
    # appraisal_percentage_id = fields.Many2one(comodel_name='job.class.apprisal',string='Appraisal Percentage')
    appraisal_percentages_id = fields.Many2one(comodel_name='job.class.apprisal',string='Appraisal Percentage')
