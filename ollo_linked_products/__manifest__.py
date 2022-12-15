# -*- coding: utf-8 -*-
{
    'name': "Ollo Linked Products",
    'summary': """
       Ollo Linked Products""",
    'description': """
       Ollo Linked Products
    """,
    'category': 'Customizations',
    'support': 'felix@fletscher.de',
    'website': 'https://www.fletscher.de',
    'version': '16.0.0.0.4',
    'images': ['static/description/icon.png'],
    'depends': ['sale_management','stock','sale_subscription','website_sale'],
    'data': [
        'security/ir.model.access.csv',
        'views/product_template_views.xml',
        'views/template.xml',
    ],
    'installable': True,
    'application': True,
    'images': [],
    'sequence': 1,
    'license': 'Other proprietary',
}
