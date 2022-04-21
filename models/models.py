# -*- coding: utf-8 -*-

from flectra import models, fields, api
from flectra import tools, _
from flectra.exceptions import ValidationError, AccessError
from flectra.modules.module import get_module_resource
from flectra.exceptions import UserError

#--------------------- hr_pf------------------------------------------------------------------------

class Towns(models.Model):
    _name = 'hr_pf.officetown'
    name = fields.Char(string='Офисы в Городах')


class UsersPF(models.Model):            # 'user_' + id_pf
    _inherit = 'res.users'
    # Поля для синхронизации с ПФ
    id_pf = fields.Integer(string='id Глобальный')
    general_user_pf = fields.Integer(string='id в адр.строке')
    userid_pf = fields.Integer(string='id для задач')
    general_contact_pf = fields.Integer(string='id в адр.строке')


class HrEmployeePf(models.Model):       # 'empl_' + id_pf
    _inherit = 'hr.employee'
    # Поля для синхронизации с ПФ
    status = fields.Char(string='Статус контакта в ПФ')
    officetown_id = fields.Many2one('hr_pf.officetown', string='Офис и Город')
    # Добавил аналог  department_id - projectgroup_id. Для этого провел рефакторинг по ключам:
    # 'department_id', 'hr.department', 'Department', 'parent', 'child', 'manager', 'member', 'jobs'
    parent_pg_id = fields.Many2one('hr.employee', 'Manager ProjectGroup')
    child_pg_ids = fields.One2many('hr.employee', 'parent_pg_id', string='Subordinates')
    projectgroup_id = fields.Many2one('hr.projectgroup', string='ProjectGroup')
    id_pf = fields.Integer(string='Глобальный id юзера из ПФ')

    @api.onchange('projectgroup_id')
    def _onchange_projectgroup(self):
        self.parent_pg_id = self.projectgroup_id.manager_pg_id


class HrJobPf(models.Model):
    _inherit = 'hr.job'
    projectgroup_id = fields.Many2one('hr.projectgroup', string='ProjectGroup')


class ProjectGroup(models.Model):
    _name = "hr.projectgroup"
    _description = "ProjectGroup"
    _inherit = ['mail.thread']
    _order = "name"

    name = fields.Char(string='ProjectGroup', required=True)
    complete_name = fields.Char('Complete Name', compute='_compute_complete_name', store=True)
    active = fields.Boolean('Active', default=True)
    company_id = fields.Many2one('res.company', string='Company', index=True, default=lambda self: self.env.user.company_id)
    parent_pg_id = fields.Many2one('hr.projectgroup', string='Parent ProjectGroup', index=True)
    child_pg_ids = fields.One2many('hr.projectgroup', 'parent_pg_id', string='Child ProjectGroup')
    manager_pg_id = fields.Many2one('hr.employee', string='Manager ProjectGroup', track_visibility='onchange')
    member_pg_ids = fields.One2many('hr.employee', 'projectgroup_id', string='ProjectGroup Members', readonly=True)
    jobs_ids = fields.One2many('hr.job', 'projectgroup_id', string='Jobs')
    note = fields.Text('Note')
    color = fields.Integer('Color Index')

    @api.depends('name', 'parent_pg_id.complete_name')
    def _compute_complete_name(self):
        for projectgroup in self:
            if projectgroup.parent_pg_id:
                projectgroup.complete_name = '%s / %s' % (projectgroup.parent_pg_id.complete_name, projectgroup.name)
            else:
                projectgroup.complete_name = projectgroup.name

    @api.constrains('parent_pg_id')
    def _check_parent_pg_id(self):
        if not self._check_recursion():
            raise ValidationError(_('Error! You cannot create recursive projectgroups.'))

    @api.model
    def create(self, vals):
        # TDE note: auto-subscription of manager done by hand, because currently
        # the tracking allows to track+subscribe fields linked to a res.user record
        # An update of the limited behavior should come, but not currently done.
        projectgroup = super(ProjectGroup, self.with_context(mail_create_nosubscribe=True)).create(vals)
        manager_pg = self.env['hr.employee'].browse(vals.get("manager_pg_id"))
        if manager_pg.user_id:
            projectgroup.message_subscribe_users(user_ids=manager_pg.user_id.ids)
        return projectgroup

    @api.multi
    def write(self, vals):
        """ If updating manager of a projectgroup, we need to update all the employees
            of projectgroup hierarchy, and subscribe the new manager.
        """
        # TDE note: auto-subscription of manager done by hand, because currently
        # the tracking allows to track+subscribe fields linked to a res.user record
        # An update of the limited behavior should come, but not currently done.
        if 'manager_pg_id' in vals:
            manager_pg_id = vals.get("manager_pg_id")
            if manager_pg_id:
                manager_pg = self.env['hr.employee'].browse(manager_pg_id)
                # subscribe the manager user
                if manager_pg.user_id:
                    self.message_subscribe_users(user_ids=manager_pg.user_id.ids)
            # set the employees's parent to the new manager
            self._update_employee_manager_pg(manager_pg_id)
        return super(ProjectGroup, self).write(vals)

    def _update_employee_manager_pg(self, manager_pg_id):
        employees = self.env['hr.employee']
        for projectgroup in self:
            employees = employees | self.env['hr.employee'].search([
                ('id', '!=', manager_pg_id),
                ('projectgroup_id', '=', projectgroup.id),
                ('parent_pg_id', '=', projectgroup.manager_pg_id.id)
            ])
        employees.write({'parent_pg_id': manager_pg_id})

#-------------------------- docflow-----------------------------------------------------------------------

class GroupsPF(models.Model):
    """Дополнительные поля в группу доступа для синхронизации с ПФ"""
    _inherit = 'res.groups'

    id_from_pf = fields.Char(string='Идентификатор группы ПФ')


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

