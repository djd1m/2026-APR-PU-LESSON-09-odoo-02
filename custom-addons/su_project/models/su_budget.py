# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError


class SuExpense(models.Model):
    _name = 'su.expense'
    _description = 'Расход по объекту'
    _inherit = ['mail.thread']
    _order = 'expense_date desc, id desc'

    # ── Core fields ──────────────────────────────────────────
    name = fields.Char(string='Описание', required=True)
    project_id = fields.Many2one(
        'su.project',
        string='Объект',
        required=True,
        ondelete='cascade',
        index=True,
    )
    amount = fields.Monetary(
        string='Сумма',
        currency_field='currency_id',
        required=True,
    )
    category = fields.Selection([
        ('materials', 'Материалы'),
        ('labor', 'Работа'),
        ('equipment', 'Оборудование'),
        ('transport', 'Транспорт'),
        ('other', 'Прочее'),
    ], string='Категория', required=True, default='materials')
    expense_date = fields.Date(
        string='Дата расхода',
        required=True,
        default=fields.Date.today,
    )
    notes = fields.Text(string='Примечания')

    # ── Attachment ───────────────────────────────────────────
    receipt_attachment = fields.Binary(
        string='Чек / Квитанция',
        attachment=True,
    )
    receipt_filename = fields.Char(string='Имя файла')

    # ── State ────────────────────────────────────────────────
    state = fields.Selection([
        ('draft', 'Черновик'),
        ('confirmed', 'Подтверждён'),
        ('cancelled', 'Отменён'),
    ], string='Статус', default='draft', required=True, tracking=True)

    # ── Tenant isolation ─────────────────────────────────────
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

    # ── State transition actions ─────────────────────────────

    def action_confirm(self):
        """Черновик → Подтверждён. Triggers budget alert check."""
        for expense in self:
            if expense.state != 'draft':
                raise UserError(
                    'Подтвердить можно только расход в статусе "Черновик".'
                )
            expense.write({'state': 'confirmed'})
        # Проверка бюджетного алерта на затронутых проектах
        self.mapped('project_id')._check_budget_alert()

    def action_cancel(self):
        """Подтверждён → Отменён."""
        for expense in self:
            if expense.state != 'confirmed':
                raise UserError(
                    'Отменить можно только подтверждённый расход.'
                )
            expense.write({'state': 'cancelled'})

    def action_reset_draft(self):
        """Отменён → Черновик."""
        for expense in self:
            if expense.state != 'cancelled':
                raise UserError(
                    'Вернуть в черновик можно только отменённый расход.'
                )
            expense.write({'state': 'draft'})
