"""
Tools for interacting with the credit statements database.
"""
from ..utils import DatabaseHandler, check_sort_order
from .tools import select_fields, filter_items

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

    def get_statements(self, fields=None, card_ids=None, banks=None,
                       sort_order='DESC', active=False):
        """
        Get credit card statements from the database.

        Query the database to select credit card statement fields.
        Statements can be filtered by card, the issuing bank, or by card
        active status. All fields for all statements (regardless of
        active status) are shown by default.

        Parameters
        ––––––––––
        fields : tuple of str, None
            A sequence of fields to select from the database (if `None`,
            all fields will be selected).
        card_ids : tuple of str, None
            A sequence of card IDs for which statements will be selected
            (if `None`, all cards will be selected).
        banks : tuple of str, None
            A sequence of banks for which statements will be selected (if
            `None`, all banks will be selected).
        sort_order : str
            An indicator of whether the statements should be ordered in
            ascending ('ASC'; oldest at top) or descending ('DESC';
            newest at top) order.
        active : bool
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
        query = (f"SELECT {select_fields(fields)} "
                  "  FROM credit_statements AS s "
                  "  JOIN credit_cards AS c ON c.id = s.card_id "
                  " WHERE user_id = ? "
                 f"       {card_filter} {bank_filter} {active_filter} "
                  " ORDER BY active DESC")
        placeholders = (self.user_id, *fill_places(card_ids),
                       *fill_places(banks))
        statements = self.cursor.execute(query, placeholders).fetchall()
        return statements

    def get_statement(self, statement_id):
        """Get a credit statement from the database given its statement ID."""
        query = ("SELECT * FROM credit_statements "
                 "WHERE id = ? AND user_id = ?")
        placeholders = (statement_id, self.user_id)
        statement = self.cursor.execute(query, placeholders).fetchone()
        # Check that a statement was found
        if statement is None:
            abort(404, f'Statement ID {statement_id} does not exist.')
        return statement
