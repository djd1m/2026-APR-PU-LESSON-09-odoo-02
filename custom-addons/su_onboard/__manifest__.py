# -*- coding: utf-8 -*-
{
    'name': 'СтройУправ Онбординг',
    'version': '17.0.1.0.0',
    'category': 'Construction',
    'summary': 'Onboarding quiz: 4 вопроса, персонализация, рекомендация тарифа',
    'description': """
        Wizard-style onboarding quiz presented after first login.
        4 questions: company type, number of objects, current tools,
        biggest pain point. Computes recommended pricing plan.
        Skippable. One-time per user per company.
    """,
    'author': 'СтройУправ',
    'depends': ['su_base', 'su_project'],
    'data': [
        'security/ir.model.access.csv',
        'security/su_onboarding_rule.xml',
        'views/su_onboarding_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
