# -*- coding: utf-8 -*-
{
    'name': 'СтройУправ Фотофиксация',
    'version': '17.0.1.0.0',
    'category': 'Construction',
    'summary': 'Фотофиксация строительных работ с геотегами',
    'description': """
        Загрузка и хранение фотоотчётов с привязкой к объектам и задачам.
        Автоматические геотеги (GPS), хронологическая галерея.
    """,
    'author': 'СтройУправ',
    'depends': ['su_base', 'su_project', 'su_task'],
    'data': [
        'security/ir.model.access.csv',
        'views/su_photo_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
