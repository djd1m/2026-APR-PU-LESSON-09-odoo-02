# -*- coding: utf-8 -*-
{
    'name': 'СтройУправ Фотофиксация',
    'version': '17.0.2.0.0',
    'category': 'Construction',
    'summary': 'Фотофиксация строительных работ с геотегами и S3 хранилищем',
    'description': """
        Загрузка и хранение фотоотчётов с привязкой к объектам и задачам.
        - Автоматические геотеги (EXIF GPS) и timestamp
        - S3 (MinIO) хранилище для фото
        - Валидация файлов: MIME, размер до 20 МБ, блокировка исполняемых
        - Автообновление прогресса задачи при загрузке фото
        - Галерея с фильтрами и группировкой
    """,
    'author': 'СтройУправ',
    'depends': ['su_base', 'su_project', 'su_task'],
    'data': [
        'security/ir.model.access.csv',
        'security/su_photo_rules.xml',
        'views/su_photo_views.xml',
    ],
    'external_dependencies': {
        'python': ['boto3', 'PIL', 'magic'],
    },
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
