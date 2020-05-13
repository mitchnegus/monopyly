"""
Tools for dealing with the credit blueprint.
"""
import operator as op

from flask import g
from werkzeug.exceptions import abort

from monopyly.db import get_db
from monopyly.utils import parse_date, reserve_places, strip_function
from monopyly.credit.constants import ALL_FIELDS


def check_field(field):
    """Check that a field matches a credit card database field."""
    field = strip_function(field)
    if not field.split('.', 1)[-1] in ALL_FIELDS:
        raise ValueError(f"The field '{field}' does not exist in the "
                          "database.")


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
        A field that will always be returned, regardless of the other fields
        provided.
    """
    if fields is None:
        return "*"
    query_fields = [id_field] if id_field else []
    for field in fields:
        check_field(field)
        if field[-5:] == '_date':
            query_fields.append(query_date(field))
        else:
            query_fields.append(field)
    return f"{', '.join(query_fields)}"


def query_date(field):
    """Return a query string specifically indicating date types."""
    # Use sqlite3 converters to get the field as a date
    return f'{field} "{field} [date]"'
