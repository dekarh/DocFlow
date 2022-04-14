# -*- coding: utf-8 -*-

from flectra import models, fields, api
from flectra.exceptions import UserError

class TaskTemplateDF(models.Model):          # 'tt_' + id из ПФ
    _name = 'docflow.tasktemplate'
    name = fields.Char(string='Название шаблона')
    id_pf = fields.Integer(string='id шаблона задачи (глобальный) в ПФ')
    id_pf_general = fields.Integer(string='id шаблона задачи (в адр.стр) в ПФ')
    task_ids = fields.One2many('project.task', 'tasktemplate_id', string='Список задач по шаблону ', readonly=True)


class ProjectDF(models.Model):          # 'pr_' + id из ПФ
    _inherit = 'project.project'
    id_pf = fields.Integer(string='id процесса(.project) в ПФ')


class FieldTemplateDF(models.Model):    # 'tpl_field_' + id из ПФ
    _name = 'docflow.field.template'
    name = fields.Char(string='Название поля в ПФ', required=True)
    id_pf = fields.Integer(string='id поля в ПФ', required=True)


class FieldDF(models.Model):            # id task из ПФ (general) + '_' + template field id из ПФ
    _name = 'docflow.field'
    name = fields.Char(string='Название поля')#, compute="_name_from_template", )
    template_field_name_id = fields.Many2one('docflow.field.template', string='Название поля в ПФ', required=True)
    template_field_id_pf = fields.Integer(compute="_template_field_id_pf")#, store=True)
    text = fields.Char(string='Параметр text')
    value = fields.Char(string='Параметр value')
    task_id = fields.Many2one('project.task',string='Связанная с полем задача')

    @api.depends('template_field_name_id')
    def _template_field_id_pf(self):
        self.template_field_id_pf = self.template_field_name_id.id_pf

    #@api.depends('name')
    #def _name_from_template(self):
    #    self.name = self.template_field_name_id.name


class TaskDF(models.Model):             # 'task_' + id (global) из ПФ
    _inherit = 'project.task'
    fields_ids = fields.One2many('docflow.field', 'task_id', string='Поля из ПФ', readonly=True)
    tasktemplate_id = fields.Many2one('docflow.tasktemplate', string='Шаблон задачи')
    id_pf = fields.Integer(string='id (глобальный) из ПФ')
    id_pf_general = fields.Integer(string='id (адр.строка) из ПФ')
    employee_id = fields.Many2one('hr.employee', string='Сотрудник')

class ProjectTaskTypeDF(models.Model):
    _inherit = 'project.task.type'
    id_pf = fields.Integer(string='id (глобальный) из ПФ')



