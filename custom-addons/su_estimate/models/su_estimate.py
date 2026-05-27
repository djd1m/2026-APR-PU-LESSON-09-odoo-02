# -*- coding: utf-8 -*-
import json
import logging

import requests
from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)

# FastAPI AI service URL — configured via Odoo system parameter
_AI_SERVICE_PARAM = "su_estimate.ai_service_url"
_AI_SERVICE_DEFAULT = "http://ai-service:8000"
_AI_TIMEOUT = 60  # seconds


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
    region = fields.Char(string='Регион', default='moscow')
    area_sqm = fields.Float(string='Площадь м²', digits=(16, 2))
    project_type = fields.Char(string='Тип объекта', default='квартира')

    subtotal = fields.Monetary(
        string='Итого без НДС',
        compute='_compute_totals',
        store=True,
    )
    nds_rate = fields.Float(string='Ставка НДС', default=0.20, digits=(4, 2))
    nds_amount = fields.Monetary(
        string='НДС',
        compute='_compute_totals',
        store=True,
    )
    total_amount = fields.Monetary(
        string='Итого с НДС',
        compute='_compute_totals',
        store=True,
    )
    state = fields.Selection([
        ('draft', 'Черновик'),
        ('processing', 'Генерация AI'),
        ('completed', 'Сформирована'),
        ('confirmed', 'Утверждена'),
        ('archived', 'Архив'),
    ], string='Статус', default='draft', tracking=True)
    ai_generated = fields.Boolean(string='Сгенерирована AI', default=False)
    ai_error = fields.Text(string='Ошибка AI', readonly=True)

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

    @api.depends('item_ids.amount', 'nds_rate')
    def _compute_totals(self):
        for estimate in self:
            subtotal = sum(estimate.item_ids.mapped('amount'))
            nds = subtotal * (estimate.nds_rate or 0.20)
            estimate.subtotal = subtotal
            estimate.nds_amount = nds
            estimate.total_amount = subtotal + nds

    # ------------------------------------------------------------------
    # AI Estimate Generation
    # ------------------------------------------------------------------

    def action_generate_ai_estimate(self):
        """Call FastAPI AI service to generate estimate from description.

        Creates estimate items from AI response. Uses requests library
        to call the internal FastAPI service.
        """
        self.ensure_one()

        if not self.description or len(self.description) < 20:
            raise UserError(
                'Описание работ должно содержать не менее 20 символов '
                'для генерации AI-сметы.'
            )

        if not self.area_sqm or self.area_sqm <= 0:
            raise UserError('Укажите площадь объекта (> 0 м²).')

        ai_url = self._get_ai_service_url()

        self.write({'state': 'processing', 'ai_error': False})

        try:
            response = requests.post(
                f"{ai_url}/api/v1/estimate/generate",
                json={
                    'description': self.description,
                    'area_sqm': self.area_sqm,
                    'project_type': self.project_type or 'квартира',
                    'region': self.region or 'moscow',
                },
                timeout=_AI_TIMEOUT,
            )
            response.raise_for_status()
            data = response.json()
        except requests.Timeout:
            self.write({
                'state': 'draft',
                'ai_error': 'Таймаут AI-сервиса. Попробуйте позже.',
            })
            raise UserError('AI-сервис не ответил в отведённое время.')
        except requests.ConnectionError:
            self.write({
                'state': 'draft',
                'ai_error': 'AI-сервис недоступен.',
            })
            raise UserError(
                'AI-сервис недоступен. Проверьте, что сервис запущен.'
            )
        except requests.HTTPError as exc:
            error_detail = ''
            try:
                error_detail = exc.response.json().get('detail', str(exc))
            except Exception:
                error_detail = str(exc)
            self.write({
                'state': 'draft',
                'ai_error': f'Ошибка AI: {error_detail}',
            })
            raise UserError(f'Ошибка AI-сервиса: {error_detail}')

        # Remove old AI-generated items (keep manual overrides)
        old_ai_items = self.item_ids.filtered(
            lambda i: not i.manual_override
        )
        old_ai_items.unlink()

        # Create new estimate items from AI response
        items_data = data.get('items', [])
        for seq, item in enumerate(items_data, start=10):
            self.env['su.estimate.item'].create({
                'estimate_id': self.id,
                'sequence': seq,
                'gesn_code': item.get('gesn_code', ''),
                'name': item.get('name', ''),
                'unit': item.get('unit', ''),
                'quantity': float(item.get('quantity', 0)),
                'unit_price': float(item.get('unit_price', 0)),
                'is_overpriced': item.get('is_overpriced', False),
                'match_score': float(item.get('match_score', 0)),
                'index_coefficient': float(
                    item.get('index_coefficient', 1.0)
                ),
            })

        self.write({
            'state': 'completed',
            'ai_generated': True,
            'ai_error': False,
        })

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'AI-смета готова',
                'message': f'Создано {len(items_data)} позиций.',
                'type': 'success',
                'sticky': False,
            },
        }

    # ------------------------------------------------------------------
    # Export actions
    # ------------------------------------------------------------------

    def action_export_pdf(self):
        """Generate and download PDF export of this estimate."""
        self.ensure_one()

        if not self.item_ids:
            raise UserError('Смета не содержит позиций.')

        ai_url = self._get_ai_service_url()

        items_payload = []
        for item in self.item_ids:
            items_payload.append({
                'gesn_code': item.gesn_code or '',
                'name': item.name,
                'unit': item.unit or '',
                'quantity': str(item.quantity),
                'unit_price': str(item.unit_price),
                'amount': str(item.amount),
                'is_overpriced': item.is_overpriced,
            })

        try:
            response = requests.post(
                f"{ai_url}/api/v1/estimate/render-pdf",
                json={
                    'items': items_payload,
                    'subtotal': str(self.subtotal),
                    'nds_amount': str(self.nds_amount),
                    'grand_total': str(self.total_amount),
                    'company_name': self.company_id.name if self.company_id else '',
                    'company_inn': (
                        self.company_id.vat if self.company_id else ''
                    ),
                },
                timeout=30,
            )
            response.raise_for_status()
        except Exception as exc:
            _logger.exception("PDF export failed: %s", exc)
            raise UserError(f'Ошибка генерации PDF: {exc}')

        # Create attachment with PDF content
        attachment = self.env['ir.attachment'].create({
            'name': f'Смета_{self.name}.pdf',
            'type': 'binary',
            'datas': self.env['base'].sudo()._encode_base64(
                response.content
            ) if hasattr(self.env['base'], '_encode_base64') else
            __import__('base64').b64encode(response.content),
            'res_model': self._name,
            'res_id': self.id,
            'mimetype': 'application/pdf',
        })

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'new',
        }

    def action_export_excel(self):
        """Export estimate to Excel format.

        TODO: implement Excel export via openpyxl when needed.
        For MVP, PDF export covers the primary use case.
        """
        self.ensure_one()
        raise UserError(
            'Экспорт в Excel будет доступен в следующей версии. '
            'Используйте экспорт в PDF.'
        )

    # ------------------------------------------------------------------
    # Workflow actions
    # ------------------------------------------------------------------

    def action_confirm(self):
        """Confirm the estimate — marks it as approved."""
        for estimate in self:
            if estimate.state not in ('completed', 'draft'):
                raise UserError(
                    'Утвердить можно только сформированную или черновую смету.'
                )
            if not estimate.item_ids:
                raise UserError('Нельзя утвердить пустую смету.')
            estimate.write({'state': 'confirmed'})

    def action_archive(self):
        """Archive the estimate."""
        for estimate in self:
            if estimate.state == 'processing':
                raise UserError(
                    'Нельзя архивировать смету в процессе генерации.'
                )
            estimate.write({'state': 'archived'})

    def action_reset_draft(self):
        """Reset estimate to draft state."""
        for estimate in self:
            if estimate.state == 'processing':
                raise UserError(
                    'Нельзя сбросить смету в процессе генерации.'
                )
            estimate.write({'state': 'draft'})

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_ai_service_url(self):
        """Get AI service URL from system parameters."""
        return (
            self.env['ir.config_parameter']
            .sudo()
            .get_param(_AI_SERVICE_PARAM, _AI_SERVICE_DEFAULT)
        ).rstrip('/')


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
    index_coefficient = fields.Float(
        string='Индекс Минстроя',
        digits=(8, 4),
        default=1.0,
    )
    amount = fields.Monetary(
        string='Сумма',
        compute='_compute_amount',
        store=True,
    )
    match_score = fields.Float(
        string='AI confidence',
        digits=(4, 2),
        default=0.0,
    )
    is_overpriced = fields.Boolean(
        string='Выше рыночной',
        default=False,
    )
    manual_override = fields.Boolean(
        string='Ручная корректировка',
        default=False,
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

    def write(self, vals):
        """Mark item as manually overridden when user edits quantity or price."""
        if 'quantity' in vals or 'unit_price' in vals:
            # Only mark as manual if not coming from AI generation
            if not self.env.context.get('from_ai_generation'):
                vals['manual_override'] = True
        return super().write(vals)
