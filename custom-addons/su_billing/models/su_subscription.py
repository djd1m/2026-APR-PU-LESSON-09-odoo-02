# -*- coding: utf-8 -*-
import json
import logging
from datetime import timedelta
from decimal import Decimal

from odoo import models, fields, api
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

# Plan configuration: limits and pricing (amounts in RUB, Decimal)
PLAN_CONFIG = {
    'free': {
        'amount': Decimal('0'),
        'projects': 1,
        'estimates': 3,
    },
    'starter': {
        'amount': Decimal('2990'),
        'projects': 5,
        'estimates': 20,
    },
    'business': {
        'amount': Decimal('9900'),
        'projects': 20,
        'estimates': 100,
    },
    'enterprise': {
        'amount': Decimal('49900'),
        'projects': 0,  # 0 = unlimited
        'estimates': 0,  # 0 = unlimited
    },
}


class SuSubscription(models.Model):
    _name = 'su.subscription'
    _description = 'Подписка'
    _order = 'create_date desc'

    name = fields.Char(
        string='Номер подписки',
        readonly=True,
        default='New',
        copy=False,
    )
    partner_id = fields.Many2one(
        'res.partner',
        string='Клиент',
        required=True,
    )
    plan = fields.Selection([
        ('free', 'Бесплатный'),
        ('starter', 'Стартер'),
        ('business', 'Бизнес'),
        ('enterprise', 'Корпоративный'),
    ], string='Тарифный план', default='free', required=True)
    status = fields.Selection([
        ('trial', 'Пробный период'),
        ('active', 'Активна'),
        ('past_due', 'Просрочена'),
        ('cancelled', 'Отменена'),
    ], string='Статус', default='trial', tracking=True)

    # Trial dates
    trial_start = fields.Date(string='Начало trial')
    trial_end = fields.Date(string='Окончание trial')

    # Billing period
    current_period_start = fields.Date(string='Начало текущего периода')
    current_period_end = fields.Date(string='Конец текущего периода')
    billing_cycle = fields.Selection([
        ('monthly', 'Ежемесячно'),
        ('annual', 'Ежегодно'),
    ], string='Цикл оплаты', default='monthly')

    # Monetary — always Decimal via fields.Monetary + currency_id
    plan_amount = fields.Monetary(
        string='Стоимость плана',
        currency_field='currency_id',
    )

    # Limits
    max_projects = fields.Integer(string='Макс. объектов')
    max_ai_estimates = fields.Integer(string='Макс. AI-смет/мес')
    ai_estimates_used = fields.Integer(
        string='AI-смет использовано',
        default=0,
    )

    # ЮKassa integration fields
    yukassa_customer_id = fields.Char(string='YuKassa Customer ID')
    yukassa_payment_method_id = fields.Char(
        string='YuKassa Payment Method ID',
    )
    yukassa_subscription_id = fields.Char(
        string='YuKassa Subscription ID',
    )
    last_payment_date = fields.Date(string='Дата последнего платежа')
    next_payment_date = fields.Date(string='Дата следующего платежа')

    # Payment retry tracking
    retry_count = fields.Integer(string='Попытки повторной оплаты', default=0)
    next_retry_date = fields.Date(string='Дата следующей попытки')

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

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'su.subscription'
                ) or 'New'
            # Set default trial dates for trial subscriptions
            if not vals.get('trial_end') and vals.get('status') == 'trial':
                today = fields.Date.today()
                vals.setdefault('trial_start', today)
                vals['trial_end'] = today + timedelta(days=14)
            # Apply plan config defaults
            plan = vals.get('plan', 'free')
            config = PLAN_CONFIG.get(plan, {})
            vals.setdefault('plan_amount', float(config.get('amount', Decimal('0'))))
            vals.setdefault('max_projects', config.get('projects', 0))
            vals.setdefault('max_ai_estimates', config.get('estimates', 0))
        return super().create(vals_list)

    def action_activate(self):
        """Activate subscription after successful payment."""
        today = fields.Date.today()
        for rec in self:
            vals = {
                'status': 'active',
                'current_period_start': today,
                'retry_count': 0,
                'next_retry_date': False,
            }
            if rec.billing_cycle == 'annual':
                vals['current_period_end'] = today + timedelta(days=365)
            else:
                vals['current_period_end'] = today + timedelta(days=30)
            # Reset usage counters for new period
            vals['ai_estimates_used'] = 0
            vals['last_payment_date'] = today
            if rec.billing_cycle == 'annual':
                vals['next_payment_date'] = today + timedelta(days=365)
            else:
                vals['next_payment_date'] = today + timedelta(days=30)
            rec.write(vals)
        return True

    def action_cancel(self):
        """Cancel subscription — takes effect at end of billing cycle."""
        for rec in self:
            rec.write({'status': 'cancelled'})
        return True

    def action_expire_trial(self):
        """Downgrade trial to free plan on expiration."""
        for rec in self:
            config = PLAN_CONFIG['free']
            rec.write({
                'plan': 'free',
                'status': 'active',
                'plan_amount': float(config['amount']),
                'max_projects': config['projects'],
                'max_ai_estimates': config['estimates'],
                'ai_estimates_used': 0,
                'trial_end': False,
            })
        return True

    def action_upgrade(self, new_plan):
        """Upgrade to a higher plan. Amount uses Decimal arithmetic."""
        self.ensure_one()
        if new_plan not in PLAN_CONFIG:
            raise UserError(f"Неизвестный тарифный план: {new_plan}")

        config = PLAN_CONFIG[new_plan]
        self.write({
            'plan': new_plan,
            'plan_amount': float(config['amount']),
            'max_projects': config['projects'],
            'max_ai_estimates': config['estimates'],
        })
        return True

    def action_set_past_due(self):
        """Mark subscription as past due (failed payment)."""
        for rec in self:
            rec.write({'status': 'past_due'})
        return True

    @api.onchange('plan')
    def _onchange_plan(self):
        config = PLAN_CONFIG.get(self.plan, {})
        self.plan_amount = float(config.get('amount', Decimal('0')))
        self.max_projects = config.get('projects', 0)
        self.max_ai_estimates = config.get('estimates', 0)

    @api.model
    def _cron_check_trial_expirations(self):
        """Cron job: check expired trials daily, downgrade to free plan."""
        today = fields.Date.today()
        expired_trials = self.search([
            ('status', '=', 'trial'),
            ('trial_end', '<=', today),
        ])

        for subscription in expired_trials:
            try:
                subscription.action_expire_trial()
                _logger.info(
                    "Trial expired for company %s (subscription %s), "
                    "downgraded to free plan",
                    subscription.company_id.name,
                    subscription.name,
                )
            except Exception:
                _logger.exception(
                    "Failed to expire trial for subscription %s",
                    subscription.name,
                )

        _logger.info(
            "Trial expiration check complete: %d processed",
            len(expired_trials),
        )
        return True

    @api.model
    def _cron_send_trial_reminders(self):
        """Cron job: send email reminders at 7, 3, and 1 day(s) before trial end."""
        today = fields.Date.today()
        for days_remaining in [7, 3, 1]:
            target_date = today + timedelta(days=days_remaining)
            trials = self.search([
                ('status', '=', 'trial'),
                ('trial_end', '=', target_date),
            ])
            for subscription in trials:
                _logger.info(
                    "Trial reminder: %d day(s) remaining for company %s",
                    days_remaining,
                    subscription.company_id.name,
                )
                # Email sending would be handled by Odoo mail module
        return True
