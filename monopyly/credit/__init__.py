"""
Flask blueprint for credit card financials.
"""
from collections import Counter

from flask import (
    Blueprint, flash, g, redirect, render_template,
    request, session, url_for, jsonify
)

from ..db import get_db
from ..auth import login_required
from ..forms import *
from .constants import (
    TRANSACTION_FIELDS, REQUIRED_FIELDS, DISPLAY_FIELDS, FORM_FIELDS
)
from .cards import CardHandler
from .transactions import TransactionHandler
from .statements import StatementHandler


# Define the blueprint
bp = Blueprint('credit', __name__, url_prefix='/credit')


@bp.route('/transactions')
@login_required
def show_transactions():
    ch, th = CardHandler(), TransactionHandler()
    # Get all of the user's credit cards from the database
    cards = ch.get_cards()
    # Get all of the user's transactions for active cards from the database
    sort_order = 'DESC'
    transactions = th.get_transactions(fields=FORM_FIELDS,
                                       sort_order=sort_order,
                                       active=True)
    return render_template('credit/transactions.html',
                           cards=cards,
                           sort_order=sort_order,
                           transactions=transactions)


@bp.route('/_update_transactions_table', methods=('POST',))
@login_required
def update_transactions_table():
    ch, th = CardHandler(), TransactionHandler()
    # Separate the arguments of the POST method
    post_args = request.get_json()
    filter_ids = post_args['filter_ids']
    sort_order = 'ASC' if post_args['sort_order'] == 'asc' else 'DESC'
    # Determine the card IDs from the arguments of POST method
    card_ids = [ch.find_card(*tag.split('-'))['id'] for tag in filter_ids]
    # Filter selected transactions from the database
    transactions = th.get_transactions(fields=DISPLAY_FIELDS.keys(),
                                       card_ids=card_ids,
                                       sort_order=sort_order)
    return render_template('credit/transaction_table.html',
                           sort_order=sort_order,
                           transactions=transactions)


@bp.route('/<int:transaction_id>/transaction')
@login_required
def show_transaction(transaction_id):
    th = TransactionHandler()
    # Get the transaction information from the database
    transaction = th.get_transaction(transaction_id)
    # Match the transaction to a registered credit card
    return render_template('credit/transaction.html',
                           transaction=transaction)


@bp.route('/new_transaction', methods=('GET', 'POST'))
@login_required
def new_transaction():
    # Define a form for a transaction
    form = TransactionForm()
    # Check if a transaction was submitted and add it to the database
    if request.method == 'POST' and form.validate():
        error = error_unless_all_fields_provided(request.form, REQUIRED_FIELDS)
        if not error:
            th = TransactionHandler()
            # Insert the new transaction into the database
            transaction = th.new_transaction(request.form)
            return render_template('credit/submission.html',
                                   field_names=DISPLAY_FIELDS,
                                   transaction=transaction,
                                   update=False)
        else:
            flash(error)
    # Display the form for accepting user input
    return render_template('credit/new_transaction.html', form=form)


@bp.route('/<int:transaction_id>/update_transaction', methods=('GET', 'POST'))
@login_required
def update_transaction(transaction_id):
    th = TransactionHandler()
    # Get the transaction information from the database
    transaction = th.get_transaction(transaction_id)
    # Define a form for a transaction
    form = TransactionForm(data=transaction)
    # Check if a transaction was updated and update it in the database
    if request.method == 'POST':
        error = error_unless_all_fields_provided(request.form, REQUIRED_FIELDS)
        if not error:
            # Update the database with the updated transaction
            transaction = th.update_transaction(transaction_id, request.form)
            return render_template('credit/submission.html',
                                   field_names=DISPLAY_FIELDS,
                                   transaction=transaction,
                                   update=True)
        else:
            flash(error)
    # Display the form for accepting user input
    return render_template('credit/update_transaction.html',
                           transaction_id=transaction_id, form=form)


@bp.route('/_suggest_autocomplete', methods=('POST',))
@login_required
def suggest_autocomplete():
    th = TransactionHandler()
    # Get the autocomplete field from the AJAX request
    field = request.get_json()
    if field not in ('bank', 'last_four_digits', 'vendor', 'notes'):
        raise ValueError(f"'{field}' does not support autocompletion.")
    # Get information from the database to use for autocompletion
    db_column = th.get_transactions(fields=(field,))
    column = [row[field] for row in db_column]
    # Order the returned values by their frequency in the database
    item_counts = Counter(column)
    unique_items = set(column)
    suggestions = sorted(unique_items, key=item_counts.get, reverse=True)
    return jsonify(suggestions)


@bp.route('/_infer_card', methods=('POST',))
@login_required
def infer_card():
    ch = CardHandler()
    # Separate the arguments of the POST method
    post_args = request.get_json()
    bank = (post_args['bank'],)
    if 'digits' in post_args:
        last_four_digits = (post_args['last_four_digits'],)
        # Try to infer card from digits alone
        cards = ch.get_cards(last_four_digits=last_four_digits, active=True)
        if len(cards) != 1:
            # Infer card from digits and bank if necessary
            cards = ch.get_cards(banks=bank, last_four_digits=last_four_digits,
                                 active=True)
    elif 'bank' in post_args:
        # Try to infer card from bank alone
        cards = ch.get_cards(banks=bank, active=True)
    # Return an inferred card if a single card is identified
    if len(cards) == 1:
        # Return the card info if its is found
        card = cards[0]
        response = {'bank': card['bank'],
                    'digits': card['last_four_digits']}
        return jsonify(response)
    else:
        return ''


@bp.route('/_infer_statement', methods=('POST',))
@login_required
def infer_statement():
    return


@bp.route('/<int:transaction_id>/delete_transaction', methods=('POST',))
@login_required
def delete_transaction(transaction_id):
    th = TransactionHandler()
    # Remove the transaction from the database
    th.delete_transaction(transaction_id)
    return redirect(url_for('credit.show_transactions'))
