"""
Tools for interacting with credit accounts in the database.
"""
from ..utils import (
    DatabaseHandler, fill_place, fill_places, filter_item, filter_items
)
from .constants import ACCOUNT_FIELDS
from .tools import select_fields
from .cards import CardHandler


class AccountHandler(DatabaseHandler):
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
    table_name : str
        The name of the database table that this handler manages.
    db : sqlite3.Connection
        A connection to the database for interfacing.
    cursor : sqlite.Cursor
        A cursor for executing database interactions.
    user_id : int
        The ID of the user who is the subject of database access.
    """
    table_name = 'credit_accounts'
    table_fields = ACCOUNT_FIELDS

    def __init__(self, db=None, user_id=None, check_user=True):
        super().__init__(db=db, user_id=user_id, check_user=check_user)

    def get_entries(self, banks=None, fields=None):
        """
        Get credit accounts from the database.

        Query the database to select credit account fields. Accounts can
        be filtered by the issuing bank. All fields for all accounts are
        shown by default.

        Parameters
        ––––––––––
        banks : tuple of str, optional
            A sequence of banks for which cards will be selected (if
            `None`, all banks will be selected).
        fields : tuple of str, optional
            A sequence of fields to select from the database (if `None`,
            all fields will be selected). Can be any field in the
            'credit_accounts' table.

        Returns
        –––––––
        accounts : list of sqlite3.Row
            A list of credit accounts matching the criteria.
        """
        bank_filter = filter_items(banks, 'bank', 'AND')
        query = (f"SELECT {select_fields(fields, 'a.id')} "
                  "  FROM credit_accounts AS a "
                  " WHERE user_id = ? "
                 f"       {bank_filter} ")
        placeholders = (self.user_id, *fill_places(banks))
        accounts = self._query_entries(query, placeholders)
        return accounts

    def get_entry(self, account_id, fields=None):
        """Get a credit account from the database given its account ID."""
        query = (f"SELECT {select_fields(fields, 'a.id')} "
                  "  FROM credit_accounts AS a "
                  " WHERE a.id = ? AND user_id = ?")
        abort_msg = f'Account ID {account_id} does not exist for the user.'
        account = self._query_entry(account_id, query, abort_msg)
        return account

    def process_account_form(self, form, account_id=None):
        """
        Process credit account information submitted on a form.

        Collect all credit account information submitted through the
        form. This aggregates all credit account data from the form,
        fills in defaults and makes inferrals when necessary, and then
        returns a dictionary mapping of the account information.

        Parameters
        ––––––––––
        form : CardForm
            An object containing the submitted form information.
        account_id : int, optional
            If given, the ID of the card to be updated. If left as
            `None`, a new credit card is created.

        Returns
        –––––––
        account : sqlite3.Row
            The saved account.
        """
        # Iterate through the account submission and create the dictionary
        mapping = {}
        for field in self.table_fields:
            if field == 'user_id':
                mapping[field] = self.user_id
            else:
                mapping[field] = form[field].data
        # Either create a new entry or update an existing entry
        if not account_id:
            account = self.new_entry(mapping)
        else:
            account = self.update_entry(account_id, mapping)
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
        ch = CardHandler()
        cards = ch.get_entries(fields=(), account_ids=entry_ids)
        card_ids = [card['id'] for card in cards]
        ch.delete_entries(card_ids)
        # Delete the given accounts
        super().delete_entries(entry_ids)
