"""
Flask blueprint for credit card financials.
"""
import operator as op
from dateutil.relativedelta import relativedelta

from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for
)
from werkzeug.exceptions import abort

from .utils import filter_dict, parse_date
from .db import get_db
from .auth import login_required
from .forms import *

# Define transaction database fields and corresponding display names
TRANSACTION_FIELDS = {'id': None,
                      'user_id': None,
                      'card_id': None,
                      'transaction_date': 'Date',
                      'vendor': 'Vendor',
                      'price': 'Price',
                      'notes': 'Notes',
                      'statement_date': 'Statement Date'}
CARD_FIELDS = {'id': None,
               'user_id': None,
               'bank': 'Bank',
               'last_four_digits': 'Last Four Digits',
               'statement_day': None,
               'active': None}
ALL_FIELDS = {**CARD_FIELDS, **TRANSACTION_FIELDS}
DISPLAY_FIELDS = filter_dict(ALL_FIELDS, op.is_not, None, by_value=True)
REQUIRED_CATEGORIES = ('transaction_date', 'vendor', 'price',
                       'notes', 'last_four_digits')
REQUIRED_FIELDS = filter_dict(DISPLAY_FIELDS, op.contains, REQUIRED_CATEGORIES)

bp = Blueprint('credit', __name__, url_prefix='/credit')

def get_transaction(transaction_id, check_user=True):
    """Given the ID of a transaction, get the transaction from the database."""
    # Get transaction information from the database
    db = get_db()
    query_fields = [denote_if_date(field) for field in DISPLAY_FIELDS]
    transaction_query = ('SELECT t.id, t.user_id, t.card_id,'
                        f'       {", ".join(query_fields)}'
                         '  FROM credit_transactions AS t'
                         '  JOIN credit_cards AS c ON t.card_id = c.id'
                         '  JOIN users AS u ON t.user_id = u.id'
                         ' WHERE t.id = ?')
    transaction = db.execute(transaction_query, (transaction_id,)).fetchone()
    # Check that a transaction was found and that it belongs to the user
    if transaction is None:
        abort(404, f'Transaction ID {transaction_id} does not exist.')
    if check_user and transaction['user_id'] != g.user['id']:
        abort(403)
    return transaction

def get_card_by_info(bank, last_four_digits, check_user=True):
    """Given the bank and last four digits, get the card from the database."""
    db = get_db()
    if not bank:
        card_query = 'SELECT * FROM credit_cards WHERE last_four_digits = ?'
        card = db.execute(card_query, (last_four_digits,)).fetchone()
    else:
        card_query = ('SELECT * FROM credit_cards'
                      ' WHERE bank = ? AND last_four_digits = ?')
        card = db.execute(card_query, (bank, last_four_digits)).fetchone()
    # Check that a card was found and that it belongs to the user
    if card is None:
        bank_name = f'{bank} ' if bank else ''
        abort(404, f'The {bank_name}card (****-{last_four_digits}) does not '
                    'exist.')
    if check_user and card['user_id'] != g.user['id']:
        abort(403)
    return card

def get_card_by_id(card_id, check_user=True):
    """Given the card ID in the database, get the card."""
    db = get_db()
    card_query = 'SELECT * FROM credit_cards WHERE id = ?'
    card = db.execute(card_query, (card_id,)).fetchone()
    # Check that a card belongs to the user
    if check_user and card['user_id'] != g.user['id']:
        abort(403)
    return card

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

    Returns
    –––––––
    card : sqlite3.Row
        A row in the database matching the card used in the transaction.
    transaction_info : dict
        A dictionary of transaction information collected (and/or extrapolated)
        from the user submission.
    """
    # Match the transaction to a registered credit card
    card = get_card_by_info(form['bank'], form['last_four_digits'])
    # Iterate through the transaction submission and create the dictionary
    transaction_info = {}
    for field in filter_dict(DISPLAY_FIELDS, op.contains, TRANSACTION_FIELDS):
        if form[field] and check_if_date(field):
            # The field was filled and should be a date
            transaction_info[field] = parse_date(form[field])
        else:
            transaction_info[field] = form[field]
    # Fill in the statement date field if it wasn't provided
    if not transaction_info['statement_date']:
        transaction_date = transaction_info['transaction_date']
        statement_date = get_expected_statement_date(transaction_date, card)
        transaction_info['statement_date'] = statement_date
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

def error_unless_all_fields_provided(fields):
    """Check that all fields have been given on a submitted form."""
    if not all(request.form[field] for field in fields):
        error = 'All fields are required.'
    else:
        error = None
    return error

@bp.route('/transactions')
@login_required
def show_transactions():
    # Get all transactions from the database
    db = get_db()
    query_fields = list(DISPLAY_FIELDS.keys())
    transactions_query = (f'SELECT t.id, {", ".join(query_fields)}'
                           '  FROM credit_transactions AS t'
                           '  JOIN credit_cards AS c ON t.card_id = c.id'
                           '  JOIN users AS u ON t.user_id = u.id'
                           ' ORDER BY transaction_date')
    transactions = db.execute(transactions_query).fetchall()
    return render_template('credit/transactions.html',
                           transactions=transactions)

@bp.route('/<int:transaction_id>/transaction')
@login_required
def show_transaction(transaction_id):
    # Get the transaction information from the database
    transaction = get_transaction(transaction_id)
    # Match the transaction to a registered credit card
    card = get_card_by_id(transaction['card_id'])
    return render_template('credit/transaction.html',
                           transaction=transaction,
                           card=card)

@bp.route('/new_transaction', methods=('GET', 'POST'))
@login_required
def new_transaction():
    # Define a form for a transaction
    form = TransactionForm()
    # Check if a transaction was submitted and add it to the database
    if request.method == 'POST' and form.validate():
        error = error_unless_all_fields_provided(REQUIRED_FIELDS)
        if not error:
            card, transaction_info = process_transaction(request.form)
            # Insert the new transaction into the database
            db = get_db()
            mapping = prepare_db_transaction_mapping(TRANSACTION_FIELDS,
                                                     transaction_info,
                                                     card['id'])
            db.execute(
                f'INSERT INTO credit_transactions {tuple(mapping.keys())}'
                 'VALUES (?, ?, ?, ?, ?, ?, ?)',
                (*mapping.values(),)
            )
            db.commit()
            return render_template('credit/submission.html',
                                   field_names=DISPLAY_FIELDS,
                                   card=card,
                                   transaction=transaction_info,
                                   update=False)
        else:
            flash(error)
    # Display the form for accepting user input
    return render_template('credit/new_transaction.html', form=form)

@bp.route('/<int:transaction_id>/update_transaction', methods=('GET', 'POST'))
@login_required
def update_transaction(transaction_id):
    # Get the transaction information from the database
    transaction = get_transaction(transaction_id)
    # Define a form for a transaction
    form = UpdateTransactionForm(data=transaction)
    # Check if a transaction was updated and update it in the database
    if request.method == 'POST':
        error = error_unless_all_fields_provided(REQUIRED_FIELDS)
        if not error:
            card, transaction_info = process_transaction(request.form)
            # Update the database with the updated transaction
            db = get_db()
            mapping = prepare_db_transaction_mapping(TRANSACTION_FIELDS,
                                                     transaction_info,
                                                     card['id'])
            update_fields = [f'{field} = ?' for field in mapping]
            db.execute(
                'UPDATE credit_transactions'
               f'   SET {", ".join(update_fields)}'
                ' WHERE id = ?',
                (*mapping.values(), transaction_id)
            )
            db.commit()
            return render_template('credit/submission.html',
                                   field_names=DISPLAY_FIELDS,
                                   card=card,
                                   transaction=transaction_info,
                                   update=True)
        else:
            flash(error)
    # Display the form for accepting user input
    return render_template('credit/update_transaction.html',
                           transaction_id=transaction_id, form=form)

@bp.route('/<int:transaction_id>/delete_transaction', methods=('POST',))
@login_required
def delete_transaction(transaction_id):
    # Get the transaction (to ensure that it exists)
    get_transaction(transaction_id)
    # Remove the transaction from the database
    db = get_db()
    db.execute(
        'DELETE FROM credit_transactions WHERE id = ?',
        (transaction_id,)
    )
    db.commit()
    return redirect(url_for('credit.show_transactions'))
