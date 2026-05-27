# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class SuTask(models.Model):
    _name = 'su.task'
    _description = 'Задача'
    _order = 'priority desc, deadline asc, id'

    name = fields.Char(string='Название', required=True)
    description = fields.Html(string='Описание')
    project_id = fields.Many2one(
        'su.project',
        string='Объект',
        ondelete='cascade',
        required=True,
    )
    state = fields.Selection([
        ('new', 'Новая'),
        ('in_progress', 'В работе'),
        ('review', 'На проверке'),
        ('done', 'Выполнена'),
        ('cancelled', 'Отменена'),
    ], string='Статус', default='new', tracking=True)
    priority = fields.Selection([
        ('0', 'Низкий'),
        ('1', 'Средний'),
        ('2', 'Высокий'),
        ('3', 'Критический'),
    ], string='Приоритет', default='1')
    brigade_id = fields.Many2one(
        'su.brigade',
        string='Бригада',
    )
    assignee_id = fields.Many2one(
        'res.users',
        string='Исполнитель',
    )
    deadline = fields.Date(string='Дедлайн')
    progress = fields.Float(string='Прогресс %', default=0.0)
    planned_cost = fields.Monetary(string='Плановая стоимость')
    company_id = fields.Many2one(
        'res.company',
        string='Компания',
        related='project_id.company_id',
        store=True,
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Валюта',
        related='company_id.currency_id',
        store=True,
    )
    parent_id = fields.Many2one(
        'su.task',
        string='Родительская задача',
        ondelete='cascade',
    )
    child_ids = fields.One2many(
        'su.task',
        'parent_id',
        string='Подзадачи',
    )
    dependency_ids = fields.Many2many(
        'su.task',
        'su_task_dependency_rel',
        'task_id',
        'depends_on_id',
        string='Зависит от',
    )
    is_blocked = fields.Boolean(
        string='Заблокирована',
        compute='_compute_is_blocked',
        store=True,
    )
    photo_ids = fields.One2many('su.photo', 'task_id', string='Фото')

    @api.depends('dependency_ids.state')
    def _compute_is_blocked(self):
        for task in self:
            task.is_blocked = any(
                dep.state not in ('done', 'cancelled')
                for dep in task.dependency_ids
            )

    def action_start(self):
        for task in self:
            if task.is_blocked:
                raise ValidationError(
                    'Задача заблокирована незавершёнными зависимостями.'
                )
            task.state = 'in_progress'

    def action_review(self):
        self.write({'state': 'review'})

    def action_done(self):
        self.write({'state': 'done', 'progress': 100.0})

    def action_cancel(self):
        self.write({'state': 'cancelled'})

    def action_reopen(self):
        self.write({'state': 'in_progress'})
