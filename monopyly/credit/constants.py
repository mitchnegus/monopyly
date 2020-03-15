"""
Module for constants that will be used throughout the `credit` module.
"""
import operator as op

from ..utils import filter_dict


# Define database fields for credit cards (without the 'id' field)
CARD_FIELDS = {'user_id': None,
               'bank': 'Bank',
               'last_four_digits': 'Last Four Digits',
               'statement_issue_day': None,
               'statement_due_day': None,
               'active': None}
# Define database fields for credit card statements (without the 'id' field)
STATEMENT_FIELDS = {'card_id': None,
                    'issue_date': 'Statement Date',
                    'due_date': None,
                    'paid': None,
                    'payment_date': None}
# Define database fields for credit card transactions (without the 'id' field)
TRANSACTION_FIELDS = {'statement_id': None,
                      'transaction_date': 'Date',
                      'vendor': 'Vendor',
                      'amount': 'Amount',
                      'notes': 'Notes'}
# Create a dictionary with all database fields
ALL_FIELDS = {**CARD_FIELDS, **STATEMENT_FIELDS, **TRANSACTION_FIELDS}
# Create a dictionary with all fields that are displayed to a user
DISPLAY_FIELDS = filter_dict(ALL_FIELDS, op.is_not, None, by_value=True)
