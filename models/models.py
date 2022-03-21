# -*- coding: utf-8 -*-

from flectra import models, fields, api
from flectra.exceptions import UserError

class ProcessDF(models.Model):          # 'pr_' + id из ПФ
    _name = 'project.process'
    name = fields.Char(string='Название процесса в ПФ', required=True)
    id_pf = fields.Integer(string='id процесса в ПФ', required=True)
    type_ids = fields.One2many('project.task.type', 'process_id', string='Список статусов процесса', readonly=True)


class ProjectTaskTypeDF(models.Model):  # 'st_' + id из ПФ
    _inherit = 'project.task.type'
    # !!!! надо поменять на Many2many ((((
    process_id = fields.Many2one('project.process',string='Связанный со статусом процесс')


class FieldTemplateDF(models.Model):    # 'tpl_field_' + id из ПФ
    _name = 'docflow.field.template'
    name = fields.Char(string='Название поля в ПФ', required=True)
    id_pf = fields.Integer(string='id поля в ПФ', required=True)


class FieldDF(models.Model):            # id task из ПФ (general) + '_' + template field id из ПФ
    _name = 'docflow.field'
    name = fields.Char(string='Название поля')
    template_field_name_id = fields.Many2one('docflow.field.template', string='Название поля в ПФ', required=True)
    template_field_id_pf = fields.Integer(compute="_template_field_id_pf", store=True)
    text = fields.Char(string='Параметр text')
    value = fields.Char(string='Параметр value')
    task_id = fields.Many2one('project.task','Связанная с полем задача')

    @api.depends('template_field_name_id')
    def _template_field_id_pf(self):
        self.template_field_id_pf = self.template_field_name_id.id_pf


class TaskDF(models.Model):
    _inherit = 'project.task'
    fields_ids = fields.One2many('docflow.field', 'task_id', string='Поля из ПФ', readonly=True)



