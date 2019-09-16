"""
Flask blueprint for credit card financials.
"""
from flask import (
    Blueprint, flash, g, redirect, render_template,
    request, session, url_for, jsonify
)

from ..db import get_db
from ..auth import login_required
from ..forms import *
from .constants import (
    CARD_FIELDS, TRANSACTION_FIELDS, REQUIRED_FIELDS, DISPLAY_FIELDS
)
from .tools import *

# Define the blueprint
bp = Blueprint('credit', __name__, url_prefix='/credit')

@bp.route('/transactions')
@login_required
def show_transactions():
    db, cursor = get_db()
    # Get all of the user's credit cards from the database
    cards_query = ('SELECT id, bank, last_four_digits, active'
                   '  FROM credit_cards'
                   ' WHERE user_id = ?'
                   ' ORDER BY active DESC')
    cards = cursor.execute(cards_query, (g.user['id'],)).fetchall()
    # Get all of the user's transactions from the database
    query_fields = list(DISPLAY_FIELDS.keys())
    sort_order = 'DESC'
    transactions_query = (f'SELECT t.id, {", ".join(query_fields)}'
                           '  FROM credit_transactions AS t'
                           '  JOIN credit_cards AS c ON t.card_id = c.id'
                           ' WHERE c.user_id = ? AND c.active = 1'
                          f' ORDER BY transaction_date {sort_order}')
    placeholders = (g.user['id'],)
    transactions = cursor.execute(transactions_query, placeholders).fetchall()
    return render_template('credit/transactions.html',
                           cards=cards,
                           sort_order=sort_order,
                           transactions=transactions)

@bp.route('/_update_transaction_table', methods=('POST',))
@login_required
def update_transaction_table():
    # Separate the arguments of the POST method
    post_arguments = request.get_json()
    filter_ids = post_arguments['filter_ids']
    sort_order = 'ASC' if post_arguments['sort_order'] == 'asc' else 'DESC'
    # Determine the card IDs from the arguments of POST method
    card_ids = get_card_ids_from_filters(g.user['id'],
                                         post_arguments['filter_ids'])
    # Filter selected transactions from the database
    db, cursor = get_db()
    query_fields = list(DISPLAY_FIELDS.keys())
    if card_ids:
        card_id_fields = ['?']*len(card_ids)
    else:
        card_id_fields = ['""']
    filter_query = (f'SELECT t.id, {", ".join(query_fields)}'
                     '  FROM credit_transactions AS t'
                     '  JOIN credit_cards AS c ON t.card_id = c.id'
                     ' WHERE c.user_id = ?'
                    f'   AND c.id IN ({", ".join(card_id_fields)})'
                    f' ORDER BY transaction_date {sort_order}')
    placeholders = (g.user['id'], *card_ids)
    transactions = cursor.execute(filter_query, placeholders).fetchall()
    return render_template('credit/transaction_table.html',
                           sort_order=sort_order,
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
        error = error_unless_all_fields_provided(request.form, REQUIRED_FIELDS)
        if not error:
            card, transaction_info = process_transaction(request.form)
            # Insert the new transaction into the database
            db, cursor = get_db()
            mapping = prepare_db_transaction_mapping(TRANSACTION_FIELDS,
                                                     transaction_info,
                                                     card['id'])
            cursor.execute(
                f'INSERT INTO credit_transactions {tuple(mapping.keys())}'
                 'VALUES (?, ?, ?, ?, ?, ?, ?)',
                (*mapping.values(),)
            )
            db.commit()
            transaction_id = cursor.lastrowid
            return render_template('credit/submission.html',
                                   field_names=DISPLAY_FIELDS,
                                   card=card,
                                   transaction_id=transaction_id,
                                   transaction=transaction_info,
                                   update=False)
        else:
            flash(error)
    # Display the form for accepting user input
    return render_template('credit/new_transaction.html', form=form)

@bp.route('/_get_autocomplete_info', methods=('POST',))
@login_required
def get_autocomplete_info():
    field = request.get_json()
    if field not in DISPLAY_FIELDS.keys():
        raise ValueError(f"'{field}' is not an available autocompletion field.")
    # Get information from the database to use for autocompletion
    db, cursor = get_db()
    autocomplete_query = (f'SELECT {field}'
                           '  FROM credit_transactions AS t'
                           '  JOIN credit_cards AS c ON t.card_id = c.id'
                           ' WHERE c.user_id = ?')
    column = cursor.execute(autocomplete_query, (g.user['id'],)).fetchall()
    unique_column = {row[field] for row in column}
    return jsonify(tuple(unique_column))

@bp.route('/<int:transaction_id>/update_transaction', methods=('GET', 'POST'))
@login_required
def update_transaction(transaction_id):
    # Get the transaction information from the database
    transaction = get_transaction(transaction_id)
    # Define a form for a transaction
    form = UpdateTransactionForm(data=transaction)
    # Check if a transaction was updated and update it in the database
    if request.method == 'POST':
        error = error_unless_all_fields_provided(request.form, REQUIRED_FIELDS)
        if not error:
            card, transaction_info = process_transaction(request.form)
            # Update the database with the updated transaction
            db, cursor = get_db()
            mapping = prepare_db_transaction_mapping(TRANSACTION_FIELDS,
                                                     transaction_info,
                                                     card['id'])
            update_fields = [f'{field} = ?' for field in mapping]
            cursor.execute(
                'UPDATE credit_transactions'
               f'   SET {", ".join(update_fields)}'
                ' WHERE id = ?',
                (*mapping.values(), transaction_id)
            )
            db.commit()
            return render_template('credit/submission.html',
                                   field_names=DISPLAY_FIELDS,
                                   card=card,
                                   transaction_id=transaction_id,
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
    db, cursor = get_db()
    cursor.execute(
        'DELETE FROM credit_transactions WHERE id = ?',
        (transaction_id,)
    )
    db.commit()
    return redirect(url_for('credit.show_transactions'))
