from odoo import _, api, fields, models
from datetime import datetime

class MollieSubscriptionsPayment(models.Model):
    _name = 'molliesubscriptions.payment'
    _description = 'Mollie Subscription Payments'
    _rec_name = 'payment_id'


    payment_id = fields.Char(string='Payment ID')
    created_at = fields.Datetime(string='Created at')
    amount_value = fields.Float(string='Amount Value')
    amount_currency = fields.Char(string='Amount Currency')
    method = fields.Char(string='Method')
    status = fields.Char(string='Status')
    paid_at = fields.Datetime(string='Paid at')
    amount_refunded_value = fields.Float(string='Amount Refunded Value')
    amount_refunded_currency = fields.Char(string='Amount Refunded Currency')
    amount_remaining_value = fields.Float(string='Amount Remaining Value')
    amount_remaining_currency =  fields.Char(string='Amount Remaining Currency')
    locale = fields.Char(string='Locale')
    profile_id = fields.Char(string='Profile ID')
    mandate_id = fields.Char(string='Mandate ID')
    sequence_type = fields.Char(string='Sequence Type')
    settlement_amount_value = fields.Float(string='Settlement Amount Value')
    settlement_amount_currency = fields.Char(string='Settlement Amount Currency')

    refund_ids = fields.One2many("molliesubscriptions.payment.refund", "payment_id", string="Refunds")    
    subscription_id = fields.Many2one("molliesubscriptions.subscription", string="Subscription")
