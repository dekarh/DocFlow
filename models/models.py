# -*- coding: utf-8 -*-

from flectra import models, fields, api
from flectra.exceptions import UserError

class Status(models.Model):
    _name = 'docflow.status'
    name = fields.Char(string='Статус')

class Task(models.Model):
    _name = 'docflow.task'
    name = fields.Char()
    status_id = fields.Many2one('docflow.status',string='Статус')



