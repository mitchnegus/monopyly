"""
Module for constants that will be used throughout the `credit` module.
"""


# Define database fields for credit accounts (without the 'id' field)
ACCOUNT_FIELDS = (
    'user_id',
    'bank',
    'statement_issue_day',
    'statement_due_day'
)
# Define database fields for credit cards (without the 'id' field)
CARD_FIELDS = (
    'account_id',
    'last_four_digits',
    'active'
)
# Define database fields for credit card statements (without the 'id' field)
STATEMENT_FIELDS = (
    'card_id',
    'issue_date',
    'due_date'
)
STATEMENT_VIEW_FIELDS = (
    'balance',
    'payment_date'
)
# Define database fields for credit card transactions (without the 'id' field)
TRANSACTION_FIELDS = (
    'statement_id',
    'transaction_date',
    'vendor',
    'amount',
    'notes'
)
# Define database fields for credit transactions tags (without the 'id' field)
TAG_FIELDS = (
    'user_id',
    'tag_name'
)
# Create a tuple with all database fields
ALL_FIELDS = (
    *ACCOUNT_FIELDS,
    *CARD_FIELDS,
    *STATEMENT_FIELDS,
    *STATEMENT_VIEW_FIELDS,
    *TRANSACTION_FIELDS,
    *TAG_FIELDS
)
