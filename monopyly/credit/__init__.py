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
    TRANSACTION_FIELDS, REQUIRED_FIELDS, DISPLAY_FIELDS
)
from .cards import CardHandler
from .transactions import (
    TransactionHandler, process_transaction, prepare_db_transaction_mapping
)


# Define the blueprint
bp = Blueprint('credit', __name__, url_prefix='/credit')

@bp.route('/transactions')
@login_required
def show_transactions():
    ch, th = CardHandler(), TransactionHandler()
    # Get all of the user's credit cards from the database
    cards = ch.get_cards()
    active_cards = ch.get_cards(active=True)
    # Get all of the user's transactions from the database
    fields = ['t.id'] + list(DISPLAY_FIELDS.keys())
    card_ids = [card['id'] for card in active_cards]
    sort_order = 'DESC'
    transactions = th.get_transactions(fields=fields, card_ids=card_ids,
                                       sort_order=sort_order)
    return render_template('credit/transactions.html',
                           cards=cards,
                           sort_order=sort_order,
                           transactions=transactions)

@bp.route('/_update_transactions_table', methods=('POST',))
@login_required
def update_transactions_table():
    # Separate the arguments of the POST method
    post_arguments = request.get_json()
    filter_ids = post_arguments['filter_ids']
    sort_order = 'ASC' if post_arguments['sort_order'] == 'asc' else 'DESC'
    # Determine the card IDs from the arguments of POST method
    ch = CardHandler()
    card_ids = [ch.find_card(*tag.split('-'))['id'] for tag in filter_ids]
    # Filter selected transactions from the database
    th = TransactionHandler()
    fields = ['t.id'] + list(DISPLAY_FIELDS.keys())
    transactions = th.get_transactions(fields=fields, card_ids=card_ids,
                                       sort_order=sort_order)
    return render_template('credit/transaction_table.html',
                           sort_order=sort_order,
                           transactions=transactions)

@bp.route('/<int:transaction_id>/transaction')
@login_required
def show_transaction(transaction_id):
    ch, th = CardHandler(), TransactionHandler()
    # Get the transaction information from the database
    transaction = th.get_transaction(transaction_id)
    # Match the transaction to a registered credit card
    card = ch.get_card(transaction['card_id'])
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
            mapping = prepare_db_transaction_mapping(TRANSACTION_FIELDS,
                                                     transaction_info,
                                                     card['id'])
            th = TransactionHandler()
            transaction_id = th.new_transaction(mapping)
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
    db = get_db()
    cursor = db.cursor()
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
    th = TransactionHandler()
    transaction = th.get_transaction(transaction_id)
    # Define a form for a transaction
    form = TransactionForm(data=transaction)
    # Check if a transaction was updated and update it in the database
    if request.method == 'POST':
        error = error_unless_all_fields_provided(request.form, REQUIRED_FIELDS)
        if not error:
            card, transaction_info = process_transaction(request.form)
            # Update the database with the updated transaction
            db = get_db()
            cursor = db.cursor()
            mapping = prepare_db_transaction_mapping(TRANSACTION_FIELDS,
                                                     transaction_info,
                                                     card['id'])
            update_fields = [f'{field} = ?' for field in mapping]
            cursor.execute(
                'UPDATE credit_transactions'
               f'   SET {", ".join(update_fields)}'
                ' WHERE id = ? AND ',
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
    th = TransactionHandler()
    th.get_transaction(transaction_id)
    # Remove the transaction from the database
    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        'DELETE FROM credit_transactions WHERE id = ?',
        (transaction_id,)
    )
    db.commit()
    return redirect(url_for('credit.show_transactions'))
