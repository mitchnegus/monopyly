"""
Tools for interacting with the credit transactions in the database.
"""
from ..utils import (
    DatabaseHandler, fill_places, filter_items, check_sort_order
)
from .constants import TRANSACTION_FIELDS, TAG_FIELDS
from .tools import select_fields


class TransactionHandler(DatabaseHandler):
    """
    A database handler for accessing credit transactions.

    Parameters
    ––––––––––
    db : sqlite3.Connection
        A connection to the database for interfacing.
    user_id : int
        The ID of the user who is the subject of database access. If not
        given, the handler defaults to using the logged-in user.
    check_user : bool
        A flag indicating whether the handler should check that the
        provided user ID matches the logged-in user.

    Attributes
    ––––––––––
    table_name : str
        The name of the database table that this handler manages.
    db : sqlite3.Connection
        A connection to the database for interfacing.
    cursor : sqlite.Cursor
        A cursor for executing database interactions.
    user_id : int
        The ID of the user who is the subject of database access.
    """
    table_name = 'credit_transactions'
    table_fields = TRANSACTION_FIELDS

    def __init__(self, db=None, user_id=None, check_user=True):
        super().__init__(db=db, user_id=user_id, check_user=check_user)

    def get_entries(self, card_ids=None, statement_ids=None, active=False,
                    sort_order='DESC', fields=TRANSACTION_FIELDS):
        """
        Get credit card transactions from the database.

        Query the database to select credit card transaction information.
        Transaction information includes details specific to the
        transaction, the transaction's statement, and the credit card
        used to make the transaction. Transactions can be filtered by
        statement or the credit card used. Query results can be ordered
        by either ascending or descending transaction date.

        Parameters
        ––––––––––
        card_ids : tuple of int, optional
            A sequence of card IDs with which to filter transactions (if
            `None`, all card IDs will be shown).
        statement_ids : tuple of str, optional
            A sequence of statement IDs with which to filter
            transactions (if `None`, all statement IDs will be shown).
        active : bool, optional
            A flag indicating whether only transactions for active cards
            will be returned. The default is `False` (all transactions
            are returned).
        sort_order : {'ASC', 'DESC'}
            An indicator of whether the transactions should be ordered
            in ascending (oldest at top) or descending (newest at top)
            order.
        fields : tuple of str, optional
            A sequence of fields to select from the database (if `None`,
            all fields will be selected). A field can be any column from
            the 'credit_transactions', credit_statements',
            'credit_cards', or 'credit_accounts' tables.

        Returns
        –––––––
        transactions : list of sqlite3.Row
            A list of credit card transactions matching the criteria.
        """
        check_sort_order(sort_order)
        card_filter = filter_items(card_ids, 'card_id', 'AND')
        statement_filter = filter_items(statement_ids, 'statement_id', 'AND')
        active_filter = "AND active = 1" if active else ""
        query = (f"SELECT {select_fields(fields, 't.id')} "
                  "  FROM credit_transactions AS t "
                  "       INNER JOIN credit_statements AS s "
                  "          ON s.id = t.statement_id "
                  "       INNER JOIN credit_cards AS c "
                  "          ON c.id = s.card_id "
                  "       INNER JOIN credit_accounts AS a "
                  "          ON a.id = c.account_id "
                  " WHERE user_id = ? "
                 f"       {card_filter} {statement_filter} {active_filter} "
                 f" ORDER BY transaction_date {sort_order}")
        placeholders = (self.user_id, *fill_places(card_ids),
                        *fill_places(statement_ids))
        transactions = self._query_entries(query, placeholders)
        return transactions

    def get_entry(self, transaction_id, fields=None):
        """
        Get a transaction from the database given its transaction ID.

        Accesses a set of fields for a given transaction. By default,
        all fields for a transaction, the corresponding statement,
        issuing credit card and account are returned.

        Parameters
        ––––––––––
        transaction_id : int
            The ID of the transaction to be found.
        fields : tuple of str, optional
            The fields (in either the transactions, statements, cards,
            or accounts tables) to be returned.

        Returns
        –––––––
        transaction : sqlite3.Row
            The transaction information from the database.
        """
        query = (f"SELECT {select_fields(fields, 't.id')} "
                  "  FROM credit_transactions AS t "
                  "       INNER JOIN credit_statements AS s "
                  "          ON s.id = t.statement_id "
                  "       INNER JOIN credit_cards AS c "
                  "          ON c.id = s.card_id "
                  "       INNER JOIN credit_accounts AS a "
                  "          ON a.id = c.account_id "
                  " WHERE t.id = ? AND user_id = ?")
        abort_msg = (f'Transaction ID {transaction_id} does not exist for the '
                      'user.')
        transaction = self._query_entry(transaction_id, query, abort_msg)
        return transaction


class TagHandler(DatabaseHandler):
    """
    A database handler for managing credit transaction tags.

    Parameters
    ––––––––––
    db : sqlite3.Connection
        A connection to the database for interfacing.
    user_id : int
        The ID of the user who is the subject of database access. If not
        given, the handler defaults to using the logged-in user.
    check_user : bool
        A flag indicating whether the handler should check that the
        provided user ID matches the logged-in user.

    Attributes
    ––––––––––
    table_name : str
        The name of the database table that this handler manages.
    db : sqlite3.Connection
        A connection to the database for interfacing.
    cursor : sqlite.Cursor
        A cursor for executing database interactions.
    user_id : int
        The ID of the user who is the subject of database access.
    """
    table_name = 'credit_tags'
    table_fields = TAG_FIELDS

    def __init__(self, db=None, user_id=None, check_user=True):
        super().__init__(db=db, user_id=user_id, check_user=check_user)

    def get_entries(self, transaction_ids=None, fields=TAG_FIELDS):
        """
        Get credit card transaction tags from the database.

        Query the database to select credit transaction tag fields. Tags
        can be filtered by transaction. All fields for a tag are shown
        by default.

        Parameters
        ––––––––––
        transaction_ids : tuple of int, optional
            A sequence of transaction IDs for which tags will be selected
            (if `None`, all tags will be selected).
        fields : tuple of str, optional
            A sequence of fields to select from the database (if `None`,
            all fields will be selected). A field can be any column from
            the 'credit_tags' table.

        Returns
        –––––––
        tags : list of sqlite3.Row
            A list of credit card transaction tags matching the criteria.
        """
        transaction_filter = filter_items(transaction_ids,
                                          'transaction_id',
                                          'AND')
        query = (f"SELECT {select_fields(fields, 'DISTINCT t.id')} "
                  "  FROM credit_tags AS t "
                  "       INNER JOIN credit_tag_links AS l "
                  "          ON l.tag_id = t.id "
                  " WHERE user_id = ? "
                 f"       {transaction_filter}")
        print(query)
        placeholders = (self.user_id, *fill_places(transaction_ids))
        statements = self._query_entries(query, placeholders)
        return statements

    def get_entry(self, tag_id, fields=None):
        """
        Get a credit transaction tag from the database given its tag ID.

        Accesses a set of fields for a given tag. By default, all fields
        for a tag are returned.

        Parameters
        ––––––––––
        tag_id : int
            The ID of the tag to be found.
        fields : tuple of str, optional
            The fields (in the tags table) to be returned.

        Returns
        –––––––
        tag : sqlite3.Row
            The tag information from the database.
        """
        query = (f"SELECT {select_fields(fields, 't.id')} "
                  "  FROM credit_tags AS t "
                  " WHERE t.id = ? AND user_id = ?")
        abort_msg = (f'Tag ID {tag_id} does not exist for the user.')
        tag = self._query_entry(tag_id, query, abort_msg)
        return tag

