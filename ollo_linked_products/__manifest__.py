# -*- coding: utf-8 -*-
{
    'name': "Ollo Linked Products",
    'summary': """
        Linked Products""",
    'description': """
        Linked Products
    """,
    'category': 'Customizations',
    'support': 'felix@fletscher.de',
    'website': 'https://www.fletscher.de',
    'version': '16.0.0.0.1',
    'images': ['static/description/icon.png'],
    # any module necessary for this one to work correctly
    'depends': ['sale_management','stock','sale_subscription','website_sale'],
    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/product_template_views.xml',
        'views/sale_order_views.xml',
        'views/res_partner_views.xml',
        'views/template.xml',
    ],
    'installable': True,
    'application': True,
    'images': [],
    'sequence': 1,
    'license': 'Other proprietary',
}
