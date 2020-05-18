"""
Tools for interacting with the credit statements in the database.
"""
from dateutil.relativedelta import relativedelta

from ..utils import (
    DatabaseHandler, fill_place, fill_places, filter_item, filter_items,
    check_sort_order
)
from .constants import STATEMENT_FIELDS
from .tools import select_fields
from .transactions import TransactionHandler


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

    def get_entries(self, card_ids=None, banks=None, active=False,
                    sort_order='DESC', fields=STATEMENT_FIELDS):
        """
        Get credit card statements from the database.

        Query the database to select credit card statement fields.
        Statements can be filtered by card, the issuing bank, or by card
        active status. All fields for all statements (regardless of
        active status) are shown by default.

        Parameters
        ––––––––––
        card_ids : tuple of int, optional
            A sequence of card IDs for which statements will be selected
            (if `None`, all cards will be selected).
        banks : tuple of str, optional
            A sequence of banks for which statements will be selected (if
            `None`, all banks will be selected).
        active : bool, optional
            A flag indicating whether only statements for active cards
            will be returned. The default is `False` (all statements are
            returned).
        sort_order : {'ASC', 'DESC'}
            An indicator of whether the statements should be ordered in
            ascending (oldest at top) or descending (newest at top)
            order.
        fields : tuple of str, optional
            A sequence of fields to select from the database (if `None`,
            all fields will be selected). A field can be any column from
            the 'credit_statements', 'credit_cards', or 'credit_accounts'
            tables.

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
                  "          ON c.id = s.card_id "
                  "       INNER JOIN credit_accounts AS a "
                  "          ON a.id = c.account_id "
                  " WHERE user_id = ? "
                 f"       {card_filter} {bank_filter} {active_filter} "
                 f" ORDER BY issue_date {sort_order}, active DESC")
        placeholders = (self.user_id, *fill_places(card_ids),
                       *fill_places(banks))
        statements = self._query_entries(query, placeholders)
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
                  "          ON c.id = s.card_id "
                  "       INNER JOIN credit_accounts AS a "
                  "          ON a.id = c.account_id "
                  " WHERE s.id = ? AND user_id = ?")
        abort_msg = (f'Statement ID {statement_id} does not exist for the '
                      'user.')
        statement = self._query_entry(statement_id, query, abort_msg)
        return statement

    def find_statement(self, card, issue_date=None, fields=None):
        """
        Find a statement using uniquely identifying characteristics.

        Queries the database to find a credit card statement based on
        the provided criteria. Credit card statements should be
        identifiable given the user's ID, the ID of the credit card to
        which the statement belongs, and the date on which the statement
        was issued.

        Parameters
        ––––––––––
        card : sqlite3.Row
            The entry of the credit card belonging to the statement.
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
        date_filter = filter_item(issue_date, 'issue_date', 'AND')
        query = (f"SELECT {select_fields(fields, 's.id')} "
                  "  FROM credit_statements_view AS s "
                  "       INNER JOIN credit_cards AS c "
                  "          ON c.id = s.card_id "
                  "       INNER JOIN credit_accounts AS a "
                  "          ON a.id = c.account_id "
                 f" WHERE user_id = ? AND card_id = ? {date_filter} "
                  " ORDER BY issue_date DESC")
        placeholders = (self.user_id, card['id'], *fill_place(issue_date))
        statement = self.cursor.execute(query, placeholders).fetchone()
        return statement

    def infer_statement(self, card, transaction_date, creation=False):
        """
        Infer the statement corresponding to the date of a transaction.

        Given the date of a transaction and the card used, infer the
        statement that the transaction belongs to. If the given card
        issues statements on a date later in the month than the
        transaction, the transaction will be assumed to be on that
        statement. Otherwise, the transaction is assumed to be on the
        following statement.

        Parameters
        ––––––––––
        card : sqlite3.Row
            The entry for the card used for the transaction.
        transaction_date : datetime.date
            The date the transaction took place.
        creation : bool, optional
            A flag indicating whether a statement should be created
            if it is not found in the database. The default is `False`;
            a statement will not be created, even if no matching
            statement already exists in the database.

        Returns
        –––––––
        statement : sqlite3.Row
            The inferred statement entry for the transaction.
        """
        issue_day = card['statement_issue_day']
        issue_date = determine_statement_issue_date(issue_day,
                                                    transaction_date)
        statement = self.find_statement(card, issue_date)
        if not statement and creation:
            statement = self.add_statement(card, issue_date)
        return statement

    def add_statement(self, card, issue_date, due_date=None):
        """Add a statement to the database."""
        if not due_date:
            due_day = card['statement_due_day']
            due_date = determine_statement_due_date(due_day, issue_date)
        statement_data = {'card_id': card['id'],
                          'issue_date': issue_date,
                          'due_date': due_date}
        statement = self.add_entry(statement_data)
        return statement

    def delete_entries(self, entry_ids):
        """
        Delete statements from the database.

        Given a set of statement IDs, delete the statements from the
        database. Deleting a statement will also delete all transactions
        on that statement.

        Parameters
        ––––––––––
        entry_ids : list of int
            The IDs of statements to be deleted.
        """
        # Delete all transactions corresponding to these statements
        transaction_db = TransactionHandler()
        transactions = transaction_db.get_entries(statement_ids=entry_ids,
                                                  fields=())
        transaction_ids = [transaction['id'] for transaction in transactions]
        transaction_db.delete_entries(transaction_ids)
        # Delete the given statements
        super().delete_entries(entry_ids)


def determine_statement_issue_date(issue_day, transaction_date):
    """
    Determine the date for the statement belonging to a transaction.

    Given the day of them month on which statements are issued and the
    date a transaction occurred, determine the date the transaction's
    statement was issued.

    Parameters
    ––––––––––
    issue_day : int
        The day of the month on which statements are issued.
    transaction_date : datetime.date
        The date the transaction took place.

    Returns
    –––––––
    statement_date : datetime.date
        The date on which the statement corresponding to the transaction
        date was issued.
    """
    curr_month_statement_date = transaction_date.replace(day=issue_day)
    if transaction_date.day < issue_day:
        # The transaction will be on the statement later in the month
        statement_date = curr_month_statement_date
    else:
        # The transaction will be on the next month's statement
        statement_date = curr_month_statement_date + relativedelta(months=+1)
    return statement_date


def determine_statement_due_date(due_day, issue_date):
    """
    Determine the due date for a statement.

    Given the day of the month on which statements are due and the date
    a statement was issued, determine the statement's due date.

    Parameters
    ––––––––––
    due_day : int
        The day of the month on which statements are due.
    issue_date : datetime.date
        The date the statement was issued.

    Returns
    –––––––
    due_date : datetime.date
        The date on which the statement is determined to be due.
    """
    curr_month_due_date = issue_date.replace(day=due_day)
    if issue_date.day < due_day:
        # The statement is due on the due date later this month
        due_date = curr_month_due_date
    else:
        # The statement is due on the due date next month
        due_date = curr_month_due_date + relativedelta(months=+1)
    return due_date
