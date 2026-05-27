# -*- coding: utf-8 -*-
from odoo import models, fields, api
from datetime import timedelta


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
    trial_end = fields.Date(string='Окончание trial')
    plan_amount = fields.Monetary(string='Стоимость плана')
    max_projects = fields.Integer(string='Макс. объектов')
    max_ai_estimates = fields.Integer(string='Макс. AI-смет/мес')
    ai_estimates_used = fields.Integer(
        string='AI-смет использовано',
        default=0,
    )

    # YuKassa integration fields
    yukassa_customer_id = fields.Char(string='YuKassa Customer ID')
    yukassa_payment_method_id = fields.Char(
        string='YuKassa Payment Method ID',
    )
    yukassa_subscription_id = fields.Char(
        string='YuKassa Subscription ID',
    )
    last_payment_date = fields.Date(string='Дата последнего платежа')
    next_payment_date = fields.Date(string='Дата следующего платежа')

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
            # Set default trial end to 14 days from now
            if not vals.get('trial_end') and vals.get('status') == 'trial':
                vals['trial_end'] = fields.Date.today() + timedelta(days=14)
        return super().create(vals_list)

    def action_activate(self):
        self.write({'status': 'active'})

    def action_cancel(self):
        self.write({'status': 'cancelled'})

    @api.onchange('plan')
    def _onchange_plan(self):
        plan_config = {
            'free': {'amount': 0, 'projects': 1, 'estimates': 3},
            'starter': {'amount': 2990, 'projects': 5, 'estimates': 20},
            'business': {'amount': 9900, 'projects': 20, 'estimates': 100},
            'enterprise': {'amount': 49900, 'projects': 0, 'estimates': 0},
        }
        config = plan_config.get(self.plan, {})
        self.plan_amount = config.get('amount', 0)
        self.max_projects = config.get('projects', 0)
        self.max_ai_estimates = config.get('estimates', 0)
