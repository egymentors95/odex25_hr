# -*- coding: utf-8 -*-
##############################################################################
#
#    Expert Co. Ltd.
#    Copyright (C) 2018 (<http://www.exp-sa.com/>).
#
##############################################################################

from odoo import models, api
from odoo.http import request
from itertools import groupby
import time


class HrSalaryScaleLevel(models.Model):
    _inherit = 'hr.payroll.structure'

    @api.model
    def hierarchical_chart_details(self):
        structure = self.env['hr.payroll.structure'].sudo().search([])
        scale = structure.filtered(lambda r: r.type == 'scale' and not r.salary_scale_id)
        data = []
        for s in scale:
            scales = {}
            level_total = []
            scales['scale'] = s.name
            scales['scale_id'] = s.id
            levels = s.salary_scale_levels_ids.filtered(lambda r: r.salary_scale_id == s and r.type == 'level')
            for l in levels:
                level = {}
                groups = []
                level['level'] = l.name
                level['level_id'] = l.id
                group = structure.filtered(lambda r: r.salary_scale_level_id == l and r.type == 'group')
                for g in group:
                    gr = {}
                    gr['group'] = g.name
                    gr['group_id'] = g.id
                    degree = []
                    degrees = structure.filtered(lambda r: r.salary_scale_group_id == g and r.type == 'degree')
                    for d in degrees:
                        if d:
                            degree.append([d.id, d.name, d.base_salary])
                    gr['degree'] = degree if degree else []
                    groups.append(gr)
                level['group'] = groups
                level_total.append(level)
            scales['data'] = level_total
            data.append(scales)
        return ['name'], data, False


class Dep(models.Model):
    _inherit = 'hr.department'

    @api.model
    def hierarchical_chart_details(self):
        departments = self.sudo().search([])
        departments = departments.read([])

        return ['name'], departments, True


class hierarchical_chart_model(models.Model):
    _name = 'hr_hierarchical_chart_model'

    @api.model
    def hierarchical_chart_details(self, model, res_id=False):
        """
        get the list of dicts in sorted oreder to fit in hierarchy view
        """

        keys, data, department = self.env[model].hierarchical_chart_details()
        model_id = self.env['ir.model'].search([('model', '=', model)])
        fields = self.env['ir.model.fields'].search(
            [('model_id', 'in', model_id.ids)])
        fields = fields.read(['name', 'field_description', 'ttype'])

        fields_names = {x['name']: x['field_description'] for x in fields}
        fields_types = {x['name']: x['ttype'] for x in fields}
        all_data = []
        scale = False
        groupby_dicts = {}
        if department:
            for rec in data:
                key = rec['parent_id'] and rec['parent_id'][0] or False
                value = rec
                if key:
                    groupby_dicts[key] = groupby_dicts.get(key, [])
                    groupby_dicts[key].append(value)
                elif not key:
                    all_data.append(value)

            # store the parents we have already delt with
            computed_parents = [False]

            while len(computed_parents) != len(groupby_dicts.keys()) + 1:
                for k in groupby_dicts:
                    if k in computed_parents:
                        continue
                    v = list(groupby_dicts[k])
                    if all_data:
                        for rec in all_data:
                            if rec['id'] == k:
                                all_data = all_data[:all_data.index(
                                    rec)] + list(v)[::-1] + \
                                           all_data[all_data.index(rec):]

                                computed_parents.append(k)

                    if not all_data:
                        all_data = list(v)

            all_data = all_data[::-1]

        else:
            all_data = data
        return {'cols': keys, 'fields_names': fields_names,
                'fields_types': fields_types, 'all_data': all_data}
