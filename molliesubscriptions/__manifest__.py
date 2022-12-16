{
    'name': "Mollie Subscriptions",
    'sequence': -1,
    'summary': "Module for Mollie Subscriptions",
    'description': "Module for Mollie Subscriptions",
    'author': "Ollo GmbH",
    'website': "https://www.ollo.de",
    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/16.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',
    # any module necessary for this one to work correctly
    'depends': ['base'],
    # always loaded
    'data': [
        'data/data.xml',
        'security/ir.model.access.csv',
        'views/molliesubscriptions_subscription_view.xml',
        'views/molliesubscriptions_payment_view.xml',
        'views/molliesubscriptions_payment_refund_view.xml',
        'views/molliesubscriptions_menus.xml',
        'views/res_config_settings.xml',

    ],
    'license': 'LGPL-3',
    'application': True,
}
