# -*- coding: utf-8 -*-
{
    'name': 'СтройУправ Биллинг',
    'version': '17.0.1.1.0',
    'category': 'Construction',
    'summary': 'Аутентификация, подписки и платежи через ЮKassa',
    'description': """
        Аутентификация (JWT в httpOnly cookies), управление подписками:
        тарифные планы, trial-период 14 дней, интеграция с ЮKassa
        для рекуррентных платежей, HMAC-верификация вебхуков.
    """,
    'author': 'СтройУправ',
    'depends': ['su_base'],
    'data': [
        'security/ir.model.access.csv',
        'data/cron.xml',
        'views/su_subscription_views.xml',
    ],
    'external_dependencies': {
        'python': ['bcrypt'],
    },
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
