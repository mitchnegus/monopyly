"""
Tools for building a common transaction interface.
"""
from flask import current_app

from ..database.models import (
    BankAccountTypeView, BankTransactionView, CreditTransactionView
)


def get_linked_transaction(transaction):
    """
    Find a transaction that is linked to the given transaction.

    Checks all transaction databases for a transaction that matches
    the given transaction.

    Parameters
    ----------
    transaction : Transaction
        The transaction for which to find a linked transaction.

    Returns
    -------
    linked_transaction : Transaction
        A transaction that is linked to the given transaction. If no
        linked transaction is found, `None` is returned.
    """
    internal_transaction_id = transaction.internal_transaction_id
    if not internal_transaction_id:
        return None
    # First, check if there is a matching bank transaction
    linked_transaction = _get_linked_bank_transaction(
        transaction.id,
        internal_transaction_id
    )
    if not linked_transaction:
        # Otherwise, check if there is a matching credit transaction
        linked_transaction = _get_linked_credit_transaction(
            transaction.id,
            internal_transaction_id
        )
    return linked_transaction


def _get_linked_bank_transaction(transaction_id, internal_transaction_id):
    """Get a bank transaction linked to the given transaction."""
    query = BankTransactionView.select_for_user().join(BankAccountTypeView)
    criteria = [
        BankTransactionView.id != transaction_id,
        BankTransactionView.internal_transaction_id == internal_transaction_id,
    ]
    query = query.where(*criteria)
    transaction = current_app.db.session.execute(query).scalar_one_or_none()
    return transaction


def _get_linked_credit_transaction(transaction_id, internal_transaction_id):
    """Get a credit transaction linked to the given transaction."""
    query = CreditTransactionView.select_for_user()
    criteria = [
        CreditTransactionView.id != transaction_id,
        CreditTransactionView.internal_transaction_id == internal_transaction_id,
    ]
    query = query.where(*criteria)
    transaction = current_app.db.session.execute(query).scalar_one_or_none()
    return transaction

