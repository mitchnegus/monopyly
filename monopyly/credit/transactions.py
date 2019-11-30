"""
Tools for interacting with the credit transactions database.
"""
from flask import g

from ..db import get_db
from ..utils import (
    DatabaseHandler, reserve_places, fill_places, check_sort_order
)
from .filters import *

class TransactionHandler(DatabaseHandler):
    """
    A database handler for accessing the credit transactions database.

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
    db : sqlite3.Connection
        A connection to the database for interfacing.
    cursor : sqlite.Cursor
        A cursor for executing database interactions.
    user_id : int
        The ID of the user who is the subject of database access.
    """

    def __init__(self, db=None, user_id=None, check_user=True):
        super().__init__(db=db, user_id=user_id, check_user=check_user)

    def get_transactions(self, fields=None, card_ids=None, statement_ids=None,
                         sort_order='DESC'):
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
        fields : tuple of str, None
            A sequence of fields to select from the database (if `None`,
            all fields will be selected).
        card_ids : tuple of str
            A sequence of card IDs with which to filter transactions (if
            `None`, all card IDs will be shown).
        statement_ids : tuple of str
            A sequence of statement IDs with which to filter
            transactions (if `None`, all statement IDs will be shown).
        sort_order : str
            An indicator of whether the transactions should be ordered
            in ascending ('ASC'; oldest at top) or descending ('DESC';
            newest at top) order.

        Returns
        –––––––
        transactions : list of sqlite3.Row
            A list of credit card transactions matching the criteria.
        """
        check_sort_order(sort_order)
        card_filter = filter_cards(card_ids, 'AND')
        statement_filter = filter_statements(statement_ids, 'AND')
        query = (f"SELECT {select_fields(fields)} "
                  "  FROM credit_transactions AS t "
                  "  JOIN credit_statements AS s ON s.id = t.statement_id "
                  "  JOIN credit_cards AS c ON c.id = s.card_id "
                 f" WHERE user_id = ? {card_filter} {statement_filter} "
                 f" ORDER BY transaction_date {sort_order}")
        placeholders = (self.user_id, *fill_places(card_ids),
                        *fill_places(statement_ids))
        transactions = self.cursor.execute(query, placeholders).fetchall()
        return transactions

    def get_transaction(self, transaction_id):
        """Get a transaction from the database given its transaction ID."""
        query = ("SELECT * "
                 "  FROM credit_transactions AS t "
                 "  JOIN credit_statements AS s ON s.id = t.statement_id "
                 "  JOIN credit_cards AS c ON c.id = s.card_id "
                 "WHERE t.id = ? AND c.user_id = ?")
        placeholders = (transaction_id, self.user_id)
        transaction = self.cursor.execute(query, placeholders).fetchone()
        if transaction is None:
            abort(404, f'Transaction ID {transaction_id} does not exist.')
        return transaction
