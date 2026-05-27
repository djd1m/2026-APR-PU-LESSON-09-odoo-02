# -*- coding: utf-8 -*-
import logging

from odoo import models, fields
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)

# Valid selection keys — used for server-side validation
COMPANY_TYPE_KEYS = {'repair', 'contractor', 'private_master', 'client'}
OBJECT_COUNT_KEYS = {'1_3', '4_10', '11_50', '50_plus'}
BIGGEST_PAIN_KEYS = {'budget', 'deadlines', 'documents', 'communication'}

# Maximum length for current_tools free-text field
MAX_TOOLS_LENGTH = 500

# Plan recommendation matrix: (company_type, object_count) -> plan
_PLAN_MATRIX = {
    # client always gets free
    ('client', '1_3'): 'free',
    ('client', '4_10'): 'free',
    ('client', '11_50'): 'free',
    ('client', '50_plus'): 'free',
    # private_master scales from free to business
    ('private_master', '1_3'): 'free',
    ('private_master', '4_10'): 'starter',
    ('private_master', '11_50'): 'business',
    ('private_master', '50_plus'): 'business',
    # repair company scales from starter to enterprise
    ('repair', '1_3'): 'starter',
    ('repair', '4_10'): 'business',
    ('repair', '11_50'): 'enterprise',
    ('repair', '50_plus'): 'enterprise',
    # contractor starts at business
    ('contractor', '1_3'): 'business',
    ('contractor', '4_10'): 'enterprise',
    ('contractor', '11_50'): 'enterprise',
    ('contractor', '50_plus'): 'enterprise',
}

# Default plan when matrix lookup fails
_DEFAULT_PLAN = 'starter'


class SuOnboarding(models.Model):
    _name = 'su.onboarding'
    _description = 'Onboarding quiz answers'
    _rec_name = 'partner_id'
    _order = 'create_date desc'

    _sql_constraints = [
        (
            'partner_company_uniq',
            'UNIQUE(partner_id, company_id)',
            'One onboarding record per partner per company.',
        ),
    ]

    partner_id = fields.Many2one(
        'res.partner',
        string='Партнёр',
        required=True,
        ondelete='cascade',
        index=True,
    )
    company_type = fields.Selection(
        [
            ('repair', 'Ремонтная компания'),
            ('contractor', 'Генподрядчик'),
            ('private_master', 'Частный мастер'),
            ('client', 'Заказчик'),
        ],
        string='Тип компании',
    )
    object_count = fields.Selection(
        [
            ('1_3', '1-3 объекта'),
            ('4_10', '4-10 объектов'),
            ('11_50', '11-50 объектов'),
            ('50_plus', '50+ объектов'),
        ],
        string='Количество объектов',
    )
    current_tools = fields.Char(
        string='Текущие инструменты',
        help='Comma-separated: excel, 1c, whatsapp, other',
    )
    biggest_pain = fields.Selection(
        [
            ('budget', 'Бюджеты'),
            ('deadlines', 'Сроки'),
            ('documents', 'Документы'),
            ('communication', 'Коммуникация'),
        ],
        string='Главная проблема',
    )
    recommended_plan = fields.Selection(
        [
            ('free', 'Бесплатный'),
            ('starter', 'Стартер'),
            ('business', 'Бизнес'),
            ('enterprise', 'Корпоративный'),
        ],
        string='Рекомендуемый план',
        readonly=True,
    )
    completed = fields.Boolean(
        string='Завершён',
        default=False,
    )
    skipped = fields.Boolean(
        string='Пропущен',
        default=False,
    )
    completed_at = fields.Datetime(
        string='Дата завершения',
    )
    company_id = fields.Many2one(
        'res.company',
        string='Компания',
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )

    # ── Public API ─────────────────────────────────────────────

    def action_submit(self, vals):
        """Submit quiz answers, compute recommendation, mark completed.

        :param vals: dict with keys company_type, object_count,
                     current_tools, biggest_pain
        :raises ValidationError: if any value is invalid
        """
        self.ensure_one()
        self._validate_answers(vals)

        plan = self._compute_recommended_plan(
            vals.get('company_type'),
            vals.get('object_count'),
        )

        write_vals = {
            'company_type': vals.get('company_type'),
            'object_count': vals.get('object_count'),
            'current_tools': vals.get('current_tools', ''),
            'biggest_pain': vals.get('biggest_pain'),
            'recommended_plan': plan,
            'completed': True,
            'skipped': False,
            'completed_at': fields.Datetime.now(),
        }
        self.write(write_vals)
        return {'recommended_plan': plan}

    def action_skip(self):
        """Skip quiz, apply safe defaults."""
        self.ensure_one()
        self.write({
            'completed': True,
            'skipped': True,
            'recommended_plan': _DEFAULT_PLAN,
            'completed_at': fields.Datetime.now(),
        })
        return {'type': 'ir.actions.act_window_close'}

    # ── Private helpers ────────────────────────────────────────

    @staticmethod
    def _compute_recommended_plan(company_type, object_count):
        """Lookup recommended plan from matrix.

        :returns: plan key string
        """
        if not company_type or not object_count:
            return _DEFAULT_PLAN
        return _PLAN_MATRIX.get(
            (company_type, object_count),
            _DEFAULT_PLAN,
        )

    @staticmethod
    def _validate_answers(vals):
        """Server-side validation of all selection values.

        :raises ValidationError: on invalid value
        """
        ct = vals.get('company_type')
        if ct and ct not in COMPANY_TYPE_KEYS:
            raise ValidationError(
                "Некорректное значение: company_type = %s" % ct
            )

        oc = vals.get('object_count')
        if oc and oc not in OBJECT_COUNT_KEYS:
            raise ValidationError(
                "Некорректное значение: object_count = %s" % oc
            )

        bp = vals.get('biggest_pain')
        if bp and bp not in BIGGEST_PAIN_KEYS:
            raise ValidationError(
                "Некорректное значение: biggest_pain = %s" % bp
            )

        tools = vals.get('current_tools', '')
        if len(tools) > MAX_TOOLS_LENGTH:
            raise ValidationError(
                "current_tools превышает максимальную длину (%d символов)"
                % MAX_TOOLS_LENGTH
            )
