"""
Tools for interacting with the credit transactions in the database.
"""

from authanor.database.handler import DatabaseHandler, DatabaseViewHandler

from ...common.forms.utils import execute_on_form_validation
from ...common.transactions import TransactionHandler, TransactionTagHandler
from ...database.models import (
    Bank,
    CreditAccount,
    CreditCard,
    CreditStatementView,
    CreditSubtransaction,
    CreditTransaction,
    CreditTransactionView,
    credit_tag_link_table,
)


class CreditTransactionHandler(
    TransactionHandler, model=CreditTransaction, model_view=CreditTransactionView
):
    """
    A database handler for accessing credit transactions.

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
        cls, statement_ids=None, card_ids=None, active=None, sort_order="DESC"
    ):
        """
        Get credit card transactions from the database.

        Query the database to select credit card transaction information.
        Transaction information includes details specific to the
        transaction, the transaction's statement, and the credit card
        used to make the transaction. Transactions can be filtered by
        statement or the credit card used. Query results can be ordered
        by either ascending or descending transaction date.

        Parameters
        ----------
        statement_ids : tuple of int, optional
            A sequence of statement IDs with which to filter
            transactions (if `None`, all statement IDs will be shown).
        card_ids : tuple of int, optional
            A sequence of card IDs with which to filter transactions (if
            `None`, all card IDs will be shown).
        active : bool, optional
            A flag indicating whether only transactions for active cards
            will be returned. The default is `None` (all transactions
            are returned).
        sort_order : {'ASC', 'DESC'}
            An indicator of whether the transactions should be ordered
            in ascending (oldest at top) or descending (newest at top)
            order.

        Returns
        -------
        transactions : sqlalchemy.engine.ScalarResult
            Returns credit card transactions matching the criteria.
        """
        criteria = cls._initialize_criteria_list()
        criteria.add_match_filter(cls.model, "statement_id", statement_ids)
        criteria.add_match_filter(CreditCard, "id", card_ids)
        criteria.add_match_filter(CreditCard, "active", active)
        transactions = super()._get_transactions(
            criteria=criteria, sort_order=sort_order
        )
        return transactions

    @classmethod
    def add_entry(cls, **field_values):
        """
        Add a transaction to the database.

        Uses values acquired from a `CreditTransactionForm` to add a new
        transaction into the database. The values include information
        for the transaction, along with information for all
        subtransactions (including tags associated with each
        subtransaction).

        Parameters
        ----------
        **field_values :
            Values for each field in the transaction (including
            subtransaction values and tags).

        Returns
        -------
        transaction : database.models.CreditTransaction
            The saved transaction.
        """
        return super().add_entry(**field_values)

    @staticmethod
    def _prepare_subtransaction(transaction, subtransaction_data):
        """Prepare a subtransaction for the given transaction."""
        # NOTE I don't believe that this adds new tags to the database
        tag_names = subtransaction_data.pop("tags")
        return CreditSubtransaction(
            transaction_id=transaction.id,
            **subtransaction_data,
            tags=CreditTagHandler.get_tags(tag_names, ancestors=True),
        )


class CreditTagHandler(TransactionTagHandler, model=TransactionTagHandler.model):
    """
    A database handler for managing credit transaction tags.

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
        filtered by tag name or credit transaction.

        Parameters
        ----------
        tag_names : tuple of str, optional
            A sequence of names of tags to be selected (if `None`, all
            tag names will be selected).
        transaction_ids : tuple of int, optional
            A sequence of transaction IDs for which tags will be
            selected (if `None`, all transaction tags will be selected).
        subtransaction_ids : tuple of int, optional
            A sequence of credit subtransaction IDs for which tags will
            be selected (if `None`, all subtransaction tags will be
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
            Returns credit card transaction tags matching the criteria.
        """
        criteria = cls._initialize_criteria_list()
        criteria.add_match_filter(cls.model, "tag_name", tag_names)
        criteria.add_match_filter(CreditTransactionView, "id", transaction_ids)
        criteria.add_match_filter(CreditSubtransaction, "id", subtransaction_ids)
        tags = super()._get_tags(criteria, ancestors=ancestors)
        return tags

    @classmethod
    def _filter_entries(cls, query, criteria):
        # Add a join to enable filtering by transaction ID or subtransaction ID
        join_transaction = CreditTransactionView in criteria.discriminators
        join_subtransaction = (
            join_transaction or CreditSubtransaction in criteria.discriminators
        )
        if join_subtransaction:
            query = query.join(credit_tag_link_table).join(CreditSubtransaction)
            if join_transaction:
                query = query.join(CreditTransactionView)
        return super()._filter_entries(query, criteria)

    # TODO: Use SQLAlchemy
    def get_totals(self, tag_ids=None, statement_ids=None, start_date=None,
                   end_date=None, group_statements=False):
        """
        Get the totals for tags given the criteria.

        Find the sum of all transactions for tags matching provided
        criteria. Only tags where a transaction was registered that
        matches the criteria will be returned.

        Parameters
        ––––––––––
        tag_ids : tuple of int
            A set of tag IDs for which to get tag totals. If left as
            `None`, totals for any matching tags will be found.
        statement_ids : tuple of int
            A set of statement IDs for which to get tag totals. If left
            as `None`, tag totals will be found for all statements in
            the date range.
        start_date : datetime.date
            The first date to consider in the time interval over which
            to get tag totals. If left as `None`, the date range will
            extend back to the first transaction made.
        end_date : datetime.date
            The last date to consider in the time interval over which to
            get tag totals. If left as `None`, the date range will
            extend up to the last transaction made.
        group_statements : bool
            A flag indicating whether totals should be grouped by
            statement.

        Returns
        –––––––
        tag_totals : dict
            The list of totals for all tags matching the criteria.
        """
        tag_filter = self._queries.filter_items(tag_ids, 'tag_id', 'AND')
        statement_filter = self._queries.filter_items(statement_ids,
                                                      'statement_id', 'AND')
        date_filter = self._queries.filter_dates(start_date, end_date,
                                                 'transaction_date', 'AND')
        fields = ['SUM(subtotal) total', 'tag_name']
        groups = ['tags.id']
        if group_statements:
            fields.append('t.statement_id')
            groups.append('t.statement_id')
        query = (f"SELECT {', '.join(fields)} "
                  "  FROM credit_tags AS tags "
                  "       INNER JOIN credit_tag_links AS l "
                  "          ON l.tag_id = tags.id "
                  "       INNER JOIN credit_subtransactions AS s_t "
                  "          ON s_t.id = l.subtransaction_id "
                  "       INNER JOIN credit_transactions AS t "
                  "          ON t.id = s_t.transaction_id "
                  "       INNER JOIN credit_statements AS s "
                  "          ON s.id = t.statement_id "
                  " WHERE tags.user_id = ? "
                 f"       {tag_filter} {statement_filter} {date_filter} "
                 f" GROUP BY {', '.join(groups)}")
        placeholders = (self.user_id,
                        *self._queries.fill_places(statement_ids))
        tag_totals = self.query_entries(query, placeholders)
        return tag_totals

    def get_statement_average_totals(self, tag_ids=None, statement_ids=None):
        """
        Get the average tag totals per statement given the criteria.

        Find the average total (per statement) of all transactions for
        tags matching provided criteria. Only tags where a transaction
        was registered that matches the criteria will be returned.

        Parameters
        ––––––––––
        tag_ids : tuple of int
            A set of tag IDs for which to get tag average totals. If
            left as `None`, average totals for any matching tags will be
            found.
        statement_ids : tuple of int
            A set of statement IDs for which to get tag average totals.
            If left as `None`, tag average totals will be found for all
            statements in the date range.

        Returns
        –––––––
        tag_average_totals : list of sqlite3.Row
            The list of average totals for all tags matching the
            criteria.
        """
        statement_filter = self._queries.filter_items(statement_ids, 'id', 'AND')
        subquery = ("SELECT COUNT(s.id) "
                    "  FROM credit_statements AS s "
                    "       INNER JOIN credit_cards AS c "
                    "             ON c.id = s.card_id "
                    "       INNER JOIN credit_accounts AS a "
                    "             ON a.id = c.account_id "
                    "       INNER JOIN banks AS b "
                    "             ON b.id = a.bank_id "
                   f" WHERE b.user_id = ? {statement_filter}")
        tag_filter = self._queries.filter_items(tag_ids, 'tag_id', 'AND')
        statement_filter = self._queries.filter_items(statement_ids,
                                                      'statement_id', 'AND')
        query = (f"SELECT SUM(subtotal) / ({subquery}) average_total, tag_name "
                  "  FROM credit_tags AS tags "
                  "       INNER JOIN credit_tag_links AS l "
                  "          ON l.tag_id = tags.id "
                  "       INNER JOIN credit_subtransactions AS s_t "
                  "          ON s_t.id = l.subtransaction_id "
                  "       INNER JOIN credit_transactions AS t "
                  "          ON t.id = s_t.transaction_id "
                  "       INNER JOIN credit_statements AS s "
                  "          ON s.id = t.statement_id "
                 f" WHERE tags.user_id = ? {tag_filter} {statement_filter} "
                 f" GROUP BY tags.id")
        placeholders = (self.user_id,
                        *self._queries.fill_places(statement_ids),
                        self.user_id,
                        *self._queries.fill_places(statement_ids))
        tag_average_totals = self.query_entries(query, placeholders)
        return tag_average_totals


@execute_on_form_validation
def save_transaction(form, transaction_id=None):
    """
    Save a credit transaction.

    Saves a transaction in the database. If a transaction ID is given,
    then the transaction is updated with the form information. Otherwise
    the form information is added as a new entry.

    Parameters
    ----------
    form : CreditTransactionForm
        The form being used to provide the data being saved.
    transaction_id : int
        The ID of the transaction to be saved. If provided, the
        named transaction will be updated in the database. Otherwise, if
        the transaction ID is `None`, a new transaction will be added.

    Returns
    -------
    transaction : database.models.CreditTransactionView
        The saved transaction.
    """
    transaction_data = form.transaction_data
    if transaction_id:
        transaction = CreditTransactionHandler.get_entry(transaction_id)
        transaction_data.update(
            internal_transaction_id=transaction.internal_transaction_id
        )
        # Update the database with the updated transaction
        transaction = CreditTransactionHandler.update_entry(
            transaction_id,
            **transaction_data,
        )
    else:
        # Insert the new transaction into the database
        transaction = CreditTransactionHandler.add_entry(**transaction_data)
    return transaction
