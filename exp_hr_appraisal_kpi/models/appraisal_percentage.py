from odoo import fields, models, api,_
from odoo.exceptions import ValidationError

class AppraisalPercentage(models.Model):
    _name = 'job.class.apprisal'
    _description = 'Appraisal Percentage'
    name = fields.Char(string='Name')
    percentage_kpi = fields.Float(string="Percentage of indicator Appraisal%",)
    percentage_skills = fields.Float(string="Percentage of Skills Appraisal%",)
    job_ids = fields.Many2many(
        comodel_name='hr.job',
        string='Jobs')

    # Constraint to ensure total percentage is 100
    @api.constrains('percentage_kpi', 'percentage_skills')
    def _check_percentage_total(self):
        for record in self:
            total_percentage = record.percentage_kpi + record.percentage_skills
            if total_percentage != 1:
                raise ValidationError(_("Total percentage should be 100."))
        if self.job_ids:
            for rec in self.job_ids:
                rec.appraisal_percentages_id = self.id