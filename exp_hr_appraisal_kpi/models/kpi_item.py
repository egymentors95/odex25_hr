from odoo import fields, models, api,_
from lxml import etree
import json
from odoo.exceptions import MissingError, UserError, ValidationError, AccessError

class KPICategory(models.Model):
    _inherit = 'kpi.category'
    @api.model
    def fields_view_get(self, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        res = super(KPICategory, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar,
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
class KPIitem(models.Model):
    _inherit = 'kpi.item'
    department_item_id = fields.Many2one(comodel_name='hr.department',string='Department')
    responsible_item_id = fields.Many2one(comodel_name='hr.employee',string='Responsible')
    mark_ids = fields.One2many(comodel_name='mark.mark',inverse_name='kip_id')
    method_of_calculate = fields.Selection(
        string='Method Of Calculate',
        selection=[('accumulative', 'Accumulative'),
                   ('avrerage', 'Average'),('undefined', 'Undefined'),],
        required=False,default='accumulative')

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        res = super(KPIitem, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar,
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

    @api.onchange('department_item_id')
    def onchange_responsible(self):
        domain = []
        if self.department_item_id:
            # Define your dynamic domain based on field1's value
            domain = [('department_id', '=', self.department_item_id.id)]
        return {'domain': {'responsible_item_id': domain}}


class Marks(models.Model):
    _name = 'mark.mark'
    choiec = fields.Selection(string='Choiec',selection=[('1', '1'), ('2', '2'), ('3', '3'), ('4', '4'),('5','5'),])
    target = fields.Float(string='From(Done)',)
    to = fields.Float(string='To(Target)',)
    kip_id = fields.Many2one(comodel_name='kpi.item',string='Kip_id')

    @api.constrains('target', 'to', 'kip_id')
    def _check_target_to_values(self):
        for record in self:
            if record.to <= record.target:
                raise ValidationError(_('The To value must be greater than the From value.'))

            # Get previous marks for the same KPI sorted by target
            # previous_marks = self.env['mark.mark'].search([('kip_id', '=', record.kip_id.id), ('id', '!=', record.id)], order='target')
            # for prev_mark in previous_marks:
            #     if record.target <= prev_mark.to:
            #         raise ValidationError(_('The From value must be greater than the previous To value.'))
