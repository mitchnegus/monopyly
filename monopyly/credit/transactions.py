"""
Tools for interacting with the credit transactions database.
"""
from flask import g

from ..db import get_db
from ..utils import (
    DatabaseHandler, reserve_places, fill_places, check_sort_order
)
from .constants import FORM_FIELDS
from .tools import select_fields, filter_items, check_if_date, parse_date
from .cards import CardHandler


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
                         sort_order='DESC', active=False):
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
        card_ids : tuple of str, None
            A sequence of card IDs with which to filter transactions (if
            `None`, all card IDs will be shown).
        statement_ids : tuple of str, None
            A sequence of statement IDs with which to filter
            transactions (if `None`, all statement IDs will be shown).
        sort_order : str
            An indicator of whether the transactions should be ordered
            in ascending ('ASC'; oldest at top) or descending ('DESC';
            newest at top) order.
        active : bool
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
        query = (f"SELECT {select_fields(fields)} "
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

    def get_transaction(self, transaction_id):
        """Get a transaction from the database given its transaction ID."""
        query = ("SELECT * "
                 "  FROM credit_transactions AS t "
                 "  JOIN credit_statements AS s ON s.id = t.statement_id "
                 "  JOIN credit_cards AS c ON c.id = s.card_id "
                 "WHERE t.id = ? AND c.user_id = ?")
        placeholders = (transaction_id, self.user_id)
        transaction = self.cursor.execute(query, placeholders).fetchone()
        # Check that a transaction was found
        if transaction is None:
            abort(404, f'Transaction ID {transaction_id} does not exist.')
        return transaction

    def new_transaction(self, mapping):
        """
        Create a new transaction in the database from the mapping.

        Returns
        –––––––
        transaction_id : int
            The ID of the newly created transaction in the database.
        """
        self.cursor.execute(
            f'INSERT INTO credit_transactions {tuple(mapping.keys())} '
            f'VALUES ({reserve_places(mapping.values())})',
            (*mapping.values(),)
        )
        self.db.commit()
        return cursor.lastrowid


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
    # Match the transaction to a registered credit card
    ch = CardHandler()
    card = ch.find_card(form['bank'], form['last_four_digits'])
    # Iterate through the transaction submission and create the dictionary
    transaction_info = {}
    for field in FORM_FIELDS:
        if form[field] and check_if_date(field):
            # The field should be a date
            transaction_info[field] = parse_date(form[field])
        elif form[field] and field == 'price':
            # Prices should be shown to 2 digits
            transaction_info[field] = f'{float(form[field]):.2f}'
        elif form[field] and field == 'last_four_digits':
            transaction_info[field] = int(form[field])
        else:
            transaction_info[field] = form[field]
    # Fill in the statement date field if it wasn't provided
    if not transaction_info['issue_date']:
        transaction_date = transaction_info['transaction_date']
        statement_date = get_expected_statement_date(transaction_date, card)
        transaction_info['issue_date'] = statement_date
    print(transaction_info)
    return card, transaction_info

def prepare_db_transaction_mapping(fields, values, card_id):
    """
    Prepare a field-value mapping for use with a database insertion/update.

    Given a set of database fields and a set of values, return a mapping of
    all the fields and values. For fields that do not have a corresponding
    value, do not include them in the mapping unless a value is otherwise
    explicitly defined.

    Parameters
    ––––––––––
    fields : iterable
        A set of fields corresponding to fields in the database.
    values : dict
        A mapping of fields and values (entered by a user for a transaction).
    card_id : int
        The ID of the card to be associated with the transaction.

    Returns
    –––––––
    mapping : dict
        A mapping between all fields to be entered into the database and the
        corresponding values.
    """
    mapping = {}
    for field in fields:
        if field != 'id':
            if field[-3:] != '_id':
                mapping[field] = values[field]
            elif field == 'user_id':
                mapping[field] = g.user['id']
            elif field == 'card_id':
                mapping[field] = card_id
    print(mapping)
    return mapping


