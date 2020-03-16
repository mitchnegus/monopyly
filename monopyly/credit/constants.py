"""
Module for constants that will be used throughout the `credit` module.
"""


# Define database fields for credit accounts (without the 'id' field)
ACCOUNT_FIELDS = ('user_id',
                  'bank',
                  'statement_issue_day',
                  'statement_due_day')
# Define database fields for credit cards (without the 'id' field)
CARD_FIELDS = ('account_id',
               'last_four_digits',
               'active')
# Define database fields for credit card statements (without the 'id' field)
STATEMENT_FIELDS = ('card_id',
                    'issue_date',
                    'due_date',
                    'paid',
                    'payment_date',
                    'balance')
# Define database fields for credit card transactions (without the 'id' field)
TRANSACTION_FIELDS = ('statement_id',
                      'transaction_date',
                      'vendor',
                      'amount',
                      'notes')
# Create a dictionary with all database fields
ALL_FIELDS = (*ACCOUNT_FIELDS, *CARD_FIELDS,
              *STATEMENT_FIELDS, *TRANSACTION_FIELDS)
