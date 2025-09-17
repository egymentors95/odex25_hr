# -*- coding: utf-8 -*-
from odoo import api, fields, models, exceptions, _


class HrDepartment(models.Model):
    _inherit = "hr.department"

    dep_link = fields.Many2one(comodel_name="department.info")

    analytic_account_id = fields.Many2one('account.analytic.account',
                                          'Analytic Account')
    employee_ids = fields.One2many("hr.employee", "department_id", string="Employees",
                                   domain=[("state", "=", "open")], )

    job_ids = fields.Many2many("hr.job", string="Jobs")
    email_manager = fields.Char(string="Email Manager", related="manager_id.work_email")
    department_type = fields.Selection(selection=[('department', 'Department'), ('unit', 'Unit')])
    english_name = fields.Char(string='English Name')

    is_branch = fields.Boolean(string='Is Branch?',tracking=True)

    his_branch = fields.Boolean(compute='get_is_branch', default=False, store=True)
    branch_name = fields.Many2one('hr.department',domain=[("is_branch","=",True)])


    @api.depends('is_branch','parent_id')
    def get_is_branch(self):
        """To know which unit or department belongs to a specific branch"""
        for rec in self:
            if rec.is_branch == True or rec.parent_id.is_branch == True or rec.parent_id.parent_id.is_branch == True:
               rec.his_branch = True

    @api.model
    def create(self, vals):
        new_record = super(HrDepartment, self).create(vals)
        data = self.env["department.info"].create(
            {
                "department": new_record.name,
                "parent_dep": new_record.parent_id.id,
                "manager": new_record.manager_id.id,
            }
        )
        new_record.dep_link = data.id

        return new_record

    def write(self, vals):
        """If the manager name or parent name is changed, the manager name 
        will be changed for all employees has with this department"""
        for rec in self:
           super(HrDepartment, rec).write(vals)
           ## to remove followers ##
           followers = self.env['mail.followers'].search([('res_id', '=', rec.id),('res_model','=','hr.department')])
           followers.sudo().unlink()
           ### end #################
           if ('manager_id' or 'parent_id') in vals:
             departments = rec.env['hr.department'].search([('id', 'child_of', rec.id)]).ids
             employees = rec.env['hr.employee'].search([('department_id', 'in', departments)])
             for emp in employees:
                 emp._onchange_department()
           if rec.dep_link:
              rec.dep_link.department = rec.name
              rec.dep_link.parent_dep = rec.parent_id.id
              rec.dep_link.manager = rec.manager_id.id
           return True

    def unlink(self):
        for rec in self:
            if rec.dep_link:
                rec.dep_link.unlink()
            if rec.employee_ids:
                raise exceptions.Warning(_('You Can Not Delete Department %s Have Employees') % rec.name)
        super(HrDepartment, self).unlink()
        return True
