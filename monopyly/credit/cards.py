"""
Tools for interacting with credit cards in the database.
"""
from werkzeug.exceptions import abort

from ..utils import (
    DatabaseHandler, fill_place, fill_places, filter_item, filter_items,
    reserve_places
)
from .constants import CARD_FIELDS
from .tools import select_fields
from .accounts import AccountHandler


class CardHandler(DatabaseHandler):
    """
    A database handler for managing credit cards.

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
    table_name = 'credit_cards'
    table_fields = CARD_FIELDS

    def __init__(self, db=None, user_id=None, check_user=True):
        super().__init__(db=db, user_id=user_id, check_user=check_user)

    def get_cards(self, fields=None, accounts=None, banks=None,
                  last_four_digits=None, active=False):
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
            'credit_cards' or 'credit_accounts' tables.
        accounts : tuple of str, optional
            A sequence of accounts for which cards will be selected (if
            `None`, all accounts will be selected).
        banks : tuple of str, optional
            A sequence of banks for which cards will be selected (if
            `None`, all banks will be selected).
        last_four_digits : tuple of str, optional
            A sequence of final 4 digits for which cards will be
            selected (if `None`, cards with any last 4 digits will be
            selected).
        active : bool, optional
            A flag indicating whether only active cards will be
            returned. The default is `False` (all cards are returned).

        Returns
        –––––––
        cards : list of sqlite3.Row
            A list of credit cards matching the criteria.
        """
        account_filter = filter_items(accounts, 'account_id', 'AND')
        bank_filter = filter_items(banks, 'bank', 'AND')
        digit_filter = filter_items(last_four_digits,
                                    'last_four_digits', 'AND')
        active_filter = "AND active = 1" if active else ""
        query = (f"SELECT {select_fields(fields, 'c.id')} "
                  "  FROM credit_cards AS c "
                  "       INNER JOIN credit_accounts AS a "
                  "       ON a.id = c.account_id "
                  " WHERE user_id = ? "
                 f"       {account_filter} {bank_filter} "
                 f"       {digit_filter} {active_filter} "
                  " ORDER BY active DESC")
        placeholders = (self.user_id,
                        *fill_places(accounts),
                        *fill_places(banks),
                        *fill_places(last_four_digits))
        cards = self.cursor.execute(query, placeholders).fetchall()
        return cards

    def get_entry(self, card_id, fields=None):
        """Get a credit card from the database given its card ID."""
        query = (f"SELECT {select_fields(fields, 'c.id')} "
                  "  FROM credit_cards AS c "
                  "       INNER JOIN credit_accounts AS a "
                  "       ON a.id = c.account_id "
                  " WHERE c.id = ? AND user_id = ?")
        placeholders = (card_id, self.user_id)
        card = self.cursor.execute(query, placeholders).fetchone()
        # Check that a card was found
        if card is None:
            abort_msg = f'Card ID {card_id} does not exist for the user.'
            abort(404, abort_msg)
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
        card : sqlite3.Row
            A credit card entry matching the given criteria. If no
            matching statement is found, returns `None`.
        """
        bank_filter = filter_item(bank, 'bank', 'AND')
        digit_filter = filter_item(last_four_digits, 'last_four_digits', 'AND')
        query = (f"SELECT {select_fields(self.table_fields, 'c.id')} "
                  "  FROM credit_cards AS c "
                  "       INNER JOIN credit_accounts AS a "
                  "       ON a.id = c.account_id "
                  " WHERE user_id = ? "
                 f"       {bank_filter} {digit_filter}")
        placeholders = (self.user_id, *fill_place(bank),
                        *fill_place(last_four_digits))
        card = self.cursor.execute(query, placeholders).fetchone()
        return card

    def process_card_form(self, form, card_id=None):
        """
        Process credit card information submitted on a form.

        Collect all credit card information submitted through the form.
        This aggregates all credit card data from the form, fills in
        defaults and makes inferrals when necessary, and then returns a
        dictionary mapping of the card information.

        Parameters
        ––––––––––
        form : CardForm
            An object containing the submitted form information.
        card_id : int, optional
            If given, the ID of the card to be updated. If left as
            `None`, a new credit card is created.

        Returns
        –––––––
        card : sqlite3.Row
            The saved credit card.
        """
        # Iterate through the card submission and create the dictionary
        mapping = {}
        for field in self.table_fields:
            if field == 'account_id':
                account_id = form[field].data
                if account_id == 0:
                    # Create a new account
                    ah = AccountHandler()
                    account_mapping = {'user_id': self.user_id,
                                       'bank': form['bank'].data,
                                       'statement_issue_day':
                                       form['statement_issue_day'].data,
                                       'statement_due_day':
                                       form['statement_due_day'].data}
                    ah.new_entry(account_mapping)
                    account_id = ah.cursor.lastrowid
                mapping[field] = account_id
            else:
                mapping[field] = form[field].data
        # Either create a new entry or update an existing entry
        if not card_id:
            card = self.new_entry(mapping)
        else:
            card = self.update_entry(card_id, mapping)
        return card
