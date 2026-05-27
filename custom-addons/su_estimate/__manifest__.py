# -*- coding: utf-8 -*-
{
    'name': 'СтройУправ Сметы',
    'version': '17.0.1.0.0',
    'category': 'Construction',
    'summary': 'AI-сметы по ГЭСН/ФЕР',
    'description': """
        Генерация и управление строительными сметами.
        Поддержка расценок ГЭСН/ФЕР, индексов Минстроя,
        AI-генерация из текста и чертежей.
    """,
    'author': 'СтройУправ',
    'depends': ['su_base', 'su_project'],
    'data': [
        'security/ir.model.access.csv',
        'views/su_estimate_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
