"""
Tools for interacting with the credit transactions database.
"""
from dateutil.relativedelta import relativedelta

from werkzeug.exceptions import abort

from ..utils import (
    DatabaseHandler, fill_places, filter_items, check_sort_order,
    reserve_places, parse_date
)
from .constants import TRANSACTION_FIELDS
from .tools import select_fields
from .cards import CardHandler
from .statements import StatementHandler


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

    def __init__(self, db=None, user_id=None, check_user=True):
        super().__init__(db=db, user_id=user_id, check_user=check_user)

    def get_transactions(self, fields=TRANSACTION_FIELDS, card_ids=None,
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
                  "      INNER JOIN credit_statements AS s "
                  "      ON s.id = t.statement_id "
                  "      INNER JOIN credit_cards AS c "
                  "      ON c.id = s.card_id "
                  "      INNER JOIN credit_accounts AS a "
                  "      ON a.id = c.account_id "
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
                  "       INNER JOIN credit_statements AS s "
                  "       ON s.id = t.statement_id "
                  "       INNER JOIN credit_cards AS c "
                  "       ON c.id = s.card_id "
                  "       INNER JOIN credit_accounts AS a "
                  "       ON a.id = c.account_id "
                  " WHERE t.id = ? AND user_id = ?")
        placeholders = (transaction_id, self.user_id)
        transaction = self.cursor.execute(query, placeholders).fetchone()
        # Check that a transaction was found
        if transaction is None:
            abort_msg = (f'Transaction ID {transaction_id} does not exist for '
                          'the user.')
            abort(404, abort_msg)
        return transaction

    def save_transaction(self, form, transaction_id=None):
        """
        Save a transaction in the database from a submitted form.

        Accept a user provided form and either insert the information
        into the database as a new transaction or update the transaction
        with matching ID. All fields are processed and sanitized using
        the database handler.

        Parameters
        ––––––––––
        form : TransactionForm
            An object containing the submitted form information.
        transaction_id : int, optional
            If given, the ID of the transaction to be updated. If left
            as `None`, a new transaction is created.

        Returns
        –––––––
        transaction : sqlite3.Row
            The saved transaction.
        """
        mapping = self.process_transaction_form(form)
        if TRANSACTION_FIELDS != tuple(mapping.keys()):
            raise ValueError('The mapping does not match the database. Fields '
                            f'({", ".join(TRANSACTION_FIELDS)}) must '
                             'be provided.')
        # Either create a new entry or update an existing entry
        if not transaction_id:
            self.new_entry(mapping)
            transaction_id = self.cursor.lastrowid
        else:
            self.update_entry(transaction_id, mapping)
        transaction = self.get_transaction(transaction_id)
        return transaction

    def process_transaction_form(self, form):
        """
        Process transaction information submitted on a form.

        Collect all transaction information submitted through the form.
        This aggregates all transaction data from the form, fills in
        defaults and makes inferrals when necessary, and then returns a
        dictionary mapping of the transaction information.

        Parameters
        ––––––––––
        form : TransactionForm
            An object containing the submitted form information.

        Returns
        –––––––
        mapping : dict
            A dictionary of transaction information collected (and/or
            extrapolated) from the user submission.
        """
        # Iterate through the transaction submission and create the dictionary
        mapping = {}
        for field in TRANSACTION_FIELDS:
            if field == 'statement_id':
                # Match the transaction to a credit card and statement
                ch, sh = CardHandler(), StatementHandler()
                card = ch.find_card(form['bank'].data,
                                    form['last_four_digits'].data)
                # Check that a card was found and that it belongs to the user
                if not card:
                    abort(404, 'A card matching the criteria was not found.')
                if not form['issue_date'].data:
                    statement_issue_day = card['statement_issue_day']
                    transaction_date = form['transaction_date'].data
                    issue_date = determine_statement_date(statement_issue_day,
                                                          transaction_date)
                else:
                    issue_date = form['issue_date'].data
                statement = sh.find_statement(card['id'], issue_date)
                # If a matching statement does not exist, create a statement
                if not statement:
                    statement = sh.new_statement(card['id'], issue_date)
                mapping[field] = statement['id']
            else:
                mapping[field] = form[field].data
        return mapping

    def delete_transaction(self, transaction_id):
        """Delete a transaction from the database given its ID."""
        # Check that the transaction exists and belongs to the user
        self.get_transaction(transaction_id)
        super().delete_entry(transaction_id)


def determine_statement_date(statement_day, transaction_date):
    """
    Determine the date for the statement belonging to a transaction.

    Given the day of them month on which statements are issued and the
    date a transaction occurred, determine the date the transaction's
    statement was issued.

    Parameters
    ––––––––––
    statement_day : int
        The day of the month on which statements are issued.
    transaction_date : datetime.date
        The date the transaction took place.

    Returns
    –––––––
    statement_date : datetime.date
        The date on which the statement corresponding to the transaction
        date was issued.
    """
    curr_month_statement_date = transaction_date.replace(day=statement_day)
    if transaction_date.day < statement_day:
        # The transaction will be on the statement later in the month
        statement_date = curr_month_statement_date
    else:
        # The transaction will be on the next month's statement
        statement_date = curr_month_statement_date + relativedelta(months=+1)
    return statement_date
