# -*- coding: utf-8 -*-
{
    'name': 'СтройУправ Биллинг',
    'version': '17.0.1.0.0',
    'category': 'Construction',
    'summary': 'Подписки и платежи через ЮKassa',
    'description': """
        Управление подписками: тарифные планы, trial-период,
        интеграция с ЮKassa для рекуррентных платежей.
    """,
    'author': 'СтройУправ',
    'depends': ['su_base'],
    'data': [
        'security/ir.model.access.csv',
        'views/su_subscription_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
