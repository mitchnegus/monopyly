"""General utility functions."""
import itertools as it
import operator as op
from datetime import datetime

from flask import g

from .db import get_db


class DatabaseHandler:
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

    def __init__(self, db=None, user_id=None, check_user=True):
        self.db = db if db else get_db()
        self.cursor = self.db.cursor()
        self.user_id = user_id if user_id else g.user['id']
        if check_user and self.user_id != g.user['id']:
            abort(403)


def filter_dict(dictionary, operator, condition, by_value=False):
    """Filter a dictionary by key using the given operator and condition."""
    if operator is op.contains:
        # `contains` method has reversed operands
        operator = lambda x, y: op.contains(y, x)
    if not by_value:
        return {k: v for k, v in dictionary.items() if operator(k, condition)}
    else:
        return {k: v for k, v in dictionary.items() if operator(v, condition)}


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

    Parameters
    ––––––––––
    given_date : str
        A date given in one of the acceptable formats to be formatted
        consistently with the database.

    Returns
    –––––––
    date : date
        A Python `date` object based on the given date string.
    """
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
            date = datetime.strptime(parseable_date, fmt).date()
            return (date)
        except ValueError:
            pass
    raise ValueError(err_msg)


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


def check_sort_order(sort_order):
    """Ensure that a valid sort order was provided."""
    if sort_order not in ('ASC', 'DESC'):
        raise ValueError('Provide a valid sort order.')
