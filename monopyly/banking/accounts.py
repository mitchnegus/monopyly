"""
Tools for interacting with bank accounts in the database.
"""
from ..utils import DatabaseHandler, fill_places, filter_items, select_fields
from .banks import BankHandler


class BankAccountHandler(DatabaseHandler):
    """
    A database handler for managing bank accounts.

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
    _table = 'bank_accounts'

    def __init__(self, db=None, user_id=None, check_user=True):
        super().__init__(db=db, user_id=user_id, check_user=check_user)

    def get_entries(self, bank_names=None, fields=None):
        """
        Get bank accounts from the database.

        Query the database to select bank account fields. Accounts can
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
            'bank_accounts' or 'banks' tables.

        Returns
        –––––––
        accounts : list of sqlite3.Row
            A list of bank accounts matching the criteria.
        """
        bank_filter = filter_items(bank_names, 'bank_name', 'AND')
        query = (f"SELECT {select_fields(fields, 'a.id')} "
                  "  FROM bank_accounts AS a "
                  "       INNER JOIN banks AS b "
                  "          ON b.id = a.bank_id "
                  " WHERE user_id = ? "
                 f"       {bank_filter} ")
        placeholders = (self.user_id, *fill_places(bank_names))
        accounts = self._query_entries(query, placeholders)
        return accounts

    def get_entry(self, account_id, fields=None):
        """Get a bank account from the database given its ID."""
        query = (f"SELECT {select_fields(fields, 'a.id')} "
                  "  FROM bank_accounts AS a "
                  "       INNER JOIN banks AS b "
                  "          ON b.id = a.bank_id "
                  " WHERE a.id = ? AND user_id = ?")
        placeholders = (account_id, self.user_id)
        abort_msg = f'Account ID {account_id} does not exist for the user.'
        account = self._query_entry(query, placeholders, abort_msg)
        return account

    def delete_entries(self, entry_ids):
        """
        Delete bank accounts from the database.

        Given a set of account IDs, delete the bank accounts from the
        database.

        Parameters
        ––––––––––
        entry_ids : list of int
            The IDs of accounts to be deleted.
        """
        # Delete the given accounts
        super().delete_entries(entry_ids)
