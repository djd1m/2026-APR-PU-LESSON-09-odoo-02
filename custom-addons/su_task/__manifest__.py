# -*- coding: utf-8 -*-
{
    'name': 'СтройУправ Задачи',
    'version': '17.0.2.0.0',
    'category': 'Construction',
    'summary': 'Управление задачами и бригадами',
    'description': """
        Задачи строительных объектов с state machine,
        назначение бригад, зависимости между задачами,
        подзадачи, канбан, уведомления, RBAC.
    """,
    'author': 'СтройУправ',
    'depends': ['su_base', 'su_project', 'mail', 'su_photo'],
    'data': [
        'security/ir.model.access.csv',
        'security/su_task_rules.xml',
        'views/su_task_views.xml',
        'views/su_brigade_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
