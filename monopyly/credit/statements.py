"""
Tools for interacting with the credit statements database.
"""
from dateutil.relativedelta import relativedelta

from werkzeug.exceptions import abort

from ..utils import (
    DatabaseHandler, fill_place, fill_places, filter_item, filter_items,
    check_sort_order
)
from .constants import STATEMENT_FIELDS
from .tools import select_fields

class StatementHandler(DatabaseHandler):
    """
    A database handler for accessing the credit statements database.

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
    table_name = 'credit_statements'

    def __init__(self, db=None, user_id=None, check_user=True):
        super().__init__(db=db, user_id=user_id, check_user=check_user)

    def get_statements(self, fields=STATEMENT_FIELDS.keys(), card_ids=None,
                       banks=None, sort_order='DESC', active=False):
        """
        Get credit card statements from the database.

        Query the database to select credit card statement fields.
        Statements can be filtered by card, the issuing bank, or by card
        active status. All fields for all statements (regardless of
        active status) are shown by default.

        Parameters
        ––––––––––
        fields : tuple of str, optional
            A sequence of fields to select from the database (if `None`,
            all fields will be selected). A field can be any column from
            the 'credit_statements' or 'credit_cards' tables, or a
            summation over the price column in the `credit_transactions`
            table.
        card_ids : tuple of str, optional
            A sequence of card IDs for which statements will be selected
            (if `None`, all cards will be selected).
        banks : tuple of str, optional
            A sequence of banks for which statements will be selected (if
            `None`, all banks will be selected).
        sort_order : {'ASC', 'DESC'}
            An indicator of whether the statements should be ordered in
            ascending (oldest at top) or descending (newest at top)
            order.
        active : bool, optional
            A flag indicating whether only statements for active cards
            will be returned. The default is `False` (all statements are
            returned).

        Returns
        –––––––
        statements : list of sqlite3.Row
            A list of credit card statements matching the criteria.
        """
        check_sort_order(sort_order)
        card_filter = filter_items(card_ids, 'card_id', 'AND')
        bank_filter = filter_items(banks, 'bank', 'AND')
        active_filter = "AND active = 1" if active else ""
        query = (f"SELECT {select_fields(fields, 's.id')} "
                  "  FROM credit_statements AS s "
                  "  JOIN credit_transactions AS t ON t.statement_id = s.id "
                  "  JOIN credit_cards AS c ON c.id = s.card_id "
                  " WHERE user_id = ? "
                 f"       {card_filter} {bank_filter} {active_filter} "
                  " GROUP BY s.id "
                 f" ORDER BY issue_date {sort_order}, active DESC")
        placeholders = (self.user_id, *fill_places(card_ids),
                       *fill_places(banks))
        statements = self.cursor.execute(query, placeholders).fetchall()
        return statements

    def get_statement(self, statement_id, fields=None):
        """Get a credit statement from the database given its statement ID."""
        query = (f"SELECT {select_fields(fields, 's.id')} "
                  "  FROM credit_statements AS s "
                  "  JOIN credit_cards AS c ON c.id = s.card_id "
                  " WHERE id = ? AND user_id = ?")
        placeholders = (statement_id, self.user_id)
        statement = self.cursor.execute(query, placeholders).fetchone()
        # Check that a statement was found
        if statement is None:
            abort_msg = (f'Statement ID {statement_id} does not exist for the '
                          'user.')
            abort(404, abort_msg)
        return statement

    def find_statement(self, card_id, issue_date=None):
        """
        Find a statement using uniquely identifying characteristics.

        Queries the database to find a credit card statement based on
        the provided criteria. Credit card statements should be
        identifiable given the user's ID, the ID of the credit card to
        which the statement belongs, and the date on which the statement
        was issued.

        Parameters
        ––––––––––
        card_id : int
            The ID of the credit card for the statement to be found.
        issue_date : datetime.date, optional
            A Python `date` object giving the issue date for the
            statement to be found (if `None`, the most recent statement
            will be found).

        Returns
        –––––––
        statement : int
            The statement entry matching the given information.
        """
        card_filter = filter_item(card_id, 'card_id', 'AND')
        date_filter = filter_item(issue_date, 'issue_date', 'AND')
        query = (f"SELECT {select_fields(STATEMENT_FIELDS.keys(), 's.id')} "
                  "  FROM credit_statements AS s "
                  "  JOIN credit_cards AS c on c.id = s.card_id "
                  " WHERE user_id = ? "
                 f"       {card_filter} {date_filter} "
                  " ORDER BY issue_date DESC")
        placeholders = (self.user_id, *fill_place(card_id),
                        *fill_place(issue_date))
        statement = self.cursor.execute(query, placeholders).fetchone()
        # Check that a statement was found and that it belongs to the user
        if statement is None:
            abort(404, 'A statement matching the information was not found.')
        return statement

    def new_statement(self, card, issue_date, payment_date=''):
        """
        Create a new credit card statement in the database.

        Accept a credit card and statement issue date and insert a new
        entry in the database for the corresponding credit card
        statement.

        Parameters
        ––––––––––
        card : sqlite3.Row
            A credit card entry from the database.
        issue_date : datetime.date
            The date the new statement was issued.
        payment_date : datetime.date, optional
            The date the new statement was paid.

        Returns
        –––––––
        statement : sqlite3.Row
            The newly added statement.
        """
        mapping = {'card_id': card['id'],
                   'issue_date': issue_date,
                   'due_date': determine_due_date(card, issue_date),
                   'paid': 1 if payment_date else 0,
                   'payment_date': payment_date}
        self.new_entry(mapping)
        statement = self.get_statement(self.cursor.lastrowid)
        return statement

    def delete_statement(self, statement_id):
        """Delete a statement from the database given its statement ID."""
        # Check that the statement exists and belongs to the user
        self.get_statement(statement_id)
        super().delete_entry()


def determine_due_date(card, issue_date):
    """Find the due date for a statement given the card and date issued."""
    due_day = card['statement_due_day']
    curr_month_due_date = issue_date.replace(day=due_day)
    if issue_date.day < due_day:
        # The statement is due on the due date later this month
        due_date = curr_month_due_date
    else:
        # The statement is due on the due date next month
        due_date = curr_month_due_date + relativedelta(months=+1)
    return due_date
