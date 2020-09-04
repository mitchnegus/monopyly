"""
Module for constants that will be used throughout the `credit` module.
"""


# Define database fields for each credit card table (skipping 'id' fields)
ACCOUNT_FIELDS = (
    'user_id',
    'bank',
    'statement_issue_day',
    'statement_due_day'
)
CARD_FIELDS = (
    'account_id',
    'last_four_digits',
    'active'
)
STATEMENT_FIELDS = (
    'card_id',
    'issue_date',
    'due_date'
)
STATEMENT_VIEW_FIELDS = (
    'balance',
    'payment_date'
)
TRANSACTION_FIELDS = (
    'statement_id',
    'transaction_date',
    'vendor'
)
TRANSACTION_VIEW_FIELDS = (
    'total',
    'notes'
)
SUBTRANSACTION_FIELDS = (
    'transaction_id',
    'subtotal',
    'note'
)
TAG_FIELDS = (
    'parent_id',
    'user_id',
    'tag_name'
)
ALL_FIELDS = (
    *ACCOUNT_FIELDS,
    *CARD_FIELDS,
    *STATEMENT_FIELDS,
    *STATEMENT_VIEW_FIELDS,
    *TRANSACTION_FIELDS,
    *TRANSACTION_VIEW_FIELDS,
    *SUBTRANSACTION_FIELDS,
    *TAG_FIELDS
)
