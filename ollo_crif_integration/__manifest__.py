# -*- coding: utf-8 -*-
{
    'name': "Ollo CRIF Integration",
    'summary': """
        Ollo CRIF Integration""",
    'description': """
        Ollo CRIF Integration
    """,
    'category': 'Customizations',
    'support': 'felix@fletscher.de',
    'website': 'https://www.fletscher.de',
    'version': '16.0.0.0.1',
    'images': ['static/description/icon.png'],
    'depends': ['ollo_linked_products'],
    'data': [
        'security/ir.model.access.csv',
        'views/sale_order_views.xml',
        'views/res_partner_views.xml',
    ],
    'installable': True,
    'application': True,
    'images': [],
    'sequence': 1,
    'license': 'Other proprietary',
}
