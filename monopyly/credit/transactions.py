"""
Tools for interacting with the credit transactions database.
"""
from flask import g

from ..db import get_db
from ..utils import (
    DatabaseHandler, parse_date, reserve_places, fill_places, check_sort_order
)
from .constants import TRANSACTION_FIELDS
from .tools import select_fields, filter_items
from .cards import CardHandler
from .statements import StatementHandler, determine_statement


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

    def get_transactions(self, fields=TRANSACTION_FIELDS.keys(), card_ids=None,
                         statement_ids=None, sort_order='DESC', active=False):
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
        fields : tuple of str, optional
            A sequence of fields to select from the database (if `None`,
            all fields will be selected). A field can be any column from
            the 'credit_transactions', credit_statements', or
            'credit_cards' tables.
        card_ids : tuple of str, optional
            A sequence of card IDs with which to filter transactions (if
            `None`, all card IDs will be shown).
        statement_ids : tuple of str, optional
            A sequence of statement IDs with which to filter
            transactions (if `None`, all statement IDs will be shown).
        sort_order : {'ASC', 'DESC'}
            An indicator of whether the transactions should be ordered
            in ascending (oldest at top) or descending (newest at top)
            order.
        active : bool, optional
            A flag indicating whether only transactions for active cards
            will be returned. The default is `False` (all transactions
            are returned).

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
                  "  JOIN credit_statements AS s ON s.id = t.statement_id "
                  "  JOIN credit_cards AS c ON c.id = s.card_id "
                  " WHERE user_id = ? "
                 f"       {card_filter} {statement_filter} {active_filter}"
                 f" ORDER BY transaction_date {sort_order}")
        placeholders = (self.user_id, *fill_places(card_ids),
                        *fill_places(statement_ids))
        transactions = self.cursor.execute(query, placeholders).fetchall()
        return transactions

    def get_transaction(self, transaction_id, fields=None):
        """Get a transaction from the database given its transaction ID."""
        query = (f"SELECT {select_fields(fields, 't.id')} "
                  "  FROM credit_transactions AS t "
                  "  JOIN credit_statements AS s ON s.id = t.statement_id "
                  "  JOIN credit_cards AS c ON c.id = s.card_id "
                  " WHERE t.id = ? AND c.user_id = ?")
        placeholders = (transaction_id, self.user_id)
        transaction = self.cursor.execute(query, placeholders).fetchone()
        # Check that a transaction was found
        if transaction is None:
            abort(404, f'Transaction ID {transaction_id} does not exist.')
        return transaction

    def new_transaction(self, form):
        """
        Create a new transaction in the database from a submitted form.

        Accept a new transaction from a user provided form, and insert
        the information into the database. All fields are processed and
        sanitized using the database handler.

        Parameters
        ––––––––––
        form : werkzeug.datastructures.ImmutableMultiDict
            A MultiDict containing the submitted form information.

        Returns
        –––––––
        transaction : sqlite3.Row
            The newly added transaction.
        """
        mapping = process_transaction(form)
        if TRANSACTION_FIELDS.keys() != mapping.keys():
            raise ValueError('The mapping does not match the database. Fields '
                            f'({", ".join(TRANSACTION_FIELDS.keys())}) must '
                             'be provided.')
        self.cursor.execute(
            f"INSERT INTO credit_transactions {tuple(mapping.keys())} "
            f"VALUES ({reserve_places(mapping.values())})",
            (*mapping.values(),)
        )
        self.db.commit()
        transaction = self.get_transaction(self.cursor.lastrowid)
        return transaction

    def update_transaction(self, transaction_id, form):
        """
        Update a transaction in the database from a submitted form.

        Accept a modified transaction from a user provied form, and update
        the corresponding information in the database. All fields are
        processed and sanitized using the database handler.

        Parameters
        ––––––––––
        transaction_id : int
            The ID of the transaction to be updated.
        form : werkzeug.datastructures.ImmutableMultiDict
            A MultiDict containing the submitted form information.

        Returns
        –––––––
        transaction : sqlite3.Row
            The newly updated transaction.
        """
        mapping = process_transaction(form)
        if TRANSACTION_FIELDS.keys() != mapping.keys():
            raise ValueError('The mapping does not match the database. Fields '
                            f'({", ".join(TRANSACTION_FIELDS.keys())}) must '
                             'be provided.')
        update_fields = ', '.join([f'{field} = ?' for field in mapping])
        self.cursor.execute(
            "UPDATE credit_transactions "
           f"   SET {update_fields} "
            " WHERE id = ?",
            (*mapping.values(), transaction_id)
        )
        self.db.commit()
        transaction = self.get_transaction(transaction_id)
        return transaction


    def delete_transaction(self, transaction_id):
        """Delete a transaction from the database given its transaction ID."""
        # Check that the transaction actually exists in the database
        self.get_transaction(transaction_id)
        self.cursor.execute(
            "DELETE FROM credit_transactions WHERE id = ?",
            (transaction_id,)
        )
        self.db.commit()


def process_transaction(form):
    """
    Collect submitted transaction information.

    Collect all transaction information submitted through the form. This
    aggregates all transaction data from the form, fills in defaults when
    necessary, and returns a dictionary of the transaction information.

    Parameters
    ––––––––––
    form : werkzeug.datastructures.ImmutableMultiDict
        A MultiDict containing the submitted form information.

    Returns
    –––––––
    card : sqlite3.Row
        A row in the database matching the card used in the transaction.
    transaction_info : dict
        A dictionary of transaction information collected (and/or extrapolated)
        from the user submission.
    """
    # Iterate through the transaction submission and create the dictionary
    transaction_info = {}
    for field in TRANSACTION_FIELDS:
        if field == 'statement_id':
            # Match the transaction to a registered credit card and statement
            ch, sh = CardHandler(), StatementHandler()
            card = ch.find_card(form['bank'], form['last_four_digits'])
            if not form['issue_date']:
                transaction_date = parse_date(form['transaction_date'])
                statement = determine_statement(card, transaction_date)
            else:
                statement_date = parse_date(form['issue_date'])
                statement = sh.find_statement(card['id'], statement_date)
            transaction_info[field] = statement['id']
        elif field == 'transaction_date':
            # The field should be a date
            transaction_info[field] = parse_date(form[field])
        elif field == 'price':
            # Prices should be shown to 2 digits
            transaction_info[field] = f'{float(form[field]):.2f}'
        else:
            transaction_info[field] = form[field]
    return transaction_info
