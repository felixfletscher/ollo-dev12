{
    'name': 'Ollo Subscription Sub Sale order',
    'version': '16.0.0.0.1',
    'author': 'Fletscher',
    'description': """
        This module enhances the sale orders of Ollo to include sub sale orders,
        and integrates with the Mollie payment gateway and the ABO delivery system.
    """,
    'summary': 'Create Sub Sale Order',
    'category': 'Customizations',
	'support': 'felix@fletscher.de',
    'website': 'https://www.fletscher.de',
    'depends': ['base', 'sale_subscription', 'account', 'ollo_mollie_integration'],
    'data': [
        'views/sale_order_views.xml'
    ],
    'installable': True,
    'application': False,
    'images': [],
    'license': 'Other proprietary',
}
