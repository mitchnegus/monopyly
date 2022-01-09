"""
Tools for interacting with bank accounts in the database.
"""
from ..utils import (
    DatabaseHandler, fill_place, fill_places, filter_item, filter_items,
    select_fields
)
from .banks import BankHandler


class BankAccountTypeHandler(DatabaseHandler):
    """
    A database handler for managing bank account types.

    Parameters
    ----------
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
    _table = 'bank_account_types'
    _table_view = 'bank_account_types_view'

    def get_entries(self, fields=None):
        """
        Get bank account types from the database.

        Query the database to select bank account type fields. Accounts
        types can be filtered by name. All fields for all accounts are
        shown by default.

        Parameters
        ––––––––––
        fields : tuple of str, optional
            A sequence of fields to select from the database (if `None`,
            all fields will be selected). Can be any field in the
            'banks' or 'bank_account_types' tables.

        Returns
        –––––––
        account_types : list of sqlite3.Row
            A list of bank accounts types matching the criteria.
        """
        query = (f"SELECT {select_fields(fields, 'types.id')} "
                  "  FROM bank_account_types_view AS types"
                 f" WHERE user_id IN (0, ?)")
        placeholders = (self.user_id,)
        account_types = self._query_entries(query, placeholders)
        return account_types

    def get_entry(self, account_type_id, fields=None):
        """Get a bank account type from the database given its ID."""
        query = (f"SELECT {select_fields(fields, 'types.id')} "
                  "  FROM bank_account_types_view AS types"
                  " WHERE types.id = ? AND user_id IN (0, ?)")
        placeholders = (account_type_id, self.user_id)
        abort_msg = (f'Account type ID {account_type_id} does not exist for '
                      'the user.')
        account = self._query_entry(query, placeholders, abort_msg)
        return account

    def find_account_type(self, type_name=None, type_abbreviation=None,
                          fields=None):
        """
        Find an account type using uniquely identifying characteristics.

        Queries the database to find a bank account type based on the
        provided criteria. Bank account types in the database can always
        be identified uniquely given the user's ID and either the name
        of an account type or the abbreviation of that name.

        Parameters
        ––––––––––
        type_name : str, optional
            The bank account type to find.
        type_abbreviation : str, optional
            The bank account type abbreviation to find.
        fields : tuple of str, optional
            The fields (in the bank account types table) to
            be returned.

        Returns
        –––––––
        account_type : sqlite3.Row
            A bank account type entry matching the given criteria. If no
            matching account type is found, returns `None`.
        """
        type_filter = filter_item(type_name, 'type_name', 'AND')
        digit_filter = filter_item(last_four_digits, 'last_four_digits', 'AND')
        abbreviation_filter = filter_item(type_abbreviation,
                                          'type_abbreviation',
                                          'AND')
        query = (f"SELECT {select_fields(fields, 'types.id')} "
                  "  FROM bank_account_types AS types "
                  " WHERE user_id IN (0, ?) "
                 f"       {type_filter} {abbreviation_filter}")
        placeholders = (self.user_id, *fill_place(type_name),
                        *fill_place(type_abbreviation))
        account_type = self.cursor.execute(query, placeholders).fetchone()
        return account_type

    def get_types_for_bank(self, bank_id):
        """Return a list of the bank account type IDs that exist for a bank."""
        query = ("SELECT DISTINCT types.* "
                 "  FROM bank_account_types_view AS types "
                 "       INNER JOIN bank_accounts AS a "
                 "          ON a.account_type_id = types.id "
                 "       INNER JOIN banks AS b "
                 "          ON b.id = a.bank_id "
                 " WHERE types.user_id IN (0, ?) AND b.id = ?")
        placeholders = (self.user_id, bank_id)
        account_types = self.cursor.execute(query, placeholders).fetchall()
        return account_types

    def _add_entry(self):
        # Should prevent a user from duplicating the common entries
        pass

    def delete_entries(self, entry_ids):
        """
        Delete bank account types from the database.

        Given a set of account type IDs, delete the bank account types
        from the database.

        Parameters
        ––––––––––
        entry_ids : list of int
            The IDs of account types to be deleted.
        """
        # Delete the given account types
        # Should prevent user from deleting common entries
        # Should ensure that this account type is deleted in all use locations
        super().delete_entries(entry_ids)


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
    _table_view = 'bank_accounts_view'

    def get_entries(self, bank_ids=None, account_type_ids=None, fields=None):
        """
        Get bank accounts from the database.

        Query the database to select bank account fields. Accounts can
        be filtered by the issuing bank. All fields for all accounts are
        shown by default.

        Parameters
        ––––––––––
        bank_ids : tuple of int, optional
            A sequence of bank IDs for which accounts will be selected
            (if `None`, all banks will be selected).
        account_type_ids : tuple of int, optional
            A sequence of bank account type IDs for which account types
            will be selected (if `None`, all account types will be
            selected).
        fields : tuple of str, optional
            A sequence of fields to select from the database (if `None`,
            all fields will be selected). Can be any field in the
            'bank_accounts' or 'banks' tables.

        Returns
        –––––––
        accounts : list of sqlite3.Row
            A list of bank accounts matching the criteria.
        """
        bank_filter = filter_items(bank_ids, 'b.id', 'AND')
        type_filter = filter_items(account_type_ids, 'types.id', 'AND')
        query = (f"SELECT {select_fields(fields, 'a.id')} "
                  "  FROM bank_accounts_view AS a "
                  "       INNER JOIN banks AS b "
                  "          ON b.id = a.bank_id "
                  "       INNER JOIN bank_account_types_view as types "
                  "          ON types.id = a.account_type_id "
                  " WHERE b.user_id = ? "
                 f"       {bank_filter} {type_filter}")
        placeholders = (self.user_id, *fill_places(bank_ids),
                        *fill_places(account_type_ids))
        accounts = self._query_entries(query, placeholders)
        return accounts

    def get_entry(self, account_id, fields=None):
        """Get a bank account from the database given its ID."""
        query = (f"SELECT {select_fields(fields, 'a.id')} "
                  "  FROM bank_accounts_view AS a "
                  "       INNER JOIN banks AS b "
                  "          ON b.id = a.bank_id "
                  "       INNER JOIN bank_account_types_view AS types "
                  "          ON types.id = a.account_type_id "
                  " WHERE a.id = ? AND b.user_id = ?")
        placeholders = (account_id, self.user_id)
        abort_msg = f'Account ID {account_id} does not exist for the user.'
        account = self._query_entry(query, placeholders, abort_msg)
        return account

    def find_account(self, bank_name=None, last_four_digits=None,
                     account_type_name=None, fields=None):
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
        account_type_name : str, optional
            The name of the account type to find.
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
        type_filter = filter_item(account_type_name, 'type_name', 'AND')
        query = (f"SELECT {select_fields(fields, 'a.id')} "
                  "  FROM bank_accounts_view AS a "
                  "       INNER JOIN banks AS b "
                  "          ON b.id = a.bank_id "
                  "       INNER JOIN bank_account_types_view AS types "
                  "          ON types.id = a.account_type_id "
                  " WHERE b.user_id = ? "
                 f"       {bank_filter} {digit_filter} {type_filter}")
        placeholders = (self.user_id, *fill_place(bank_name),
                        *fill_place(last_four_digits),
                        *fill_place(account_type_name))
        account = self.cursor.execute(query, placeholders).fetchone()
        return account

    def get_balance(self, bank_id):
        """Get the balance of all accounts at one bank."""
        query = ("SELECT sum(balance) balance "
                 "  FROM bank_accounts_view AS a"
                 "  LEFT OUTER JOIN banks AS b "
                 "    ON b.id = a.bank_id "
                 " WHERE b.user_id = ? AND b.id = ?")
        placeholders = (self.user_id, bank_id)
        balance = self.cursor.execute(query, placeholders).fetchone()[0]
        return balance

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
