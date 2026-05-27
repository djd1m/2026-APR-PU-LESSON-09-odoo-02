# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class SuTask(models.Model):
    _name = 'su.task'
    _description = 'Задача'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'priority desc, deadline asc, id'

    name = fields.Char(string='Название', required=True, tracking=True)
    description = fields.Html(string='Описание')
    project_id = fields.Many2one(
        'su.project',
        string='Объект',
        ondelete='cascade',
        required=True,
        tracking=True,
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
        tracking=True,
    )
    assignee_id = fields.Many2one(
        'res.users',
        string='Исполнитель',
        tracking=True,
    )
    deadline = fields.Date(string='Дедлайн', tracking=True)
    progress = fields.Float(
        string='Прогресс %',
        compute='_compute_progress',
        inverse='_inverse_progress',
        store=True,
    )
    progress_manual = fields.Float(string='Прогресс (ручной) %', default=0.0)
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
    subtask_count = fields.Integer(
        string='Подзадач',
        compute='_compute_subtask_count',
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

    # ── Computed fields ─────────────────────────────────────────

    @api.depends('dependency_ids.state')
    def _compute_is_blocked(self):
        for task in self:
            task.is_blocked = any(
                dep.state not in ('done', 'cancelled')
                for dep in task.dependency_ids
            )

    @api.depends('child_ids.progress', 'child_ids.state', 'progress_manual')
    def _compute_progress(self):
        for task in self:
            children = task.child_ids.filtered(
                lambda c: c.state != 'cancelled'
            )
            if children:
                task.progress = sum(children.mapped('progress')) / len(children)
            else:
                task.progress = task.progress_manual

    def _inverse_progress(self):
        for task in self:
            if not task.child_ids:
                task.progress_manual = task.progress

    def _compute_subtask_count(self):
        for task in self:
            task.subtask_count = len(task.child_ids)

    # ── Constraints ─────────────────────────────────────────────

    @api.constrains('dependency_ids')
    def _check_circular_dependency(self):
        for task in self:
            visited = set()
            stack = list(task.dependency_ids.ids)
            while stack:
                dep_id = stack.pop()
                if dep_id == task.id:
                    raise ValidationError(
                        'Обнаружена циклическая зависимость задач.'
                    )
                if dep_id not in visited:
                    visited.add(dep_id)
                    dep_task = self.browse(dep_id)
                    stack.extend(dep_task.dependency_ids.ids)

    # ── State machine actions ───────────────────────────────────

    def action_start(self):
        for task in self:
            if task.is_blocked:
                raise ValidationError(
                    'Задача заблокирована незавершёнными зависимостями.'
                )
            if task.state != 'new':
                raise ValidationError(
                    'Начать можно только новую задачу.'
                )
            task.state = 'in_progress'

    def action_review(self):
        for task in self:
            if task.state != 'in_progress':
                raise ValidationError(
                    'Отправить на проверку можно только задачу в работе.'
                )
            task.state = 'review'

    def action_done(self):
        for task in self:
            if task.state != 'review':
                raise ValidationError(
                    'Завершить можно только задачу на проверке.'
                )
            task.state = 'done'
            task.progress_manual = 100.0

    action_complete = action_done  # alias

    def action_cancel(self):
        for task in self:
            if task.state in ('done', 'cancelled'):
                raise ValidationError(
                    'Нельзя отменить завершённую или уже отменённую задачу.'
                )
            # Предупредить о зависимых задачах
            dependents = self.search([
                ('dependency_ids', 'in', task.id),
                ('state', 'not in', ('done', 'cancelled')),
            ])
            if dependents:
                task.message_post(
                    body='Внимание: %d зависимых задач будут заблокированы: %s'
                    % (len(dependents), ', '.join(dependents.mapped('name'))),
                )
            task.state = 'cancelled'

    def action_reopen(self):
        for task in self:
            if task.state not in ('review', 'done'):
                raise ValidationError(
                    'Вернуть в работу можно только задачу на проверке'
                    ' или завершённую.'
                )
            task.state = 'in_progress'
            if task.progress_manual >= 100.0:
                task.progress_manual = 99.0

    # ── Navigation ───────────────────────────────────────────────

    def action_view_subtasks(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Подзадачи',
            'res_model': 'su.task',
            'view_mode': 'tree,form',
            'domain': [('parent_id', '=', self.id)],
            'context': {
                'default_parent_id': self.id,
                'default_project_id': self.project_id.id,
            },
        }

    # ── Notification on brigade assignment ──────────────────────

    def write(self, vals):
        # Guard: prevent kanban drag-drop from bypassing blocked check
        if 'state' in vals and vals['state'] == 'in_progress':
            for task in self:
                if task.state == 'new' and task.is_blocked:
                    raise ValidationError(
                        'Задача "%s" заблокирована незавершёнными'
                        ' зависимостями.' % task.name
                    )
        old_brigades = {}
        if 'brigade_id' in vals:
            old_brigades = {task.id: task.brigade_id for task in self}
        result = super().write(vals)
        if 'brigade_id' in vals:
            for task in self:
                old = old_brigades.get(task.id)
                if task.brigade_id and task.brigade_id != old:
                    partners = task.brigade_id.member_ids.mapped('partner_id')
                    if task.brigade_id.foreman_id:
                        partners |= task.brigade_id.foreman_id.partner_id
                    if partners:
                        task.message_post(
                            body='Задача назначена на бригаду: %s'
                            % task.brigade_id.name,
                            partner_ids=partners.ids,
                            message_type='notification',
                            subtype_xmlid='mail.mt_comment',
                        )
        return result
