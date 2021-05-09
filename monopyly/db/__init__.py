"""
Expose commonly used database functionality to the rest of the package.
"""
from .db import get_db


# Define database fields ('id' field is ommitted in all cases where it exists)
DATABASE_FIELDS = {
    'users': (
        'username',
        'password',
    ),
    'banks': (
        'user_id',
        'bank_name',
    ),
    'bank_account_types': (
        'user_id',
        'type_name',
        'type_abbreviation',
    ),
    'bank_accounts': (
        'bank_id',
        'account_type_id',
        'last_four_digits',
        'active',
    ),
    'bank_transactions': (
        'account_id',
        'transaction_date',
        'total',
        'note',
    ),
    'credit_accounts': (
        'bank_id',
        'statement_issue_day',
        'statement_due_day',
    ),
    'credit_cards': (
        'account_id',
        'last_four_digits',
        'active',
    ),
    'credit_statements': (
        'card_id',
        'issue_date',
        'due_date',
    ),
    'credit_statments_view': (
        'card_id',
        'issue_date',
        'due_date',
        'balance',
        'payment_date',
    ),
    'credit_transactions': (
        'statement_id',
        'transaction_date',
        'vendor',
    ),
    'credit_transactions_view': (
        'statement_id',
        'transaction_date',
        'vendor',
        'total',
        'notes',
    ),
    'credit_subtransactions': (
        'transaction_id',
        'subtotal',
        'note',
    ),
    'credit_tags': (
        'parent_id',
        'user_id',
        'tag_name',
    ),
    'credit_tag_links': (
        'subtransaction_id',
        'tag_id',
    ),
}

