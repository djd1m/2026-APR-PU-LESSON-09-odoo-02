# -*- coding: utf-8 -*-
{
    'name': 'СтройУправ Base',
    'version': '17.0.1.0.0',
    'category': 'Construction',
    'summary': 'Base module for СтройУправ construction ERP',
    'description': """
        Base module providing security groups and shared configuration
        for all СтройУправ modules.
    """,
    'author': 'СтройУправ',
    'depends': ['base', 'web'],
    'data': [
        'security/security_groups.xml',
        'security/ir.model.access.csv',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
