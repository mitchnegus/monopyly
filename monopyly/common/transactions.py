"""
Tools for building a common transaction interface.
"""
from abc import abstractmethod

from flask import current_app

from ..database.handler import DatabaseViewHandler
from ..database.models import (
    BankAccountTypeView,
    BankTransactionView,
    CreditTransactionView,
)


class TransactionHandler(DatabaseViewHandler):
    """
    An abstract database handler for accessing transactions.

    Attributes
    ----------
    user_id : int
        The ID of the user who is the subject of database access.
    model : type
        The type of database model that the handler is primarily
        designed to manage.
    table : str
        The name of the database table that this handler manages.
    """

    @classmethod
    def _customize_entries_query(cls, query, filters, sort_order):
        query = super()._customize_entries_query(query, filters, sort_order)
        # Group transactions and order by transaction date
        query = query.group_by(cls.model.id)
        query = cls._sort_query(
            query,
            (cls.model.transaction_date, sort_order),
        )
        return query

    @classmethod
    def add_entry(cls, **field_values):
        """
        Add a transaction to the database.

        Uses values acquired from a `TransactionForm` to add a new
        transaction into the database. The values include information
        for the transaction, along with information for all
        subtransactions.

        Parameters
        ----------
        **field_values :
            Values for each field in the transaction (including
            subtransaction values).

        Returns
        -------
        transaction : database.models.BankTransaction
            The saved transaction.
        """
        # Extend the default method to account for subtransactions
        subtransactions_data = field_values.pop("subtransactions")
        transaction = super().add_entry(**field_values)
        cls._add_subtransactions(transaction, subtransactions_data)
        # Refresh the transaction with the subtransaction information
        cls._db.session.refresh(transaction)
        return transaction

    @classmethod
    def update_entry(cls, entry_id, **field_values):
        """Update a transaction in the database."""
        # Extend the default method to account for subtransactions
        subtransactions_data = field_values.pop("subtransactions", None)
        transaction = super().update_entry(entry_id, **field_values)
        if subtransactions_data:
            # Replace all subtransactions when updating any subtransaction
            for subtransaction in transaction.subtransactions:
                cls._db.session.delete(subtransaction)
            cls._add_subtransactions(transaction, subtransactions_data)
        # Refresh the transaction with the subtransaction information
        cls._db.session.refresh(transaction)
        return transaction

    @classmethod
    def _add_subtransactions(cls, transaction, subtransactions_data):
        """Add subtransactions to the database for the data given."""
        for subtransaction_data in subtransactions_data:
            subtransaction = cls._prepare_subtransaction(
                transaction, subtransaction_data
            )
            cls._db.session.add(subtransaction)
        # Flush to the database after all subtransactions have been added
        cls._db.session.flush()


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
        transaction.id, internal_transaction_id
    )
    if not linked_transaction:
        # Otherwise, check if there is a matching credit transaction
        linked_transaction = _get_linked_credit_transaction(
            transaction.id, internal_transaction_id
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
