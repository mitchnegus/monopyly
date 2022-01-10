"""
Tools for interacting with credit accounts in the database.
"""
from ..utils import DatabaseHandler, fill_places, filter_items, select_fields
from .cards import CreditCardHandler


class CreditAccountHandler(DatabaseHandler):
    """
    A database handler for managing credit accounts.

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
    _table = 'credit_accounts'

    def get_entries(self, bank_names=None, fields=None):
        """
        Get credit accounts from the database.

        Query the database to select credit account fields. Accounts can
        be filtered by the issuing bank. All fields for all accounts are
        shown by default.

        Parameters
        ––––––––––
        bank_names : tuple of str, optional
            A sequence of bank names for which accounts will be selected (if
            `None`, all banks will be selected).
        fields : tuple of str, optional
            A sequence of fields to select from the database (if `None`,
            all fields will be selected). Can be any field in the
            'credit_accounts' or 'banks' tables.

        Returns
        –––––––
        accounts : list of sqlite3.Row
            A list of credit accounts matching the criteria.
        """
        bank_filter = filter_items(bank_names, 'bank_name', 'AND')
        query = (f"SELECT {select_fields(fields, 'a.id')} "
                  "  FROM credit_accounts AS a "
                  "       INNER JOIN banks AS b "
                  "          ON b.id = a.bank_id "
                  " WHERE user_id = ? "
                 f"       {bank_filter} ")
        placeholders = (self.user_id, *fill_places(bank_names))
        accounts = self._query_entries(query, placeholders)
        return accounts

    def get_entry(self, account_id, fields=None):
        """Get a credit account from the database given its ID."""
        query = (f"SELECT {select_fields(fields, 'a.id')} "
                  "  FROM credit_accounts AS a "
                  "       INNER JOIN banks AS b "
                  "          ON b.id = a.bank_id "
                  " WHERE a.id = ? AND user_id = ?")
        placeholders = (account_id, self.user_id)
        abort_msg = f'Account ID {account_id} does not exist for the user.'
        account = self._query_entry(query, placeholders, abort_msg)
        return account

    def delete_entries(self, entry_ids):
        """
        Delete credit card accounts from the database.

        Given a set of account IDs, delete the credit card accounts from
        the database. Deleting an account will also delete all credit
        cards (and statements, transactions) for that account.

        Parameters
        ––––––––––
        entry_ids : list of int
            The IDs of accounts to be deleted.
        """
        # Delete all cards corresponding to these accounts
        card_db = CreditCardHandler()
        cards = card_db.get_entries(fields=(), account_ids=entry_ids)
        card_ids = [card['id'] for card in cards]
        card_db.delete_entries(card_ids)
        # Delete the given accounts
        super().delete_entries(entry_ids)
