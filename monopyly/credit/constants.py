"""
Module for constants that will be used throughout the `credit` module.
"""
import operator as op

from ..utils import filter_dict

# Define database fields for credit card transactions
TRANSACTION_FIELDS = {'id': None,
                      'user_id': None,
                      'card_id': None,
                      'transaction_date': 'Date',
                      'vendor': 'Vendor',
                      'price': 'Price',
                      'notes': 'Notes',
                      'statement_date': 'Statement Date'}
# Define database fields for credit cards
CARD_FIELDS = {'id': None,
               'user_id': None,
               'bank': 'Bank',
               'last_four_digits': 'Last Four Digits',
               'statement_day': None,
               'active': None}
# Create a dictionary with both credit card and transaction fields
ALL_FIELDS = {**CARD_FIELDS, **TRANSACTION_FIELDS}
# Create a dictionary with all fields that are displayed to a user
DISPLAY_FIELDS = filter_dict(ALL_FIELDS, op.is_not, None, by_value=True)
# Create a dictionary with all fields that a user is required to provide
REQUIRED_CATEGORIES = ('transaction_date', 'vendor', 'price',
                       'notes', 'last_four_digits')
REQUIRED_FIELDS = filter_dict(DISPLAY_FIELDS, op.contains, REQUIRED_CATEGORIES)
