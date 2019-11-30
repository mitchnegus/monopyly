"""
...
"""
from flask import g

from ..db import get_db, reserve_places

class _DatabaseHandler:
    """
    A generic handler for database access.

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
        self.db = db if db else get_db()
        self.cursor = self.db.cursor()
        self.user_id = user_id if user_id else g.user['id']
        if check_user and self.user_id != g.user['id']:
            abort(403)


class CardHandler(_DatabaseHandler):
    """A database handler for accessing the credit cards database."""

    def __init__(self, db=None, user_id=None, check_user=True):
        super().__init__(db=db, user_id=user_id, check_user=check_user)

    def get_cards(self, banks=(), active=False):
        """
        Get credit cards from the database.

        Query the database to select credit cards. Cards can be
        filtered by the issuing bank, or by active status. All cards
        (regardless of active status) are shown by default.

        Parameters
        ––––––––––
        banks : tuple of str
            A sequence of banks for which cards will be selected.
        active : bool
            A flag indicating whether only active cards will be
            returned. The default is `False` (all cards are returned).
        """
        bank_filter = f"AND bank IN ({reserve_places(banks)})" if banks else ""
        active_filter = "AND active = 1" if active else ""
        query = ("SELECT * FROM credit_cards"
                f" WHERE user_id = ? {bank_filter} {active_filter}"
                 " ORDER BY active DESC")
        placeholders = (self.user_id, *banks)
        cards = self.cursor.execute(query, placeholders).fetchall()
        return cards

    def get_card(self, card_id):
        """Get a credit card from the database given its card ID."""
        query = "SELECT * FROM credit_cards WHERE id = ?"
        placeholders = (card_id,)
        card = self.cursor.execute(query, placeholders).fetchone()
        return card
