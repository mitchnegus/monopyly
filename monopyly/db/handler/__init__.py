"""
A database handler for facilitating interactions with the SQLite database.
"""
from abc import ABC, abstractmethod

from flask import g
from werkzeug.exceptions import abort

from ..utils import get_db
from ..fields import DATABASE_FIELDS
from . import queries


class DatabaseHandler(ABC):
    """
    A generic handler for database access.

    Database handlers simplify commonly used database interactions.
    Complicated queries can be reformulated as class methods, taking
    variable arguments. The handler also performs user authentication
    upon creation so that user authentication is not required for each
    query.

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
    _queries = queries

    def __init__(self, db=None, user_id=None, check_user=True):
        # Set the fields for the handler
        self._table_fields = DATABASE_FIELDS[self.table]
        # Process arguments
        self.db = db if db else get_db()
        self.cursor = self.db.cursor()
        self.user_id = user_id if user_id else g.user['id']
        if check_user and self.user_id != g.user['id']:
            abort(403)

    @property
    @abstractmethod
    def table(self):
        raise NotImplementedError("The handler must have a defined table.")

    def get_entries(self, fields=None):
        """
        Retrieve a set of entries from the database.

        Executes a default simple for selecting the table entries from
        the database. By default, all database fields for the entries
        are returned.

        Parameters
        ––––––––––
        fields : tuple of str
            The fields (in the specified table) to be returned.
        """
        query = (f"SELECT {select_fields(fields)} "
                 f"  FROM {self.table} "
                  " WHERE user_id = ? ")
        placeholders = (self.user_id,)
        entries = self._query_entries(query, placeholders)
        return entries

    def _query_entries(self, query, placeholders):
        """Execute a query to return entries from the database."""
        entries = self.cursor.execute(query, placeholders).fetchall()
        return entries

    def get_entry(self, entry_id, fields=None):
        """
        Retrieve a single entry from the database.

        Executes a default simple query from the database to get a
        single entry. By default, all fields for the entry are returned.

        Parameters
        ––––––––––
        entry_id : int
            The ID of the entry to be found.
        fields : tuple of str, optional
            The fields (in the specified table) to be returned.

        Returns
        –––––––
        entry : sqlite3.Row
            The entry information from the database.
        """
        query = (f"SELECT {select_fields(fields)} "
                 f"  FROM {self.table} "
                  " WHERE id = ? AND user_id = ?")
        placeholders = (entry_id, self.user_id)
        entry = self._query_entry(entry_id, query, placeholders)
        return entry

    def _query_entry(self, query, placeholders, abort_msg=None):
        """Execute a query to return a single entry from the database."""
        entry = self.cursor.execute(query, placeholders).fetchone()
        # Check that an entry was found
        if entry is None:
            if not abort_msg:
                abort_msg = (f'The entry with ID {entry["id"]} does not exist '
                              'for the user.')
            abort(404, abort_msg)
        return entry

    def add_entry(self, mapping):
        """
        Create a new entry in the database given a mapping for fields.

        Accept a mapping relating given inputs to database fields. This
        mapping is used to insert a new entry into the database. All
        fields are sanitized prior to insertion. In general it is
        preferable to use a handler specific method as it will perform
        entry-specific inferences and preprocessing. This method should
        be used only when given a mapping that exactly corresponds to
        the new database entry.

        Parameters
        ––––––––––
        mapping : dict
            A mapping between database fields and the value to be
            entered into that field for the entry.

        Returns
        –––––––
        entry : sqlite3.Row
            The saved entry.
        """
        # Use default table name and query if not provided
        if self._table_fields !=  tuple(mapping.keys()):
            raise ValueError('The fields given in the mapping '
                            f'{tuple(mapping.keys())} do not match the fields '
                             'in the database. The fields must be the '
                             'following (in order): '
                            f'{", ".join(self._table_fields)}.')
        self.cursor.execute(
            f"INSERT INTO {self.table} {self._table_fields} "
            f"     VALUES ({self._queries.reserve_places(mapping.values())})",
            (*mapping.values(),)
        )
        self.db.commit()
        entry_id = self.cursor.lastrowid
        entry = self.get_entry(entry_id)
        return entry

    def update_entry(self, entry_id, mapping):
        """
        Update an entry in the database given a mapping for fields.

        Accept a mapping relating given inputs to database fields. This
        mapping is used to update an existing entry in the database. All
        fields are sanitized prior to updating.

        Parameters
        ––––––––––
        entry_id : int
            The ID of the entry to be updated.
        mapping : dict
            A mapping between database fields and the values to be
            updated in that field for the entry.

        Returns
        –––––––
        entry : sqlite3.Row
            The saved entry.
        """
        self._confirm_entry_owner(entry_id)
        # Check the validity of the mapping
        if not all(key in self._table_fields for key in mapping.keys()):
            raise ValueError('The mapping contains at least one field that '
                             'not match the database. Fields must be one of '
                            f'the following: {", ".join(self._table_fields)}.')
        update_fields = ', '.join([f'{field} = ?' for field in mapping])
        self.cursor.execute(
            f"UPDATE {self.table} "
            f"   SET {update_fields} "
             " WHERE id = ?",
            (*mapping.values(), entry_id)
        )
        self.db.commit()
        entry = self.get_entry(entry_id)
        return entry

    def delete_entries(self, entry_ids):
        """Delete entries in the database given their IDs."""
        for entry_id in entry_ids:
            self._confirm_entry_owner(entry_id)
        self.cursor.execute(
            "DELETE "
           f"  FROM {self.table} "
           f" WHERE id IN ({self._queries.reserve_places(entry_ids)})",
            entry_ids
        )
        self.db.commit()

    def _confirm_entry_owner(self, entry_id):
        # Ensure that the registered user owns the entry
        if self._get_entry_user_id(entry_id) != self.user_id:
            abort(403)

    def _get_entry_user_id(self, entry_id):
        # Get the user ID for a given entry
        return self.get_entry(entry_id, fields=('user_id',))['user_id']

