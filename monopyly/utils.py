"""
General utility objects.
"""
from abc import ABC, abstractmethod
import itertools as it
import datetime

from flask import g
from werkzeug.exceptions import abort

from monopyly.db import get_db


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
    db : sqlite3.Connection
        A connection to the database for interfacing.
    cursor : sqlite.Cursor
        A cursor for executing database interactions.
    user_id : int
        The ID of the user who is the subject of database access.
    """
    table_name = None
    table_fields = ()

    def __init__(self, db=None, user_id=None, check_user=True):
        self.db = db if db else get_db()
        self.cursor = self.db.cursor()
        self.user_id = user_id if user_id else g.user['id']
        if check_user and self.user_id != g.user['id']:
            abort(403)

    @abstractmethod
    def get_entries(self, fields=None):
        raise NotImplementedError('This is an Abstract Base Class. Define '
                                  'a `get_entries` method in a subclass.')

    def _query_entries(self, query=None, placeholders=None):
        """
        Execute a query to return entries from the database.

        Accepts an optional query for selecting entries from the
        database. If no query is provided, a default query getting all
        database fields is used.

        Parameters
        ––––––––––
        query : str, optional
            A query to use in selecting entries. The query may include
            placeholders.
        placeholders : tuple, optional
            Placeholders to be substituted into the query safely.
        """
        if not query:
            query = (f"SELECT * "
                     f"  FROM {self.table_name} "
                      " WHERE user_id = ?")
            placeholders = (self.user_id,)
        entries = self.cursor.execute(query, placeholders).fetchall()
        return entries

    @abstractmethod
    def get_entry(self, entry_id, fields=None):
        raise NotImplementedError('This is an Abstract Base Class. Define '
                                  'a `get_entry` method in a subclass.')

    def _query_entry(self, entry_id, query=None, abort_msg=None):
        """Execute a query to return a single entry from the database."""
        if not query:
            query = (f"SELECT * "
                     f"  FROM {self.table_name} "
                      " WHERE id = ? AND user_id = ?")
        placeholders = (entry_id, self.user_id)
        entry = self.cursor.execute(query, placeholders).fetchone()
        # Check that an entry was found
        if not entry:
            if not abort_msg:
                abort_msg = (f'The entry with ID {entry_id} does not exist '
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
        if tuple(self.table_fields) !=  tuple(mapping.keys()):
            raise ValueError('The fields given in the mapping '
                            f'{tuple(mapping.keys())} do not match the fields '
                             'in the database. The fields must be the '
                            f'following: {", ".join(self.table_fields)}.')
        self.cursor.execute(
            f"INSERT INTO {self.table_name} {tuple(self.table_fields)} "
            f"     VALUES ({reserve_places(mapping.values())})",
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
        if not all(key in self.table_fields for key in mapping.keys()):
            raise ValueError('The mapping contains at least one field that '
                             'not match the database. Fields must be one of '
                            f'the following: {", ".join(self.table_fields)}.')
        update_fields = ', '.join([f'{field} = ?' for field in mapping])
        self.cursor.execute(
            f"UPDATE {self.table_name} "
            f"   SET {update_fields} "
             " WHERE id = ?",
            (*mapping.values(), entry_id)
        )
        self.db.commit()
        entry = self.get_entry(entry_id)
        return entry

    def delete_entries(self, entry_ids):
        """Delete entries in the database given their IDs."""
        # Check that the entries exist and belong to the user
        for entry_id in entry_ids:
            self.get_entry(entry_id)
        self.cursor.execute(
            "DELETE "
           f"  FROM {self.table_name} "
           f" WHERE id IN ({reserve_places(entry_ids)})",
            entry_ids
        )
        self.db.commit()


def parse_date(given_date):
    """
    Given a string in an accepted format, return a Python date object.

    All dates should be stored in the database as YYYY-MM-DD, but can be
    added to the database directly from Python date objects. This
    function takes a date that is given as any of the acceptable formats
    and returns a date object (which can be added into the database).
    The following are acceptable date formats (in order of parsing
    precedence):
        - YYYYMMDD
        - YYYY/[M]M/[D]
        - [M]M/[D]D/[YY]YY
    Dates with a delimiter between time categories (day, month, year)
    are not required to have two digit values (e.g. 'August' could be
    indicated by '08' or just '8'). For dates that are given with a
    delimiter, it may be either "/", ".", or "-".

    If a `datetime.date` object is given, it is returned without
    processing.

    Parameters
    ––––––––––
    given_date : str, datetime.date
        A date given in one of the acceptable formats to be formatted
        consistently with the database.

    Returns
    –––––––
    date : datetime.date
        A Python `date` object based on the given date string.
    """
    if not given_date:
        return None
    if isinstance(given_date, datetime.date):
        return given_date
    # Handle options for alternate delimiters
    alt_delimiters = ('.', '/')
    date_formats = ('%Y-%m-%d', '%m-%d-%Y', '%m-%d-%y')
    err_msg = (f"The given date ('{given_date}') was not in an acceptable "
                "format. Try entering the date in the format 'YYYY-MM-DD'.")
    # Make the delimiter consistent and split the date into components
    delimited_date = given_date
    for delimiter in alt_delimiters:
        delimited_date = delimited_date.replace(delimiter, '-')
    # Zero pad all date components to be at least length 2
    split_date = delimited_date.split('-')
    if len(split_date) == 3:
        components = [f'{_:0>2}' if len(_) < 2 else _ for _ in split_date]
    elif len(split_date) == 1 and len(given_date) == 8:
        components = [given_date[:4], given_date[4:6], given_date[6:]]
    else:
        raise ValueError(err_msg)
    parseable_date = '-'.join(components)
    # Join the components back together and parse with `datetime` module
    for fmt in date_formats:
        try:
            date = datetime.datetime.strptime(parseable_date, fmt).date()
            return date
        except ValueError:
            pass
    raise ValueError(err_msg)


def strip_function(field):
    """Return a database field name, even if it's a function argument."""
    functions = ('COALESCE', 'SUM', 'MAX', 'MIN')
    while any(field.upper().startswith(function) for function in functions):
        # A function was given, and the column name should be isolated
        field = field.split('(', 1)[-1].rsplit(')', 1)[0]
    return field


def dedelimit_float(value):
    """Remove delimiters from strings before conversion to floats."""
    delimiter = ','
    try:
        return float(value.replace(delimiter, ''))
    except AttributeError:
        return value


def reserve_places(placeholders):
    """Reserve a set of places matching the placeholders input."""
    return ', '.join(['?']*len(placeholders))


def fill_place(placeholder):
    """Generate a singular tuple for a placeholder (if it is given)."""
    if placeholder is None:
        return ()
    return (placeholder,)


def fill_places(placeholders):
    """Generate a tuple for a sequence of placeholders (if it is given)."""
    if placeholders is None:
        return ()
    return tuple(placeholders)


def filter_item(item, db_item_name, prefix=""):
    """Create a filter based on a given item."""
    if item is None:
        return ""
    return f"{prefix} {db_item_name} = ?"


def filter_items(items, db_item_name, prefix=""):
    """Create a filter based on a set of items."""
    if items is None:
        return ""
    return f"{prefix} {db_item_name} IN ({reserve_places(items)})"


def check_sort_order(sort_order):
    """Ensure that a valid sort order was provided."""
    if sort_order not in ('ASC', 'DESC'):
        raise ValueError('Provide a valid sort order.')
