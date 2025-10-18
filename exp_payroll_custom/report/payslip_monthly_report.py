# -*- coding: utf-8 -*-
from odoo import models, api, _
from odoo.exceptions import ValidationError


class PayslipMonthlyReport(models.AbstractModel):
    _name = 'report.exp_payroll_custom.payslip_monthly_report'
    _description = 'Payslip Monthly Report'

    def get_rule_values(self, data=None, context={}):
        docs = []
        payslip_line = self.env['hr.payslip.line']
        count = 0
        exception = False
        if data['delist'] == 'ff':
            ftotal = 0
            title = _('Allowances and deduction Totals')
            docs.append({'count': '#', 'rule': _('Name'), 'type': _('Type'), 'amount': _('Amount'), })
            for rule in self.env[data['model']].browse(data['ids']):
                count += 1
                total = sum(payslip_line.browse(data['payslip_line_ids']).filtered(
                    lambda r: r.salary_rule_id.id == rule.id).mapped('amount'))
                ftotal += total
                docs.append({
                    'count': count,
                    'rule': rule.name,
                    'type': _(dict(rule.category_id._fields['rule_type'].selection, context={}).get(
                        rule.category_id.rule_type)),
                    'amount': total,
                })
            docs.append({'count': '', 'rule': _('Total'), 'type': '', 'amount': ftotal, })
        elif data['delist'] == 'tt':
            # TODO review bellow raise
            if not data['payslip_line_ids'] or not data['rule_ids']: raise ValidationError(
                _('Sorry No Data To Be Printed'))
            title = _('Employees Paysheet')
            rule_dict = {}
            for line in self.env['hr.salary.rule'].browse(data['rule_ids']):
                rule_dict.setdefault(line.category_id.rule_type, [])
                rule_dict[line.category_id.rule_type] += line
            tdict = {'count': '#', 'emp_no':_('EMP #'),'emp': _('Name'), }
            ndict = {'count': '', 'emp_no': _('Nets'),'emp':'' }
            for key, value in rule_dict.items():
                for x in value:
                    tdict[x.id], ndict[x.id] = x.name, 0
                tdict[key], ndict[key] = _('Total ') + _(
                    dict(x.category_id._fields['rule_type'].selection, context={}).get(key)), 0
            tdict['net'], ndict['net'], = _('Net'), 0
            if self.env.context.get('track_emp', False): tdict['track_id'] = 'track_id'
            docs.append(tdict)
            fnet = 0
            for emp in self.env[data['model']].browse(data['ids']):
                emp_dict = {}
                count += 1
                net = 0
                for key, value in tdict.items():
                    if value == _('#'):
                        emp_dict[key] = count
                        continue
                    elif value == _('EMP #'):
                        emp_dict[key] = emp.emp_no
                        continue
                    elif value == _('Name'):
                        emp_dict[key] = emp.name
                        continue
                    elif value == 'track_id':
                        emp_dict['track_id'] = emp.id
                        continue
                    elif isinstance(key, int):
                        total = sum(payslip_line.browse(data['payslip_line_ids']).filtered(
                            lambda r: r.employee_id.id == emp.id and r.salary_rule_id.id == key).mapped('total'))
                        emp_dict[key] = total
                        net += total
                        fnet += total
                        ndict[key] += total
                    elif isinstance(key, str):
                        total = sum(payslip_line.browse(data['payslip_line_ids']).filtered(
                            lambda
                                r: r.employee_id.id == emp.id and r.salary_rule_id.category_id.rule_type == key).mapped(
                            'amount'))
                        emp_dict[key] = total
                        ndict[key] += total
                    elif isinstance(key, bool):
                        total = sum(payslip_line.browse(data['payslip_line_ids']).filtered(
                            lambda
                                r: r.employee_id.id == emp.id and r.salary_rule_id.category_id.rule_type == False).mapped(
                            'total'))
                        emp_dict[key] = total
                        ndict[key] += total
                    if value == _('Net'):
                        emp_dict[key] = net
                        continue
                docs.append(emp_dict)
            ndict['net'] = fnet
            docs.append(ndict)
        else:
            title = _('Specific Allowance and deduction Report')
            exception = True
            for rule in self.env[data['model']].browse(data['ids']):
                count = 0
                ftotal = 0
                inner_doc = {'rule': rule.name, 'lines': [], }
                inner_doc['lines'].append({'count': '#', 'emp_no': _('EMP #'), 'emp': _('Employee'), 'amount': _('Amount'), })
                for emp in set(payslip_line.browse(data['payslip_line_ids']).filtered(
                        lambda r: r.salary_rule_id.id == rule.id).mapped('employee_id')):
                    count += 1
                    total = sum(payslip_line.browse(data['payslip_line_ids']).filtered(
                        lambda r: r.employee_id.id == emp.id and r.salary_rule_id.id == rule.id).mapped('amount'))
                    ftotal += total
                    inner_doc['lines'].append({'count': count, 'emp_no': emp.emp_no, 'emp': emp.name, 'amount': total, })
                inner_doc['lines'].append({'count': '', 'emp_no': _('Total'),'emp':'', 'amount': ftotal, })
                docs.append(inner_doc)
        return title, exception, docs

    @api.model
    def _get_report_values(self, docids, data=None):
        title, exception, docs = self.get_rule_values(data)
        return {
            'exception': exception,
            'title': title,
            'date_from': data['form']['date_from'],
            'date_to': data['form']['date_to'],
            'docs': docs,
        }


class PayslipMonthlyReportXlsx(models.AbstractModel):
    _name = "report.exp_payroll_custom.payslip_monthly_report_xlsx"
    _inherit = 'report.report_xlsx.abstract'

    @api.model
    def generate_xlsx_report(self, workbook, data, objs):
        title, exception, docs = PayslipMonthlyReport.get_rule_values(self, data)
        sheet = workbook.add_worksheet('Proll Monthly report')
        format1 = workbook.add_format({'bottom': True, 'right': True, 'left': True, 'top': True, 'align': 'center', })
        format2 = workbook.add_format({'font_size': 14, 'bottom': True, 'right': True, 'left': True, 'top': True,
                                       'align': 'center', 'bold': True})
        format2.set_align('center')
        format2.set_align('vcenter')
        format3 = workbook.add_format({'bottom': True, 'align': 'center', 'bold': True, })
        if data['delist'] != 'tf':
            sheet.merge_range('C5:F5', title, format2)
            sheet.merge_range('C6:F6', data['form']['date_from'] + '  -  ' + data['form']['date_to'], format2)
        else:
            sheet.merge_range('C5:E5', title, format2)
            sheet.merge_range('C6:E6', data['form']['date_from'] + '  -  ' + data['form']['date_to'], format2)
        sheet.set_column('C:C', 10)
        sheet.set_column('D:D', 40)
        # sheet.set_column('E:Z', 20)
        row = 6
        for line in docs:
            if data['delist'] != 'tf':
                row += 1
                clm = 1
                for k, v in line.items():
                    clm += 1
                    sheet.write(row, clm, line[k], format1)
            else:
                row += 1
                clm = 2
                sheet.write(row, clm, line['rule'], format3)
                for ln in line['lines']:
                    row += 1
                    clm = 1
                    for k, v in ln.items():
                        clm += 1
                        sheet.write(row, clm, ln[k], format1)
                row += 1
