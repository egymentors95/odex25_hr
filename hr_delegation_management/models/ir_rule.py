from odoo import models, fields, api, _, tools, SUPERUSER_ID
from datetime import date
from odoo.tools.safe_eval import safe_eval
from odoo.osv import expression
from odoo.tools import config
import logging

_logger = logging.getLogger(__name__)


class IrRuleInherit(models.Model):
    _inherit = 'ir.rule'

    @api.model
    def _compute_domain(self, model_name, mode="read"):
        if self.env.su:
            return self.browse(())

        user_id = self.env.user
        today = date.today()
        if user_id:
            employee_id = user_id.employee_id.id or False
            has_delegation = False
            delegation_ids = self.env['authority.delegation']
            domain = []
            if employee_id:
                delegation_ids = self.env['authority.delegation'].sudo().search([
                    ('state', '=', 'approved'),
                    ('date_from', '<=', str(today)),
                    ('date_to', '>=', str(today)),
                    ('delegate_id', '=', employee_id)
                ])
            for delegation_id in delegation_ids:
                    has_delegation = True
                    if delegation_id.delegation_line_ids and model_name in delegation_id.delegation_line_ids. \
                            mapped('model_configuration_id').mapped('model_id').mapped('model') \
                            and delegation_id.delegator_id and delegation_id.delegator_id.user_id:
                        user_id = delegation_id.delegator_id.user_id
                        action_domain = delegation_id.delegation_line_ids.mapped('action_id') \
                            .filtered(lambda act: act.res_model == model_name).domain
                        if action_domain:
                            domain.append(safe_eval(action_domain))
                            if mode not in self._MODES:
                                raise ValueError('Invalid mode: %r' % (mode,))
                            if self._uid == SUPERUSER_ID:
                                return None
            if mode not in self._MODES:
                raise ValueError('Invalid mode: %r' % (mode,))

            rules = self._get_rules(model_name, mode=mode)
            if not rules:
                return

            eval_context = self._eval_context()
            if has_delegation and user_id == self.env.user:
                user_groups = self.env['res.groups'].browse([group_id.id for group_id in
                                                                 delegation_ids.mapped('user_group_ids')])
            else:
                user_groups = user_id.groups_id
            global_domains = []  # list of domains
            group_domains = domain  # list of domains
            for rule in rules.sudo():
                    # evaluate the domain for the current user
                eval_context['user'] = user_id
                dom = safe_eval(rule.domain_force, eval_context) if rule.domain_force else []
                dom = expression.normalize_domain(dom)
                if not rule.groups:
                    global_domains.append(dom)
                elif rule.groups & user_groups:
                    group_domains.append(dom)

                # combine global domains and group domains
                if not group_domains:
                    return expression.AND(global_domains)
            return expression.AND(global_domains + [expression.OR(group_domains)])



    # def _compute_domain(self, model_name, mode="read"):
    #     user_id = self.env.user
    #     today = date.today()
    #     if user_id:
    #         employee_id = user_id.employee_id.id or False
    #         has_delegation = False
    #         delegation_ids = self.env['authority.delegation']
    #         domain = []
    #         if employee_id:
    #             delegation_ids = self.env['authority.delegation'].sudo().search([
    #                 ('state', '=', 'approved'),
    #                 ('date_from', '<=', str(today)),
    #                 ('date_to', '>=', str(today)),
    #                 ('delegate_id', '=', employee_id)
    #             ])
    #             for delegation_id in delegation_ids:
    #                 has_delegation = True
    #                 if delegation_id.delegation_line_ids and model_name in delegation_id.delegation_line_ids. \
    #                         mapped('model_configuration_id').mapped('model_id').mapped('model') \
    #                         and delegation_id.delegator_id and delegation_id.delegator_id.user_id:
    #                     user_id = delegation_id.delegator_id.user_id
    #                     action_domain = delegation_id.delegation_line_ids.mapped('action_id') \
    #                         .filtered(lambda act: act.res_model == model_name).domain
    #                     if action_domain:
    #                         domain.append(safe_eval(action_domain))
    #         rules = self._get_rules(model_name, mode=mode)
    #         if not rules:
    #             return
    #
    #         # browse user and rules as SUPERUSER_ID to avoid access errors!
    #         eval_context = self._eval_context()
    #         if has_delegation and user_id == self.env.user:
    #             user_groups = self.env['res.groups'].browse([group_id.id for group_id in
    #                                                          delegation_ids.mapped('user_group_ids')])
    #         else:
    #             user_groups = user_id.groups_id
    #         global_domains = []  # list of domains
    #         group_domains = domain  # list of domains
    #         for rule in self.browse(rules).sudo():
    #             # evaluate the domain for the current user
    #             eval_context['user'] = user_id
    #             dom = safe_eval(rule.domain_force, eval_context) if rule.domain_force else []
    #             dom = expression.normalize_domain(dom)
    #             if not rule.groups:
    #                 global_domains.append(dom)
    #             elif rule.groups & user_groups:
    #                 group_domains.append(dom)
    #
    #         # combine global domains and group domains
    #         if not group_domains:
    #             return expression.AND(global_domains)
    #         return expression.AND(global_domains + [expression.OR(group_domains)])
