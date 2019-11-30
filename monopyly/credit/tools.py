"""
Tools for dealing with the credit blueprint.
"""
import operator as op
from dateutil.relativedelta import relativedelta

from flask import g
from werkzeug.exceptions import abort

from .cards import CardHandler
from .constants import DISPLAY_FIELDS, TRANSACTION_FIELDS
from ..utils import filter_dict, parse_date
from ..db import get_db


def get_card_by_info(user_id, bank, last_four_digits, check_user=True):
    """Given the user, bank and last four digits, get the card from the database."""
    db = get_db()
    cursor = db.cursor()
    if not bank:
        card_query = ('SELECT * FROM credit_cards'
                      ' WHERE user_id = ?'
                      '   AND last_four_digits = ?')
        placeholders = (user_id, last_four_digits)
    else:
        card_query = ('SELECT * FROM credit_cards'
                      ' WHERE user_id = ?'
                      '   AND bank = ? AND last_four_digits = ?')
        placeholders = (user_id, bank, last_four_digits)
    card = cursor.execute(card_query, placeholders).fetchone()
    # Check that a card was found and that it belongs to the user
    if card is None:
        bank_name = f'{bank} ' if bank else ''
        abort(404, f'The {bank_name}card (****-{last_four_digits}) does not '
                    'exist.')
    if check_user and card['user_id'] != g.user['id']:
        abort(403)
    return card

def get_card_ids_from_filters(user_id, filter_ids):
    """
    Convert a filter ID into a card ID.

    Given a JSON converted POST request of filter IDs, convert the list into a
    list of corresponding card IDs from the database.

    Parameters
    ––––––––––
    user_id : str
        The unique ID of the user for whom to filter the cards.
    filter_ids : list
        A list of IDs for the filters (of the form BANK-LAST_FOUR_DIGITS).

    Returns
    –––––––
    card_ids : list
        A list of database card IDs corresponding to the input list of filters.
    """
    # Split the filter ID into 'bank' and 'last_four_digits' elements
    filter_info = [filter_id.split('-') for filter_id in filter_ids]
    # Get the corresponding cards from the database
    card_ids = [get_card_by_info(user_id, *info)['id'] for info in filter_info]
    return card_ids

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

def process_transaction(form):
    """
    Collect submitted transaction information.

    Collect all transaction information submitted through the form. This
    aggregates all transaction data from the form, fills in defaults when
    necessary, and returns a dictionary of the transaction information.

    Parameters
    ––––––––––
    form : werkzeug.datastructures.ImmutableMultiDict
        A MultiDict containing the submitted form information.

    Returns
    –––––––
    card : sqlite3.Row
        A row in the database matching the card used in the transaction.
    transaction_info : dict
        A dictionary of transaction information collected (and/or extrapolated)
        from the user submission.
    """
    # Match the transaction to a registered credit card
    user_id = g.user['id']
    card = get_card_by_info(user_id, form['bank'], form['last_four_digits'])
    # Iterate through the transaction submission and create the dictionary
    transaction_info = {}
    selected_fields = list(TRANSACTION_FIELDS.keys()) + ['issue_date']
    for field in filter_dict(DISPLAY_FIELDS, op.contains, selected_fields):
        if form[field] and check_if_date(field):
            # The field should be a date
            transaction_info[field] = parse_date(form[field])
        elif form[field] and field == 'price':
            # Prices should be shown to 2 digits
            transaction_info[field] = f'{float(form[field]):.2f}'
        else:
            transaction_info[field] = form[field]
    # Fill in the statement date field if it wasn't provided
    if not transaction_info['issue_date']:
        transaction_date = transaction_info['transaction_date']
        statement_date = get_expected_statement_date(transaction_date, card)
        transaction_info['issue_date'] = statement_date
    return card, transaction_info

def prepare_db_transaction_mapping(fields, values, card_id):
    """
    Prepare a field-value mapping for use with a database insertion/update.

    Given a set of database fields and a set of values, return a mapping of
    all the fields and values. For fields that do not have a corresponding
    value, do not include them in the mapping unless a value is otherwise
    explicitly defined.

    Parameters
    ––––––––––
    fields : iterable
        A set of fields corresponding to fields in the database.
    values : dict
        A mapping of fields and values (entered by a user for a transaction).
    card_id : int
        The ID of the card to be associated with the transaction.

    Returns
    –––––––
    mapping : dict
        A mapping between all fields to be entered into the database and the
        corresponding values.
    """
    mapping = {}
    for field in fields:
        if field != 'id':
            if field[-3:] != '_id':
                mapping[field] = values[field]
            elif field == 'user_id':
                mapping[field] = g.user['id']
            elif field == 'card_id':
                mapping[field] = card_id
    return mapping

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

def error_unless_all_fields_provided(form, fields):
    """Check that all fields have been given on a submitted form."""
    if not all(form[field] for field in fields):
        error = 'All fields are required.'
    else:
        error = None
    return error
