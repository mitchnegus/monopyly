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
    TRANSACTION_FIELDS, REQUIRED_FIELDS, DISPLAY_FIELDS, FORM_FIELDS
)
from .cards import CardHandler
from .transactions import TransactionHandler, process_transaction
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
    post_arguments = request.get_json()
    filter_ids = post_arguments['filter_ids']
    sort_order = 'ASC' if post_arguments['sort_order'] == 'asc' else 'DESC'
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
    # Get the transaction information from the database
    th = TransactionHandler()
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
            # Insert the new transaction into the database
            th = TransactionHandler()
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
    # Get the transaction information from the database
    th = TransactionHandler()
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


@bp.route('/<int:transaction_id>/delete_transaction', methods=('POST',))
@login_required
def delete_transaction(transaction_id):
    # Remove the transaction from the database
    th = TransactionHandler()
    th.delete_transaction(transaction_id)
    return redirect(url_for('credit.show_transactions'))
