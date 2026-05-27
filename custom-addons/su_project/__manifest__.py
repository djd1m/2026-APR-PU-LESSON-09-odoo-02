# -*- coding: utf-8 -*-
{
    'name': 'СтройУправ Объекты',
    'version': '17.0.1.0.0',
    'category': 'Construction',
    'summary': 'Управление строительными объектами',
    'description': """
        Строительные объекты: карточки, прогресс, бюджет план/факт,
        dashboard с цветовой индикацией.
    """,
    'author': 'СтройУправ',
    'depends': ['su_base'],
    'data': [
        'security/ir.model.access.csv',
        'views/su_project_views.xml',
        'views/su_project_dashboard.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
