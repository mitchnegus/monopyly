"""
Tools for interacting with the bank transactions in the database.
"""
from ..core.internal_transactions import add_internal_transaction
from ..common.forms.utils import execute_on_form_validation
from ..database.handler import DatabaseHandler, DatabaseViewHandler
from ..database.models import (
    BankAccountView, BankTransaction, BankTransactionView, BankSubtransaction,
)


class BankTransactionHandler(DatabaseViewHandler):
    """
    A database handler for accessing bank transactions.

    Parameters
    ----------
    user_id : int
        The ID of the user who is the subject of database access. If not
        given, the handler defaults to using the logged-in user.

    Attributes
    ----------
    table : str
        The name of the database table that this handler manages.
    db : sqlite3.Connection
        A connection to the database for interfacing.
    user_id : int
        The ID of the user who is the subject of database access.
    """
    _model = BankTransaction
    _model_view = BankTransactionView

    @classmethod
    @DatabaseViewHandler.view_query
    def get_transactions(cls, account_ids=None, active=None,
                         sort_order="DESC"):
        """
        Get bank transactions from the database.

        Query the database to select bank transaction information.
        Transaction information includes details specific to the
        transaction and the corresponding bank account. Transactions can
        be filtered by bank, and query results can be ordered
        by either ascending or descending transaction date.

        Parameters
        ----------
        account_ids : tuple of int, optional
            A sequence of bank account IDs with which to filter
            transactions (if `None`, all bank account IDs will be
            shown).
        active : bool, optional
            A flag indicating whether to return transactions for active
            accounts, inactive accounts, or both. The default is `None`,
            where all transactions are returned regardless of the
            account's active status.
        sort_order : {'ASC', 'DESC'}
            An indicator of whether the transactions should be ordered
            in ascending (oldest at top) or descending (newest at top)
            order. The default is descending order.

        Returns
        -------
        transactions : sqlalchemy.engine.ScalarResult
            Returns bank account transactions matching the criteria.
        """
        criteria = [
            cls._filter_values(cls.model.account_id, account_ids),
            cls._filter_value(BankAccountView.active, active),
        ]
        transactions = super().get_entries(*criteria, sort_order=sort_order)
        return transactions

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

        Uses values acquired from a `BankTransactionForm` to add a new
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
        subtransactions_data = field_values.pop('subtransactions')
        transaction = super().add_entry(**field_values)
        cls._add_subtransactions(transaction, subtransactions_data)
        # Refresh the transaction with the subtransaction information
        cls._db.session.refresh(transaction)
        return transaction

    @classmethod
    def update_entry(cls, entry_id, **field_values):
        """Update a transaction in the database."""
        # Extend the default method to account for subtransactions
        subtransactions_data = field_values.pop('subtransactions', None)
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
            subtransaction = BankSubtransaction(
                transaction_id =transaction.id,
                **subtransaction_data,
            )
            cls._db.session.add(subtransaction)
        # Flush to the database after all subtransactions have been added
        cls._db.session.flush()


@execute_on_form_validation
def save_transaction(form, transaction_id=None):
    """
    Save a banking transaction.

    Saves a transaction in the database. If a transaction ID is given,
    then the transaction is updated with the form information. Otherwise
    the form information is added as a new entry.

    Parameters
    ----------
    form : BankTransactionForm
        The form being used to provide the data being saved.
    transaction_id : int
        The ID of the transaction to be saved. If provided, the
        named transaction will be updated in the database. Otherwise, if
        the transaction ID is `None`, a new transaction will be added.

    Returns
    -------
    transaction : database.models.BankTransactionView
        The saved transaction.
    """
    transaction_data = form.transaction_data
    transfer_data = form.transfer_data
    if transaction_id:
        transaction = BankTransactionHandler.get_entry(transaction_id)
        # Update the database with the updated transaction
        transaction_data.update(
            internal_transaction_id=transaction.internal_transaction_id
        )
        transaction = BankTransactionHandler.update_entry(
            transaction_id,
            **transaction_data,
        )
        # The transfer is not updated automatically; update it independently
    else:
        # Insert the new transaction into the database
        if transfer_data:
            transfer = record_new_transfer(transfer_data)
            transaction_data.update(
                internal_transaction_id=transfer.internal_transaction_id
            )
        transaction = BankTransactionHandler.add_entry(**transaction_data)
    return transaction


def record_new_transfer(transfer_data):
    """Record a new transfer given the data for populating the database."""
    # Create a new internal transaction ID to assign to the transfer
    transfer_data["internal_transaction_id"] = add_internal_transaction()
    # Add the transfer transaction to the database
    transfer = BankTransactionHandler.add_entry(**transfer_data)
    return transfer

