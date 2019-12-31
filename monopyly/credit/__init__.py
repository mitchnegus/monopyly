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
from ..utils import parse_date
from .constants import DISPLAY_FIELDS
from .cards import CardHandler
from .statements import StatementHandler
from .transactions import TransactionHandler, determine_statement_date


# Define the blueprint
bp = Blueprint('credit', __name__, url_prefix='/credit')

# Define a custom form error messaage
form_err_msg = 'There was an improper value in your form. Please try again.'

@bp.route('/cards')
@login_required
def show_cards():
    ch = CardHandler()
    # Get all of the user's credit cards from the database
    cards = ch.get_cards()
    return render_template('credit/cards_page.html', cards=cards)


@bp.route('/<int:card_id>/card')
@login_required
def show_card(card_id):
    ch = CardHandler()
    # Get the credit card information from the database
    card = ch.get_card(card_id)
    return render_template('credit/card_page.html',
                           card=card)


@bp.route('/new_card', methods=('GET', 'POST'))
@login_required
def new_card():
    # Define a form for a credit card
    form = CardForm()
    # Check if a card was submitted and add it to the database
    if request.method == 'POST':
        if form.validate():
            ch = CardHandler()
            # Insert the new credit card into the database
            card = ch.save_card(form)
            return render_template('credit/card_submission_page.html',
                                   update=False)
        else:
            flash(form_err_msg)
    # Define a form for a card
    return render_template('credit/card_form_page_new.html', form=form)


@bp.route('/<int:card_id>/update_card', methods=('GET', 'POST'))
@login_required
def update_card(card_id):
    ch = CardHandler()
    # Get the credit card information from the database
    card = ch.get_card(card_id)
    # Define a form for a card
    form = CardForm(data=card)
    # Check if a card was updated and update it in the database
    if request.method == 'POST':
        if form.validate():
            # Update the database with the updated credit card
            card = ch.save_card(form, card_id)
            return render_template('credit/card_submission_page.html',
                                   update=True)
        else:
            flash(form_err_msg)
    # Display the form for accepting user input
    return render_template('credit/card_form_page_update.html',
                           card_id=card_id, form=form)


@bp.route('/<int:card_id>/delete_card', methods=('POST',))
@login_required
def delete_card(card_id):
    ch = CardHandler()
    # Remove the credit card from the database
    ch.delete_card(card_id)
    return redirect(url_for('credit.show_cards'))


@bp.route('/statements')
@login_required
def show_statements():
    sh = StatementHandler()
    # Get all of the user's statements from the database
    statements = sh.get_statements()
    # Get all of the user's statements for active cards from the database
    fields = ('bank', 'last_four_digits', 'issue_date', 'due_date', 'paid',
              'SUM(price)')
    statements = sh.get_statements(fields=fields, active=True)
    return render_template('credit/statements_page.html',
                           statements=statements)


@bp.route('/transactions')
@login_required
def show_transactions():
    ch, th = CardHandler(), TransactionHandler()
    # Get all of the user's credit cards from the database
    cards = ch.get_cards()
    # Get all of the user's transactions for active cards from the database
    sort_order = 'DESC'
    transactions = th.get_transactions(fields=DISPLAY_FIELDS.keys(),
                                       sort_order=sort_order,
                                       active=True)
    return render_template('credit/transactions_page.html',
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
    return render_template('credit/transactions_table.html',
                           sort_order=sort_order,
                           transactions=transactions)


@bp.route('/<int:transaction_id>/transaction')
@login_required
def show_transaction(transaction_id):
    th = TransactionHandler()
    # Get the transaction information from the database
    transaction = th.get_transaction(transaction_id)
    return render_template('credit/transaction_page.html',
                           transaction=transaction)


@bp.route('/new_transaction', methods=('GET', 'POST'))
@login_required
def new_transaction():
    # Define a form for a transaction
    form = TransactionForm()
    # Check if a transaction was submitted and add it to the database
    if request.method == 'POST':
        if form.validate():
            th = TransactionHandler()
            # Insert the new transaction into the database
            transaction = th.save_transaction(form)
            return render_template('credit/transaction_submission_page.html',
                                   field_names=DISPLAY_FIELDS,
                                   transaction=transaction,
                                   update=False)
        else:
            flash(form_err_msg)
    # Display the form for accepting user input
    return render_template('credit/transaction_form_page_new.html', form=form)


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
        if form.validate():
            # Update the database with the updated transaction
            transaction = th.save_transaction(form, transaction_id)
            return render_template('credit/transaction_submission_page.html',
                                   field_names=DISPLAY_FIELDS,
                                   transaction=transaction,
                                   update=True)
        else:
            flash(form_err_msg)
    # Display the form for accepting user input
    return render_template('credit/transaction_form_page_update.html',
                           transaction_id=transaction_id, form=form)


@bp.route('/<int:transaction_id>/delete_transaction', methods=('POST',))
@login_required
def delete_transaction(transaction_id):
    th = TransactionHandler()
    # Remove the transaction from the database
    th.delete_transaction(transaction_id)
    return redirect(url_for('credit.show_transactions'))


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
        last_four_digits = (post_args['digits'],)
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
    ch, sh = CardHandler(), StatementHandler()
    # Separate the arguments of the POST method
    post_args = request.get_json()
    bank = (post_args['bank'],)
    last_four_digits = (post_args['digits'],)
    transaction_date = parse_date(post_args['transaction_date'])
    # Determine the card used for the transaction from the given info
    cards = ch.get_cards(banks=bank, last_four_digits=last_four_digits,
                         active=True)
    if len(cards) == 1:
        # Determine the statement corresponding to the card and date
        card = cards[0]
        statement_date = determine_statement_date(card, transaction_date)
        statement = sh.find_statement(card['id'], issue_date=statement_date)
        return statement['issue_date']
    return ''
