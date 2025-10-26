"""
Tools for interacting with the bank transactions in the database.
"""

from dry_foundation.database.handler import DatabaseViewHandler

from ..common.forms.utils import execute_on_form_validation
from ..common.transactions import TransactionHandler, TransactionTagHandler
from ..core.internal_transactions import add_internal_transaction
from ..database.models import (
    BankAccountView,
    BankSubtransaction,
    BankTransaction,
    BankTransactionView,
    bank_tag_link_table,
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
    def get_transactions(
        cls, account_ids=None, active=None, sort_order="DESC", offset=None, limit=None
    ):
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
        offset : int, optional
            The number of transactions by which to offset the results
            returned by this query. The default is `None`, in which case
            no offset will be added.
        limit : int, optional
            A limit on the number of transactions retrieved from the
            database.

        Returns
        -------
        transactions : sqlalchemy.engine.ScalarResult
            Returns bank account transactions matching the criteria.
        """
        criteria = cls._initialize_criteria_list()
        criteria.add_match_filter(cls.model, "account_id", account_ids)
        criteria.add_match_filter(BankAccountView, "active", active)
        transactions = super()._get_transactions(
            criteria=criteria, sort_order=sort_order, offset=offset, limit=limit
        )
        return transactions

    @staticmethod
    def _prepare_subtransaction(transaction, subtransaction_data):
        """Prepare a subtransaction for the given transaction."""
        tag_names = subtransaction_data.pop("tags")
        return BankSubtransaction(
            transaction_id=transaction.id,
            **subtransaction_data,
            tags=BankTagHandler.get_tags(tag_names, ancestors=True),
        )


class BankTagHandler(TransactionTagHandler, model=TransactionTagHandler.model):
    """
    A database handler for managing bank transaction tags.

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
    def get_tags(
        cls,
        tag_names=None,
        transaction_ids=None,
        subtransaction_ids=None,
        ancestors=None,
    ):
        """
        Get transaction tags from the database.

        Query the database to select transaction tag fields. Tags can be
        can be filtered by tag name or bank transaction.

        Parameters
        ----------
        tag_names : tuple of str, optional
            A sequence of names of tags to be selected (if `None`, all
            tag names will be selected).
        transaction_ids : tuple of int, optional
            A sequence of bank transaction IDs for which tags will be
            selected (if `None`, all transaction tags will be selected).
        subtransaction_ids : tuple of int, optional
            A sequence of bank subtransaction IDs for which tags will be
            selected (if `None`, all subtransaction tags will be
            selected).
        ancestors : bool, optional
            A flag indicating whether the query should include tags
            that are the ancestor tags of other explictly selected tags
            returned from the database based on selection criteria. If
            `True`, all tags matching the criteria will be returned
            along with their ancestor tags. If `False`, any tag that is
            an ancestor of another tag in the list will be removed from
            the list. The default is `None`, in which case all tags
            matching the criteria will be returned, and no others.

        Returns
        -------
        tags : list of database.models.TransactionTag
            Returns transaction tags matching the criteria.
        """
        criteria = cls._initialize_criteria_list()
        criteria.add_match_filter(cls.model, "tag_name", tag_names)
        criteria.add_match_filter(BankTransactionView, "id", transaction_ids)
        criteria.add_match_filter(BankSubtransaction, "id", subtransaction_ids)
        tags = super()._get_tags(criteria, ancestors=ancestors)
        return tags

    @classmethod
    def _filter_entries(cls, query, criteria, offset, limit):
        # Add a join to enable filtering by transaction ID or subtransaction ID
        join_transaction = BankTransactionView in criteria.discriminators
        join_subtransaction = (
            join_transaction or BankSubtransaction in criteria.discriminators
        )
        if join_subtransaction:
            query = query.join(bank_tag_link_table).join(BankSubtransaction)
            if join_transaction:
                query = query.join(BankTransactionView)
        return super()._filter_entries(query, criteria, offset, limit)


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
                internal_transaction_id=transfer.internal_transaction_id,
                merchant=transfer.account_view.bank.bank_name,
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
