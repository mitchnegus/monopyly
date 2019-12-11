"""
Tools for dealing with the credit blueprint.
"""
import operator as op

from flask import g
from werkzeug.exceptions import abort

from ..db import get_db
from ..utils import parse_date, reserve_places
from .constants import ALL_FIELDS


def select_fields(fields, id_field=None):
    """
    Create a list of a given set of fields.

    Given a set of fields, create a list from the sequence to use when
    querying the database. If the fields parameter is set to `None`,
    then all fields in the database are returned. An optional 'id_field'
    can be provided to ensure that that field will always be returned,
    regardless of which other fields are provided.

    Parameters
    ––––––––––
    fields : tuple of str, None
        A list of fields to arrrange as a string for database querying.
    id_field : str, optional
        A field that will always be returned, regardless of the fields
        provided.
    """
    if fields is None:
        return "*"
    elif not all(field.split('.')[-1] in ALL_FIELDS for field in fields):
        raise ValueError('The given field does not exist in the database.')
    id_field_prefix = f'{id_field}, ' if id_field else ''
    return f"{id_field_prefix}{', '.join(fields)}"


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


def denote_if_date(field):
    """Return a query string specifically indicating date types."""
    if len(field) >= 5 and field[-5:] == '_date':
        query_string = f'{field} "{field} [date]"'
    else:
        query_string = field
    return query_string
