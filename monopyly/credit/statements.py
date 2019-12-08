"""
Tools for interacting with the credit statements database.
"""
from ..utils import DatabaseHandler, fill_place, fill_places, check_sort_order
from .constants import STATEMENT_FIELDS
from .tools import select_fields, filter_item, filter_items

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
    db : sqlite3.Connection
        A connection to the database for interfacing.
    cursor : sqlite.Cursor
        A cursor for executing database interactions.
    user_id : int
        The ID of the user who is the subject of database access.
    """

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
            the 'credit_statements' or 'credit_cards' tables.
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
        query = (f"SELECT {select_fields(fields, s.id)} "
                  "  FROM credit_statements AS s "
                  "  JOIN credit_cards AS c ON c.id = s.card_id "
                  " WHERE user_id = ? "
                 f"       {card_filter} {bank_filter} {active_filter} "
                  " ORDER BY active DESC")
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
            abort(404, f'Statement ID {statement_id} does not exist.')
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
        issue_date : str, optional
            The issue date for the statement to be found (if `None`, the
            most recent statement will be found).

        Returns
        –––––––
        statement_id : int
            The ID of the card matching the given information.
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
