"""
Tools for interacting with the credit cards database.
"""
from ..utils import DatabaseHandler, reserve_places, fill_place, fill_places
from .constants import CARD_FIELDS
from .tools import select_fields, filter_item, filter_items

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

    def get_cards(self, fields=CARD_FIELDS.keys(), banks=None, active=False):
        """
        Get credit cards from the database.

        Query the database to select credit card fields. Cards can be
        filtered by the issuing bank or by active status. All fields for
        all cards (regardless of active status) are shown by default.

        Parameters
        ––––––––––
        fields : tuple of str, optional
            A sequence of fields to select from the database (if `None`,
            all fields will be selected). Can be any field in the
            'credit_cards' table.
        banks : tuple of str, optional
            A sequence of banks for which cards will be selected (if
            `None`, all banks will be selected).
        active : bool, optional
            A flag indicating whether only active cards will be
            returned. The default is `False` (all cards are returned).

        Returns
        –––––––
        cards : list of sqlite3.Row
            A list of credit cards matching the criteria.
        """
        bank_filter = filter_items(banks, 'bank', 'AND')
        active_filter = "AND active = 1" if active else ""
        query = (f"SELECT {select_fields(fields, 'id')} "
                  "  FROM credit_cards "
                  " WHERE user_id = ? "
                 f"       {bank_filter} {active_filter} "
                  " ORDER BY active DESC")
        placeholders = (self.user_id, *fill_places(banks))
        cards = self.cursor.execute(query, placeholders).fetchall()
        return cards

    def get_card(self, card_id, fields=None):
        """Get a credit card from the database given its card ID."""
        query = (f"SELECT {select_fields(fields, 'id')} "
                  "  FROM credit_cards "
                  " WHERE id = ? AND user_id = ?")
        placeholders = (card_id, self.user_id)
        card = self.cursor.execute(query, placeholders).fetchone()
        # Check that a card was found
        if card is None:
            abort(404, f'Card ID {card_id} does not exist.')
        return card

    def find_card(self, bank=None, last_four_digits=None):
        """
        Find a credit card using uniquely identifying characteristics.

        Queries the database to find a credit card based on the provided
        criteria. Credit cards in the database can almost always be
        identified uniquely given the user's ID and the last four digits
        of the card number. In rare cases where a user has two cards
        with the same last four digits, the issuing bank can be used to
        help determine the card. (It is expected to be exceptionally
        rare that a user has two cards with the same last four digits
        from the same bank.) If multiple cards do match the criteria,
        only the first one found is returned.

        Parameters
        ––––––––––
        bank : str
            The bank of the card to find.
        last_four_digits : int
            The last four digits of the card to find.

        Returns
        –––––––
        card_id : int
            The ID of the card matching the given information.
        """
        bank_filter = filter_item(bank, 'bank', 'AND')
        digits_filter = filter_item(last_four_digits, 'last_four_digits','AND')
        query = (f"SELECT {select_fields(CARD_FIELDS.keys(), 'id')} "
                  "  FROM credit_cards "
                  " WHERE user_id = ? "
                 f"       {bank_filter} {digits_filter}")
        placeholders = (self.user_id, *fill_place(bank),
                        *fill_place(last_four_digits))
        card = self.cursor.execute(query, placeholders).fetchone()
        # Check that a card was found and that it belongs to the user
        if card is None:
            abort(404, 'A card matching the information was not found.')
        return card
