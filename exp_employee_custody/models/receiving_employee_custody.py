from odoo import models, fields, api, _, exceptions
from odoo import SUPERUSER_ID
from datetime import datetime, date
import calendar
from pprint import pprint


class EmployeeReceiveCustody(models.Model):
    _name = 'hr.custody.receiving'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'employee_id'
    _description = 'Receiving custody'

    current_date = fields.Date(default=lambda self: fields.Date.today())
    from_hr_department = fields.Boolean()
    employee_no = fields.Char(related="employee_id.emp_no", readonly=True)
    note = fields.Text()
    deduction_amount = fields.Float()
    salary_rule_flag = fields.Boolean()
    state = fields.Selection(selection=[
        ("draft", _("Draft")),
        ("submit", _("send")),
        ("direct", _("Direct Manager")),
        ("admin", _("Human Resources Manager")),
        ("approve", _("Warehouse Keeper")),
        ("done", _("Return Done")),
        ("refuse", _("Refuse"))
    ], default='draft')
    call_compute_function = fields.Char(compute='_get_custody_line_domain')

    # Relational fields
    department_id = fields.Many2one(related="employee_id.department_id", readonly=True)
    job_id = fields.Many2one(related="employee_id.job_id", readonly=True)
    country_id = fields.Many2one(related="employee_id.country_id", readonly=True)
    return_custody_line_ids = fields.One2many('employee.return.custody.line', 'employee_return_custody_line_id',
                                              store=True)
    employee_id = fields.Many2one('hr.employee', 'Employee', default=lambda item: item.get_user_id())
    salary_rule_id = fields.Many2one('hr.salary.rule', domain=['|', ('category_id.rule_type', '=', 'deduction'),
                                                               ('category_id.name', '=', 'Deduction')])
    advantage_line_id = fields.Many2one('contract.advantage')  # To save advantage line

    def get_user_id(self):
        employee_id = self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)
        if employee_id:
            return employee_id.id
        else:
            return False


    @api.depends('employee_id')
    def _get_custody_line_domain(self):
        for item in self:
            item.return_custody_line_ids = [(0, 0, val) for val in []]
            if item.employee_id:
                employee_custody = self.env['custom.employee.custody'].search(
                    [('employee_id', '=', item.employee_id.id), ('state', 'in', ['approve', 'done'])])
                items = []
                for record in employee_custody:
                    if ((item.state == 'done' and record.state == 'done') and (
                            record.receiving_custody.id == item.id)) or record.state == 'approve':
                        for line in record.custody_line_ids:
                            if line.quantity - line.receiving_quantity > 0 and line.amount == 0:
                                items.append({
                                    'name': line.name,
                                    'serial': line.serial,
                                    'employee_return_custody_line_id': item.id,
                                    'quantity': line.quantity - line.receiving_quantity,
                                    'note': line.note,
                                    'custody_line_id': line.id})
                item.return_custody_line_ids = [(0, 0, val) for val in items]

    # Re-fill receive custody lines

    def re_fill_receive_custody_lines(self):
        for item in self:
            item.return_custody_line_ids = False
            if item.employee_id:
                employee_custody = self.env['custom.employee.custody'].search(
                    [('employee_id', '=', item.employee_id.id), ('state', 'in', ['approve', 'done'])])
                items = []
                for record in employee_custody:
                    if ((item.state == 'done' and record.state == 'done') and (
                            record.receiving_custody.id == item.id)) or record.state == 'approve':
                        for line in record.custody_line_ids:
                            if line.quantity - line.receiving_quantity > 0 and line.amount == 0:
                                items.append({
                                    'name': line.name,
                                    'serial': line.serial,
                                    'employee_return_custody_line_id': item.id,
                                    'quantity': line.quantity - line.receiving_quantity,
                                    'note': line.note,
                                    'custody_line_id': line.id})
                item.return_custody_line_ids = [(0, 0, val) for val in items]

    @api.onchange('return_custody_line_ids')
    def compute_deduction_amount(self):
        total_amount = 0.0
        for item in self:
            item.salary_rule_flag = False
            for line in item.return_custody_line_ids:
                total_amount += line.deduction_amount
            item.deduction_amount = total_amount

            # salary_rule_flag Flag do visible salary rule
            if item.deduction_amount > 0.0:
                item.salary_rule_flag = True


    def set_to_draft(self):
        for item in self:
            if item.employee_id and item.state == 'done':
                employee_custody = self.env['custom.employee.custody'].search(
                    [('employee_id', '=', item.employee_id.id), ('state', 'in', ['done', 'approve'])])
                for line in employee_custody:
                    for element in self.return_custody_line_ids:
                        for custody in line.custody_line_ids:
                            if custody.receiving_quantity > 0.0:
                                line.state = 'approve'
                            if element.custody_line_id.id == custody.id:
                                if custody.receiving_quantity - element.quantity >= 0:
                                    custody.receiving_quantity = custody.receiving_quantity - element.quantity
                                    custody.amount = 0.0
                                else:
                                    raise exceptions.Warning(_('Receiving quantity can not be negative value '))

                # Remove contract advantage line when re-draft
                if item.advantage_line_id:
                    item.advantage_line_id.unlink()

        self.state = 'draft'

    def send(self):
        self.state = 'submit'

    def dr_manager(self):
        self.state = 'direct'


    def dr_hr_manager(self):
        self.state = 'admin'


    def done(self):
        for item in self:

            # If return any custody quantity fill it in receiving quantity
            for line in item.return_custody_line_ids:
                if (line.custody_line_id.receiving_quantity + line.quantity) > line.custody_line_id.quantity:
                    raise exceptions.Warning(_('Receiving quantity can not be greater than original quantity'))
                else:
                    line.custody_line_id.receiving_quantity = line.custody_line_id.receiving_quantity + line.quantity
                    line.custody_line_id.amount = line.deduction_amount

                if line.custody_line_id.receiving_quantity < 0.0:
                    raise exceptions.Warning(_('Receiving quantity can not be negative value '))

            if item.employee_id:
                custody_not_complete = 0.0
                employee_custody = self.env['custom.employee.custody'].search(
                    [('employee_id', '=', item.employee_id.id), ('state', '=', 'approve')])
                for record in employee_custody:
                    record.write({
                        'receiving_custody': item.id,
                    })

                # Check all employee custody line are completed the change state to done
                for record in employee_custody:
                    for line in record.custody_line_ids:
                        if line.receiving_quantity != line.quantity and line.amount == 0.0:
                            custody_not_complete += 1
                    if custody_not_complete == 0:
                        record.state = 'done'

                # Move deduction amount to employee contract advantage lines
                if item.employee_id.contract_id:
                    if item.deduction_amount and item.salary_rule_id:
                        contract = item.employee_id.contract_id
                        # get start and end date of the current month
                        current_date = date.today()
                        month_start = date(current_date.year, current_date.month, 1)
                        month_end = date(current_date.year, current_date.month, calendar.mdays[current_date.month])

                        advantage_line_id = self.env['contract.advantage'].create({
                            'benefits_discounts': item.salary_rule_id.id,
                            'type': 'customize',
                            'date_from': month_start,
                            'date_to': month_end,
                            'amount': item.deduction_amount,
                            'contract_advantage_id': contract.id,
                        })
                        item.advantage_line_id = advantage_line_id.id
                else:
                    raise exceptions.Warning(_('Employee "%s" has not contract !') % item.employee_id.name)

            item.state = 'done'


    def warehouse_keeper(self):
        self.state = 'approve'


    def refuse(self):
        self.state = 'refuse'

    # Override create function
    # make sure the one2many return_custody_line_ids save changes when create and updates
    # @api.model
    # def create(self , values):
    #     deduction_amount = values.get('return_custody_line_ids')
    #     deduction_amount_list = []
    #     quantity_list = []
    #
    #     for line in deduction_amount:
    #         deduction_amount_list.append(line[2]['deduction_amount'])
    #         quantity_list.append(line[2]['quantity'])
    #     print(deduction_amount)
    #     print(deduction_amount_list)
    #     res = super(EmployeeReceiveCustody ,self).create(values)
    #
    #     index = 0
    #     for element in res.return_custody_line_ids:
    #         element.deduction_amount = deduction_amount_list[index]
    #         element.quantity = quantity_list[index]
    #         index +=1
    #
    #     print(quantity_list)
    #     return res

    # Override unlink function
    def unlink(self):
        for i in self:
            if i.state != 'draft':
                raise exceptions.Warning(_('You can not delete record in state not in draft'))
        return super(EmployeeReceiveCustody, self).unlink()


class EmployeeReturnCustodyLine(models.Model):
    _name = 'employee.return.custody.line'
    _rec_name = 'name'

    name = fields.Char()
    serial = fields.Char()
    quantity = fields.Float()
    note = fields.Char()
    deduction_amount = fields.Float()

    # Relational fields
    employee_return_custody_line_id = fields.Many2one(comodel_name='hr.custody.receiving')  # inverse field
    custody_line_id = fields.Many2one('employee.custody.line')  # to save custody_id