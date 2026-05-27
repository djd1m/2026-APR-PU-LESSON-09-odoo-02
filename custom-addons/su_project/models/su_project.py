# -*- coding: utf-8 -*-
from datetime import timedelta
from odoo import models, fields, api
from odoo.exceptions import UserError


class SuProject(models.Model):
    _name = 'su.project'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Строительный объект'
    _order = 'create_date desc'

    # ── Thresholds (class constants) ───────────────────────────
    BUDGET_YELLOW_THRESHOLD = 5.0   # % over budget → yellow
    BUDGET_RED_THRESHOLD = 15.0     # % over budget → red
    BUDGET_ALERT_THRESHOLD = 10.0   # % over budget → AI alert
    DEADLINE_WARNING_DAYS = 7       # days until end_date → yellow

    # ── Core fields ────────────────────────────────────────────
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

    # ── Relational fields ──────────────────────────────────────
    task_ids = fields.One2many('su.task', 'project_id', string='Задачи')
    estimate_ids = fields.One2many('su.estimate', 'project_id', string='Сметы')
    photo_ids = fields.One2many('su.photo', 'project_id', string='Фото')
    expense_ids = fields.One2many('su.expense', 'project_id', string='Расходы')

    # ── Budget fields (Monetary — never Float for money) ───────
    budget_planned = fields.Monetary(string='Плановый бюджет')
    budget_actual = fields.Monetary(
        string='Фактический бюджет',
        compute='_compute_budget_actual',
        store=True,
    )
    budget_deviation = fields.Monetary(
        string='Отклонение бюджета',
        compute='_compute_budget_deviation',
        store=True,
    )
    budget_deviation_pct = fields.Float(
        string='Отклонение %',
        compute='_compute_budget_deviation',
        store=True,
        digits=(5, 2),
    )

    # ── Progress & stats ───────────────────────────────────────
    progress = fields.Float(
        string='Прогресс %',
        compute='_compute_progress',
        store=True,
    )
    task_count = fields.Integer(
        string='Кол-во задач',
        compute='_compute_task_count',
        store=True,
    )
    expense_count = fields.Integer(
        string='Кол-во расходов',
        compute='_compute_expense_count',
        store=True,
    )

    # ── Health indicators ──────────────────────────────────────
    health_status = fields.Selection([
        ('green', 'В норме'),
        ('yellow', 'Внимание'),
        ('red', 'Критично'),
    ], string='Статус здоровья', compute='_compute_health_status', store=True)
    overdue = fields.Boolean(
        string='Просрочен',
        compute='_compute_overdue',
        store=True,
    )

    # ── Computed methods ───────────────────────────────────────

    @api.depends('task_ids.progress')
    def _compute_progress(self):
        for project in self:
            tasks = project.task_ids
            if tasks:
                project.progress = sum(tasks.mapped('progress')) / len(tasks)
            else:
                project.progress = 0.0

    @api.depends('expense_ids.amount', 'expense_ids.state')
    def _compute_budget_actual(self):
        for project in self:
            confirmed = project.expense_ids.filtered(
                lambda e: e.state == 'confirmed'
            )
            project.budget_actual = sum(confirmed.mapped('amount'))

    @api.depends('budget_actual', 'budget_planned')
    def _compute_budget_deviation(self):
        for project in self:
            if project.budget_planned:
                deviation = project.budget_actual - project.budget_planned
                project.budget_deviation = deviation
                project.budget_deviation_pct = (
                    deviation / project.budget_planned
                ) * 100.0
            else:
                project.budget_deviation = 0.0
                project.budget_deviation_pct = 0.0

    @api.depends('budget_deviation_pct', 'end_date')
    def _compute_health_status(self):
        today = fields.Date.today()
        for project in self:
            pct = project.budget_deviation_pct
            is_overdue = (
                project.end_date and project.end_date < today
            )
            is_near_deadline = (
                project.end_date
                and project.end_date < today + timedelta(
                    days=self.DEADLINE_WARNING_DAYS
                )
            )

            if is_overdue or pct > self.BUDGET_RED_THRESHOLD:
                project.health_status = 'red'
            elif is_near_deadline or (
                pct > self.BUDGET_YELLOW_THRESHOLD
                and pct <= self.BUDGET_RED_THRESHOLD
            ):
                project.health_status = 'yellow'
            else:
                project.health_status = 'green'

    @api.depends('task_ids')
    def _compute_task_count(self):
        for project in self:
            project.task_count = len(project.task_ids)

    @api.depends('end_date')
    def _compute_overdue(self):
        today = fields.Date.today()
        for project in self:
            project.overdue = bool(
                project.end_date and project.end_date < today
            )

    @api.depends('expense_ids')
    def _compute_expense_count(self):
        for project in self:
            project.expense_count = len(project.expense_ids)

    def _check_budget_alert(self):
        """Post chatter notification when budget deviation exceeds threshold."""
        # Ensure stored computed fields are flushed before reading
        self.flush_recordset(['budget_deviation_pct'])
        for project in self:
            if not project.budget_planned:
                continue
            pct = project.budget_deviation_pct
            if pct > self.BUDGET_ALERT_THRESHOLD:
                project.message_post(
                    body=(
                        'Внимание: бюджет объекта "%s" превышен на %.1f%% '
                        '(порог: %.1f%%)'
                    ) % (project.name, pct, self.BUDGET_ALERT_THRESHOLD),
                    subject='Превышение бюджета',
                    message_type='notification',
                    subtype_xmlid='mail.mt_note',
                )

    def action_view_expenses(self):
        """Open expense list for this project."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Расходы',
            'res_model': 'su.expense',
            'view_mode': 'tree,form,pivot,graph',
            'domain': [('project_id', '=', self.id)],
            'context': {'default_project_id': self.id},
        }

    # ── State transition actions ───────────────────────────────

    def action_start(self):
        """Черновик → В работе."""
        for project in self:
            if project.state != 'draft':
                raise UserError(
                    'Начать можно только объект в статусе "Черновик".'
                )
            vals = {'state': 'active'}
            if not project.start_date:
                vals['start_date'] = fields.Date.today()
            project.write(vals)

    def action_pause(self):
        """В работе → Пауза."""
        for project in self:
            if project.state != 'active':
                raise UserError(
                    'Приостановить можно только объект в статусе "В работе".'
                )
            project.write({'state': 'paused'})

    def action_resume(self):
        """Пауза → В работе."""
        for project in self:
            if project.state != 'paused':
                raise UserError(
                    'Возобновить можно только объект в статусе "Пауза".'
                )
            project.write({'state': 'active'})

    def action_done(self):
        """В работе → Завершён."""
        for project in self:
            if project.state != 'active':
                raise UserError(
                    'Завершить можно только объект в статусе "В работе".'
                )
            project.write({'state': 'done'})
