"""
Flask blueprint for credit card financials.
"""
from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for
)

from ..db import get_db
from ..auth import login_required
from ..forms import *
from .constants import TRANSACTION_FIELDS, REQUIRED_FIELDS, DISPLAY_FIELDS
from .tools import *

# Define the blueprint
bp = Blueprint('credit', __name__, url_prefix='/credit')

@bp.route('/transactions')
@login_required
def show_transactions():
    # Get all transactions from the database
    db = get_db()
    cards_query = ('SELECT c.id, bank, last_four_digits, active'
                   '  FROM credit_cards as c'
                   '  JOIN users AS u ON c.user_id = u.id'
                   ' WHERE u.id = ?'
                   ' ORDER BY active')
    cards = db.execute(cards_query, (g.user['id'],)).fetchall()
    query_fields = list(DISPLAY_FIELDS.keys())
    transactions_query = (f'SELECT t.id, {", ".join(query_fields)}'
                           '  FROM credit_transactions AS t'
                           '  JOIN credit_cards AS c ON t.card_id = c.id'
                           '  JOIN users AS u ON t.user_id = u.id'
                           ' WHERE u.id = ? AND c.active = 1'
                           ' ORDER BY transaction_date')
    placeholders = (g.user['id'],)
    transactions = db.execute(transactions_query, placeholders).fetchall()
    return render_template('credit/transactions.html',
                           cards=cards,
                           transactions=transactions)

@bp.route('/_filter_transactions', methods=('POST',))
@login_required
def filter_transactions():
    # *** Route should not be accessible to users outside of Ajax requests ***
    # Determine the card IDs from the arguments of GET method
    filter_ids = request.get_json()
    card_ids = get_card_ids_from_filter_ids(filter_ids)
    # Filter selected transactions from the database
    db = get_db()
    query_fields = list(DISPLAY_FIELDS.keys())
    if card_ids:
        card_id_fields = ['c.id = ?']*len(card_ids)
    else:
        card_id_fields = ['c.id = ""']
    filter_query = (f'SELECT t.id, {", ".join(query_fields)}'
                     '  FROM credit_transactions AS t'
                     '  JOIN credit_cards AS c ON t.card_id = c.id'
                     '  JOIN users AS u ON t.user_id = u.id'
                    f' WHERE u.id = ? AND ({" OR ".join(card_id_fields)})'
                     ' ORDER BY transaction_date')
    placeholders = (g.user['id'], *card_ids)
    transactions = db.execute(filter_query, placeholders).fetchall()
    print('there are', len(transactions), 'transactions')

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
            db = get_db()
            mapping = prepare_db_transaction_mapping(TRANSACTION_FIELDS,
                                                     transaction_info,
                                                     card['id'])
            print(mapping.values())
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
        error = error_unless_all_fields_provided(request.form, REQUIRED_FIELDS)
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
