"""
Tools for interacting with the credit cards database.
"""
from ..utils import DatabaseHandler, reserve_places, fill_places
from .filters import *

class CardHandler(DatabaseHandler):
    """
    A database handler for accessing the credit cards database.

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

    def get_cards(self, fields=None, banks=None, active=False):
        """
        Get credit cards from the database.

        Query the database to select credit card fields. Cards can be
        filtered by the issuing bank or by active status. All fields for
        all cards (regardless of active status) are shown by default.

        Parameters
        ––––––––––
        fields : tuple of str, None
            A sequence of fields to select from the database (if `None`,
            all fields will be selected).
        banks : tuple of str
            A sequence of banks for which cards will be selected (if
            `None`, all banks will be selected).
        active : bool
            A flag indicating whether only active cards will be
            returned. The default is `False` (all cards are returned).

        Returns
        –––––––
        cards : list of sqlite3.Row
            A list of credit cards matching the criteria.
        """
        bank_filter = filter_banks(banks, 'AND')
        active_filter = "AND active = 1" if active else ""
        query = (f"SELECT {select_fields(fields)} "
                  "  FROM credit_cards "
                 f" WHERE user_id = ? {bank_filter} {active_filter} "
                  " ORDER BY active DESC")
        placeholders = (self.user_id, *fill_places(banks))
        cards = self.cursor.execute(query, placeholders).fetchall()
        return cards

    def get_card(self, card_id):
        """Get a credit card from the database given its card ID."""
        query = ("SELECT * FROM credit_cards "
                 "WHERE id = ? AND user_id = ?")
        placeholders = (card_id, self.user_id)
        card = self.cursor.execute(query, placeholders).fetchone()
        return card
