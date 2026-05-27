# -*- coding: utf-8 -*-
from odoo import models, fields, api


class SuEstimate(models.Model):
    _name = 'su.estimate'
    _description = 'Строительная смета'
    _order = 'create_date desc'

    name = fields.Char(string='Название', required=True)
    project_id = fields.Many2one(
        'su.project',
        string='Объект',
        ondelete='cascade',
    )
    description = fields.Text(string='Описание работ')
    total_amount = fields.Monetary(
        string='Итого',
        compute='_compute_total',
        store=True,
    )
    state = fields.Selection([
        ('draft', 'Черновик'),
        ('confirmed', 'Утверждена'),
        ('archived', 'Архив'),
    ], string='Статус', default='draft', tracking=True)
    ai_generated = fields.Boolean(string='Сгенерирована AI', default=False)
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
    item_ids = fields.One2many(
        'su.estimate.item',
        'estimate_id',
        string='Позиции сметы',
    )

    @api.depends('item_ids.amount')
    def _compute_total(self):
        for estimate in self:
            estimate.total_amount = sum(estimate.item_ids.mapped('amount'))


class SuEstimateItem(models.Model):
    _name = 'su.estimate.item'
    _description = 'Позиция сметы'
    _order = 'sequence, id'

    estimate_id = fields.Many2one(
        'su.estimate',
        string='Смета',
        ondelete='cascade',
        required=True,
    )
    sequence = fields.Integer(string='Порядок', default=10)
    gesn_code = fields.Char(string='Код ГЭСН')
    name = fields.Char(string='Наименование работ', required=True)
    unit = fields.Char(string='Ед. изм.')
    quantity = fields.Float(string='Количество', digits=(16, 4))
    unit_price = fields.Monetary(string='Цена за ед.')
    amount = fields.Monetary(
        string='Сумма',
        compute='_compute_amount',
        store=True,
    )
    company_id = fields.Many2one(
        'res.company',
        string='Компания',
        related='estimate_id.company_id',
        store=True,
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Валюта',
        related='estimate_id.currency_id',
        store=True,
    )

    @api.depends('quantity', 'unit_price')
    def _compute_amount(self):
        for item in self:
            item.amount = item.quantity * item.unit_price
