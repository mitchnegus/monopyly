"""
Tools for interacting with banks in the database.
"""
from ..utils import DatabaseHandler, fill_places, filter_items, select_fields


class BankHandler(DatabaseHandler):
    """
    A database handler for managing bank information.

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
    _table = 'banks'

    def get_entries(self, bank_names=None, fields=None):
        """
        Get banks from the database.

        Query the database to select bank fields. Banks can be filtered
        by name. All fields are shown by default.

        Parameters
        ––––––––––
        bank_names : tuple of str, optional
            A sequence of bank names for which cards will be selected
            (if `None`, all banks will be selected).
        fields : tuple of str, optional
            A sequence of fields to select from the database (if `None`,
            all fields will be selected). Can be any field in the
            'banks' table.

        Returns
        –––––––
        banks : list of sqlite3.Row
            A list of banks matching the criteria.
        """
        bank_filter = filter_items(bank_names, 'bank_name', 'AND')
        query = (f"SELECT {select_fields(fields, 'b.id')} "
                  "  FROM banks AS b "
                  " WHERE user_id = ? "
                 f"       {bank_filter} ")
        placeholders = (self.user_id, *fill_places(bank_names))
        banks = self._query_entries(query, placeholders)
        return banks

    def get_entry(self, bank_id, fields=None):
        """Get a bank from the database given its ID."""
        query = (f"SELECT {select_fields(fields, 'b.id')} "
                  "  FROM banks AS b "
                  " WHERE b.id = ? AND user_id = ?")
        placeholders = (bank_id, self.user_id)
        abort_msg = f'Bank ID {bank_id} does not exist for the user.'
        bank = self._query_entry(query, placeholders, abort_msg)
        return bank
