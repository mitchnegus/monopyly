"""
Tools for dealing with the credit blueprint.
"""
import operator as op
from dateutil.relativedelta import relativedelta

from flask import g
from werkzeug.exceptions import abort

from ..db import get_db
from ..utils import parse_date, reserve_places
from .constants import ALL_FIELDS


def get_expected_statement_date(transaction_date, card):
    """Give the expected statement date given the card and transaction date."""
    statement_day = card['statement_day']
    curr_month_statement_date = transaction_date.replace(day=statement_day)
    if transaction_date.day < statement_day:
        # The transaction will be on the statement later in the month
        statement_date = curr_month_statement_date
    else:
        # The transaction will be on the next month's statement
        statement_date = curr_month_statement_date + relativedelta(months=+1)
    return statement_date


def select_fields(fields):
    """Create placeholders for given fields (all fields if none are given)."""
    if fields is None:
        return "*"
    elif not all(field.split('.')[-1] in ALL_FIELDS for field in fields):
        raise ValueError('The given field does not exist in the database.')
    return ', '.join(fields)


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


def check_if_date(field):
    """Check if a field is a date."""
    return (len(field) >= 4 and field[-4:] == 'date')


def denote_if_date(field):
    """Return a query string specifically indicating date types."""
    if check_if_date(field):
        query_string = f'{field} "{field} [date]"'
    else:
        query_string = field
    return query_string
