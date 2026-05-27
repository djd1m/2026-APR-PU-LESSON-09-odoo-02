# -*- coding: utf-8 -*-
from odoo import models, fields, api


class SuProject(models.Model):
    _name = 'su.project'
    _description = 'Строительный объект'
    _order = 'create_date desc'

    name = fields.Char(string='Название', required=True)
    address = fields.Char(string='Адрес')
    project_type = fields.Selection([
        ('renovation', 'Ремонт'),
        ('construction', 'Строительство'),
        ('izhs', 'ИЖС'),
    ], string='Тип объекта')
    state = fields.Selection([
        ('draft', 'Черновик'),
        ('active', 'В работе'),
        ('paused', 'Пауза'),
        ('done', 'Завершён'),
    ], string='Статус', default='draft', tracking=True)
    area_sqm = fields.Float(string='Площадь м²')
    budget_planned = fields.Monetary(string='Плановый бюджет')
    budget_actual = fields.Monetary(
        string='Фактический бюджет',
        compute='_compute_budget_actual',
        store=True,
    )
    progress = fields.Float(
        string='Прогресс %',
        compute='_compute_progress',
        store=True,
    )
    start_date = fields.Date(string='Дата начала')
    end_date = fields.Date(string='Дата окончания')
    manager_id = fields.Many2one('res.users', string='Ответственный')
    company_id = fields.Many2one(
        'res.company',
        string='Компания',
        default=lambda self: self.env.company,
        required=True,
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Валюта',
        related='company_id.currency_id',
        store=True,
    )
    task_ids = fields.One2many('su.task', 'project_id', string='Задачи')
    estimate_ids = fields.One2many('su.estimate', 'project_id', string='Сметы')
    photo_ids = fields.One2many('su.photo', 'project_id', string='Фото')

    @api.depends('task_ids.progress')
    def _compute_progress(self):
        for project in self:
            tasks = project.task_ids
            if tasks:
                project.progress = sum(tasks.mapped('progress')) / len(tasks)
            else:
                project.progress = 0.0

    @api.depends('estimate_ids.total_amount')
    def _compute_budget_actual(self):
        for project in self:
            project.budget_actual = sum(
                project.estimate_ids.filtered(
                    lambda e: e.state == 'confirmed'
                ).mapped('total_amount')
            )
