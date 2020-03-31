"""
Tools for interacting with the credit statements in the database.
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
    A database handler for managing credit card statements.

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
    table_fields = STATEMENT_FIELDS

    def __init__(self, db=None, user_id=None, check_user=True):
        super().__init__(db=db, user_id=user_id, check_user=check_user)

    def get_statements(self, fields=STATEMENT_FIELDS, card_ids=None,
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
            the 'credit_statements', 'credit_cards', or 'credit_accounts'
            tables.
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
                  "  FROM credit_statements_view AS s "
                  "       INNER JOIN credit_cards AS c "
                  "       ON c.id = s.card_id "
                  "       INNER JOIN credit_accounts AS a "
                  "       ON a.id = c.account_id "
                  " WHERE user_id = ? "
                 f"       {card_filter} {bank_filter} {active_filter} "
                 f" ORDER BY issue_date {sort_order}, active DESC")
        placeholders = (self.user_id, *fill_places(card_ids),
                       *fill_places(banks))
        statements = self.cursor.execute(query, placeholders).fetchall()
        return statements

    def get_entry(self, statement_id, fields=None):
        """
        Get a credit statement from the database given its statement ID.

        Accesses a set of fields for a given statement. By default, all
        fields for a statement and the corresponding credit card/account
        are returned.

        Parameters
        ––––––––––
        statement_id : int
            The ID of the statement to be found.
        fields : tuple of str, optional
            The fields (in either the statements, cards, or accounts
            tables) to be returned.

        Returns
        –––––––
        statement : sqlite3.Row
            The statement information from the database.
        """
        query = (f"SELECT {select_fields(fields, 's.id')} "
                  "  FROM credit_statements_view AS s "
                  "       INNER JOIN credit_cards AS c "
                  "       ON c.id = s.card_id "
                  "       INNER JOIN credit_accounts AS a "
                  "       ON a.id = c.account_id "
                  " WHERE s.id = ? AND user_id = ?")
        abort_msg = (f'Statement ID {statement_id} does not exist for the '
                      'user.')
        statement = self._query_entry(statement_id, query, abort_msg)
        return statement

    def find_statement(self, card_id, issue_date=None, fields=None):
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
        fields : tuple of str, optional
            The fields (in either the statements, cards, or accounts
            tables) to be returned.

        Returns
        –––––––
        statement : sqlite3.Row
            The statement entry matching the given criteria. If no
            matching statement is found, returns `None`.
        """
        card_filter = filter_item(card_id, 'card_id', 'AND')
        date_filter = filter_item(issue_date, 'issue_date', 'AND')
        query = (f"SELECT {select_fields(fields, 's.id')} "
                  "  FROM credit_statements_view AS s "
                  "       INNER JOIN credit_cards AS c "
                  "       ON c.id = s.card_id "
                  "       INNER JOIN credit_accounts AS a "
                  "       ON a.id = c.account_id "
                  " WHERE user_id = ? "
                 f"       {card_filter} {date_filter} "
                  " ORDER BY issue_date DESC")
        placeholders = (self.user_id, *fill_place(card_id),
                        *fill_place(issue_date))
        statement = self.cursor.execute(query, placeholders).fetchone()
        return statement


def determine_due_date(statement_due_day, issue_date):
    """
    Determine the due date for a statement.

    Given the day of the month on which statements are due and the date
    a statement was issued, determine the statement's due date.

    Parameters
    ––––––––––
    statement_due_day : int
        The day of the month on which statements are due.
    issue_date : datetime.date
        The date the statement was issued.

    Returns
    –––––––
    due_date : datetime.date
        The date on which the statement is determined to be due.
    """
    curr_month_due_date = issue_date.replace(day=statement_due_day)
    if issue_date.day < statement_due_day:
        # The statement is due on the due date later this month
        due_date = curr_month_due_date
    else:
        # The statement is due on the due date next month
        due_date = curr_month_due_date + relativedelta(months=+1)
    return due_date
