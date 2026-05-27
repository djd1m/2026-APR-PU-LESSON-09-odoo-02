# -*- coding: utf-8 -*-
from odoo import models, fields, api


class SuPayment(models.Model):
    _name = 'su.payment'
    _description = 'Платёж'
    _order = 'create_date desc'

    subscription_id = fields.Many2one(
        'su.subscription',
        string='Подписка',
        required=True,
        ondelete='restrict',
    )
    company_id = fields.Many2one(
        'res.company',
        string='Компания',
        related='subscription_id.company_id',
        store=True,
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Валюта',
        related='company_id.currency_id',
        store=True,
    )

    # Monetary — always Decimal via fields.Monetary + currency_id
    amount = fields.Monetary(
        string='Сумма',
        currency_field='currency_id',
        required=True,
    )
    status = fields.Selection([
        ('pending', 'Ожидает'),
        ('success', 'Успешно'),
        ('failed', 'Ошибка'),
        ('refunded', 'Возврат'),
    ], string='Статус', default='pending', required=True)

    yukassa_payment_id = fields.Char(
        string='YuKassa Payment ID',
        index=True,
    )
    payment_method = fields.Selection([
        ('bank_card', 'Банковская карта'),
        ('sbp', 'СБП'),
        ('yoo_money', 'ЮMoney'),
    ], string='Способ оплаты')

    description = fields.Char(string='Описание')
    paid_at = fields.Datetime(string='Дата оплаты')
    failed_at = fields.Datetime(string='Дата ошибки')
    failure_reason = fields.Char(string='Причина ошибки')

    # Refund fields — Monetary with currency_id (Decimal, never Float)
    refund_amount = fields.Monetary(
        string='Сумма возврата',
        currency_field='currency_id',
    )
    refund_reason = fields.Char(string='Причина возврата')

    retry_count = fields.Integer(string='Попытки', default=0)
    next_retry_at = fields.Datetime(string='Следующая попытка')

    _sql_constraints = [
        (
            'yukassa_payment_id_unique',
            'UNIQUE(yukassa_payment_id)',
            'YuKassa Payment ID must be unique',
        ),
        (
            'amount_positive',
            'CHECK(amount > 0)',
            'Amount must be positive',
        ),
    ]
