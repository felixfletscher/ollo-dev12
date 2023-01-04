# -*- coding: utf-8 -*-
{
    'name': "Ollo Mollie Integration",
    'summary': """
        Ollo Mollie Integration""",
    'description': """
        Ollo Mollie Integration
    """,
    'category': 'Customizations',
    'support': 'felix@fletscher.de',
    'website': 'https://www.fletscher.de',
    'version': '16.0.0.0.1',
    'images': ['static/description/icon.png'],
    'depends': ['ollo_linked_products','molliesubscriptions'],
    'data': [
        'data/create_mollie_subscription_cron.xml',
        'data/create_mollie_payment_cron.xml',
        'data/mollie_interval_data.xml',
        'data/update_mollie_payment_state_cron.xml',
        'security/ir.model.access.csv',
        'views/sale_order_views.xml',
        'views/res_partner_views.xml',
        'views/molliesubscriptions_subscription_view.xml',
        'views/res_config_settings.xml',
        'views/stock_picking.xml',
        'views/mollie_interval_views.xml',
        'views/payment_transaction_views.xml',
        'views/account_move_views.xml',
        'views/account_payment_views.xml',
    ],
    'installable': True,
    'application': True,
    'images': [],
    'sequence': 1,
    'license': 'Other proprietary',
}
