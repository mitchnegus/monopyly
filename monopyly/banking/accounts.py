"""
Tools for interacting with bank accounts in the database.
"""
from ..utils import (
    DatabaseHandler, fill_place, fill_places, filter_item, filter_items,
    select_fields
)
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

    def find_account(self, bank_name=None, last_four_digits=None,
                     account_type=None, fields=None):
        """
        Find a bank account using uniquely identifying characteristics.

        Queries the database to find a bank account based on the
        provided criteria. Bank accounts in the database can almost
        always be identified uniquely given the user's ID, the last
        four digits of the account number, and the account type.
        In rare cases where a user has two accounts of the same type
        both with the same last four digits, the bank name can be used to
        to help determine the account. (It is expected to be
        exceptionally rare that a user has two accounts of the same
        type, both with the same last four digits, and both from the
        same bank.) If multiple cards do match the criteria, only the
        first one found is returned.

        Parameters
        ––––––––––
        bank_name : str, optional
            The bank of the account to find.
        last_four_digits : int, optional
            The last four digits of the bank account to find.
        account_type : str, optional
            The type of account to find.
        fields : tuple of str, optional
            The fields (in either the banks or bank accounts tables) to
            be returned.

        Returns
        –––––––
        account : sqlite3.Row
            A bank account entry matching the given criteria. If no
            matching account is found, returns `None`.
        """
        bank_filter = filter_item(bank_name, 'bank_name', 'AND')
        digit_filter = filter_item(last_four_digits, 'last_four_digits', 'AND')
        type_filter = filter_item(account_type, 'account_type', 'AND')
        query = (f"SELECT {select_fields(fields, 'a.id')} "
                  "  FROM bank_accounts AS a "
                  "       INNER JOIN banks AS b "
                  "          ON b.id = a.bank_id "
                  " WHERE user_id = ? "
                 f"       {bank_filter} {digit_filter} {type_filter}")
        placeholders = (self.user_id, *fill_place(bank_name),
                        *fill_place(last_four_digits),
                        *fill_place(account_type))
        account = self.cursor.execute(query, placeholders).fetchone()
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
