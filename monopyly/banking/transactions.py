"""
Tools for interacting with the bank transactions in the database.
"""
from ..common.forms.utils import execute_on_form_validation
from ..common.transactions import TransactionHandler
from ..core.internal_transactions import add_internal_transaction
from ..database.handler import DatabaseViewHandler
from ..database.models import (
    BankAccountView,
    BankSubtransaction,
    BankTransaction,
    BankTransactionView,
)


class BankTransactionHandler(
    TransactionHandler, model=BankTransaction, model_view=BankTransactionView
):
    """
    A database handler for accessing bank transactions.

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
    @DatabaseViewHandler.view_query
    def get_transactions(cls, account_ids=None, active=None, sort_order="DESC"):
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
        criteria = cls._initialize_criteria_list()
        criteria.add_match_filter(cls.model, "account_id", account_ids)
        criteria.add_match_filter(BankAccountView, "active", active)
        transactions = super().get_entries(criteria, sort_order=sort_order)
        return transactions

    @staticmethod
    def _prepare_subtransaction(transaction, subtransaction_data):
        """Prepare a subtransaction for the given transaction."""
        return BankSubtransaction(transaction_id=transaction.id, **subtransaction_data)


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
