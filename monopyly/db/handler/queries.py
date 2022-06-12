"""
A module with functions specific to making database handler queries.
"""
import datetime

from ..fields import DATABASE_FIELDS


ALL_FIELDS = [field for fields in DATABASE_FIELDS.values() for field in fields]
# Many tables have an 'id' field that is not included in `DATABASE_FIELDS`
ALL_FIELDS.append('id')


def validate_field(field, field_list=None):
    """
    Check that a named field matches a database field.

    Parameters
    ----------
    field : str
        A field name to be validated.
    field_list : list, optional
        A set of field names to be used when determining valid fields.
        The default is `None`, in which case all fields in the database
        (and only those fields) are considered valid names.
    """
    field = strip_function(field)
    if field_list is None:
        field_list = ALL_FIELDS
        err_msg = f"The field '{field}' does not exist in the database."
    else:
        if not all(field in ALL_FIELDS for field in field_list):
            raise ValueError("The list of fields given contains fields that "
                             "are not present in the global list of available "
                             "fields. This poses a security risk and is "
                             "disallowed.")
        err_msg = f"The field '{field}' is not in the given list of fields."
    if field.split('.', 1)[-1] not in field_list:
        raise ValueError(err_msg)


def validate_sort_order(sort_order):
    """
    Ensure that a valid sort order was provided.

    Parameters
    ----------
    sort_order : str
        The order, ascending or descending, that should be used when
        sorting the returned values from the database query. The order
        must be either 'ASC' or 'DESC'.
    """
    if sort_order not in ('ASC', 'DESC'):
        raise ValueError('Provide a valid sort order.')


def strip_function(field):
    """Return a database field name, even if it's a function argument."""
    functions = ('COALESCE', 'SUM', 'MAX', 'MIN')
    while any(field.upper().startswith(function) for function in functions):
        # A function was given, and the column name should be isolated
        field = field.split('(', 1)[-1].rsplit(')', 1)[0]
    return field


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


def filter_item(item, field, prefix=""):
    """Create a filter based on a given item."""
    validate_field(field)
    if item is None:
        return ""
    return f"{prefix} {field} = ?"


def filter_items(items, field, prefix=""):
    """Create a filter based on a set of items."""
    validate_field(field)
    if items is None:
        return ""
    return f"{prefix} {field} IN ({reserve_places(items)})"


def filter_dates(start_date, end_date, field, prefix=""):
    """Create a filter for a date range."""
    validate_field(field)
    start_filter, end_filter = "", ""
    if start_date is None and end_date is None:
        return ""
    if isinstance(start_date, datetime.date):
        start_filter = f"{field} >= {start_date}"
    if isinstance(end_date, datetime.date):
        end_filter = f"{field} <= {end_date}"
    date_filter = ' AND '.join([_ for _ in (start_filter, end_filter) if _])
    return f"{prefix} {date_filter}"


def prepare_date_query(field):
    """Return a query string specifically indicating date types."""
    # Use sqlite3 converters to get the field as a date
    return f'{field} "{field} [date]"'


def select_fields(fields, id_field=None, convert_dates=True):
    """
    Create a list of a given set of fields.

    Given a set of fields, create a list from the sequence to use when
    querying the database. If the fields parameter is set to `None`,
    then all fields in the database are returned. An optional 'id_field'
    can be provided to ensure that that field will always be returned,
    regardless of which other fields are provided. Note that field names
    ending with the string '_date' are automatically converted to Python
    `datetime.date` objects. This behavior can be disabled by setting
    the `convert_dates` flag to `False`.

    Parameters
    ––––––––––
    fields : tuple of str, None
        A list of fields to arrrange as a string for database querying.
    id_field : str, optional
        A field that will always be returned, regardless of the other
        fields provided.
    convert_dates : bool, optional
        A flag indicating whether field names ending with '_date' are
        automatically converted into Python `datetime.date` objecs.
    """
    if fields is None:
        return "*"
    query_fields = [id_field] if id_field else []
    for field in fields:
        validate_field(field)
        if field[-5:] == '_date' and convert_dates:
            query_fields.append(prepare_date_query(field))
        else:
            query_fields.append(field)
    return f"{', '.join(query_fields)}"

