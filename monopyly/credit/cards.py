"""
Tools for interacting with credit cards in the database.
"""
from ..utils import (
    DatabaseHandler, fill_place, fill_places, filter_item, filter_items,
    select_fields
)
from .statements import CreditStatementHandler


class CreditCardHandler(DatabaseHandler):
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
    table : str
        The name of the database table that this handler manages.
    db : sqlite3.Connection
        A connection to the database for interfacing.
    cursor : sqlite.Cursor
        A cursor for executing database interactions.
    user_id : int
        The ID of the user who is the subject of database access.
    """
    _table = 'credit_cards'

    def get_entries(self, account_ids=None, bank_names=None,
                    last_four_digits=None, active=False, fields=None):
        """
        Get credit cards from the database.

        Query the database to select credit card fields. Cards can be
        filtered by the issuing bank or by active status. All fields for
        all cards (regardless of active status) are shown by default.

        Parameters
        ––––––––––
        account_ids : tuple of int, optional
            A sequence of account IDs for which cards will be selected
            (if `None`, all accounts will be selected).
        bank_names : tuple of str, optional
            A sequence of bank names for which cards will be selected
            (if `None`, all banks will be selected).
        last_four_digits : tuple of str, optional
            A sequence of final 4 digits for which cards will be
            selected (if `None`, cards with any last 4 digits will be
            selected).
        active : bool, optional
            A flag indicating whether only active cards will be
            returned. The default is `False` (all cards are returned).
        fields : tuple of str, optional
            A sequence of fields to select from the database (if `None`,
            all fields will be selected). Can be any field in the
            'credit_cards', 'credit_accounts', or 'banks' tables.

        Returns
        –––––––
        cards : list of sqlite3.Row
            A list of credit cards matching the criteria.
        """
        account_filter = filter_items(account_ids, 'account_id', 'AND')
        bank_filter = filter_items(bank_names, 'bank_name', 'AND')
        digit_filter = filter_items(last_four_digits,
                                    'last_four_digits', 'AND')
        active_filter = "AND active = 1" if active else ""
        query = (f"SELECT {select_fields(fields, 'c.id')} "
                  "  FROM credit_cards AS c "
                  "       INNER JOIN credit_accounts AS a "
                  "          ON a.id = c.account_id "
                  "       INNER JOIN banks AS b "
                  "          ON b.id = a.bank_id "
                  " WHERE user_id = ? "
                 f"       {account_filter} {bank_filter} "
                 f"       {digit_filter} {active_filter} "
                  " ORDER BY active DESC")
        placeholders = (self.user_id,
                        *fill_places(account_ids),
                        *fill_places(bank_names),
                        *fill_places(last_four_digits))
        cards = self._query_entries(query, placeholders)
        return cards

    def get_entry(self, card_id, fields=None):
        """
        Get a credit card from the database given its ID.

        Accesses a set of fields for a given card. By default, all
        fields for a credit card and the corresponding account are
        returned.

        Parameters
        ––––––––––
        card_id : int
            The ID of the card to be found.
        fields : tuple of str, optional
            The fields (in either the cards, accounts, or banks tables)
            to be returned.

        Returns
        –––––––
        card : sqlite3.Row
            The card information from the database.
        """
        query = (f"SELECT {select_fields(fields, 'c.id')} "
                  "  FROM credit_cards AS c "
                  "       INNER JOIN credit_accounts AS a "
                  "          ON a.id = c.account_id "
                  "       INNER JOIN banks AS b "
                  "          ON b.id = a.bank_id "
                  " WHERE c.id = ? AND user_id = ?")
        placeholders = (card_id, self.user_id)
        abort_msg = f'Card ID {card_id} does not exist for the user.'
        card = self._query_entry(query, placeholders, abort_msg)
        return card

    def find_card(self, bank_name=None, last_four_digits=None, fields=None):
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
        bank_name : str, optional
            The bank of the card to find.
        last_four_digits : int, optional
            The last four digits of the card to find.
        fields : tuple of str, optional
            The fields (in either the credit accounts or credit cards
            tables) to be returned.

        Returns
        –––––––
        card : sqlite3.Row
            A credit card entry matching the given criteria. If no
            matching card is found, returns `None`.
        """
        bank_filter = filter_item(bank_name, 'bank_name', 'AND')
        digit_filter = filter_item(last_four_digits, 'last_four_digits', 'AND')
        query = (f"SELECT {select_fields(fields, 'c.id')} "
                  "  FROM credit_cards AS c "
                  "       INNER JOIN credit_accounts AS a "
                  "          ON a.id = c.account_id "
                  "       INNER JOIN banks AS b "
                  "          ON b.id = a.bank_id "
                  " WHERE user_id = ? "
                 f"       {bank_filter} {digit_filter}")
        placeholders = (self.user_id, *fill_place(bank_name),
                        *fill_place(last_four_digits))
        card = self.cursor.execute(query, placeholders).fetchone()
        return card

    def delete_entries(self, entry_ids):
        """
        Delete credit cards from the database.

        Given a set of card IDs, delete the credit cards from the
        database. Deleting a card will also delete all statements (and
        transactions) for that card.

        Parameters
        ––––––––––
        entry_ids : list of int
            The IDs of credit cards to be deleted.
        """
        # Delete all statements corresponding to these cards
        statement_db = CreditStatementHandler()
        statements = statement_db.get_entries(card_ids=entry_ids, fields=())
        statement_ids = [statement['id'] for statement in statements]
        statement_db.delete_entries(statement_ids)
        # Delete the given cards
        super().delete_entries(entry_ids)
