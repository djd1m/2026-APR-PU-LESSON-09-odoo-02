# -*- coding: utf-8 -*-
from odoo import models, fields


class SuWebhookLog(models.Model):
    _name = 'su.webhook.log'
    _description = 'Лог вебхуков'
    _order = 'create_date desc'

    idempotency_key = fields.Char(
        string='Ключ идемпотентности',
        required=True,
        index=True,
    )
    event_type = fields.Char(string='Тип события')
    payload = fields.Text(string='Данные (JSON)')
    source_ip = fields.Char(string='IP источника')
    signature_valid = fields.Boolean(string='Подпись валидна')
    processed_at = fields.Datetime(string='Обработано')

    _sql_constraints = [
        (
            'idempotency_key_unique',
            'UNIQUE(idempotency_key)',
            'Idempotency key must be unique',
        ),
    ]
