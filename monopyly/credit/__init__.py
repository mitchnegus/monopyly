"""
Flask blueprint for credit card financials.
"""
from collections import Counter

from werkzeug.exceptions import abort
from flask import (
    Blueprint, redirect, render_template,
    flash, request, url_for, jsonify
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


@bp.route('/card/<int:card_id>')
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
            print(form.errors)
    return render_template('credit/card_form_page_new.html', form=form)


@bp.route('/update_card/<int:card_id>', methods=('GET', 'POST'))
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
            print(form.errors)
    # Display the form for accepting user input
    return render_template('credit/card_form_page_update.html',
                           card_id=card_id, form=form)


@bp.route('/delete_card/<int:card_id>', methods=('POST',))
@login_required
def delete_card(card_id):
    ch = CardHandler()
    # Remove the credit card from the database
    ch.delete_card(card_id)
    return redirect(url_for('credit.show_cards'))


@bp.route('/statements')
@login_required
def show_statements():
    ch, sh = CardHandler(), StatementHandler()
    # Get all of the user's credit cards from the database
    cards = ch.get_cards()
    active_cards = ch.get_cards(active=True)
    # Get all of the user's statements for active cards from the database
    fields = ('card_id', 'issue_date', 'due_date', 'paid', 'payment_date',
              'COALESCE(SUM(price), 0) total')
    statements = sh.get_statements(fields=fields, active=True)
    return render_template('credit/statements_page.html',
                           filter_cards=cards,
                           selected_cards=active_cards,
                           statements=statements)


@bp.route('/_update_statements_display', methods=('POST',))
@login_required
def update_statements_display():
    ch, sh = CardHandler(), StatementHandler()
    # Separate the arguments of the POST method
    post_args = request.get_json()
    filter_ids = post_args['filter_ids']
    # Determine the card IDs from the arguments of POST method
    cards = [ch.find_card(*tag.split('-')) for tag in filter_ids]
    # Filter selected statements from the database
    fields = ('card_id', 'issue_date', 'due_date', 'paid', 'payment_date',
              'COALESCE(SUM(price), 0) total')
    statements = sh.get_statements(fields=fields,
                                   card_ids=[card['id'] for card in cards])
    return render_template('credit/statements.html',
                           selected_cards=cards,
                           statements=statements)


@bp.route('/statement/<int:statement_id>')
@login_required
def show_statement(statement_id):
    sh, th = StatementHandler(), TransactionHandler()
    # Get the statement information from the database
    fields = ('bank', 'last_four_digits', 'issue_date', 'due_date', 'paid',
              'payment_date', 'COALESCE(SUM(price), 0) total')
    statement = sh.get_statement(statement_id, fields=fields)
    # Get all of the transactions for the statement from the database
    sort_order = 'DESC'
    transactions = th.get_transactions(fields=DISPLAY_FIELDS.keys(),
                                       sort_order=sort_order,
                                       statement_ids=(statement['id'],))
    return render_template('credit/statement_page.html',
                           statement=statement,
                           statement_transactions=transactions)


@bp.route('/_update_statement_due_date/<int:statement_id>', methods=('POST',))
@login_required
def update_statement_due_date(statement_id):
    sh = StatementHandler()
    # Get the autocomplete field from the AJAX request
    new_due_date = request.get_json()
    # Update the statement in the database
    sh.update_statement_due_date(statement_id, new_due_date)
    statement = sh.get_statement(statement_id, fields=('due_date',))
    return str(statement['due_date'])


@bp.route('/_update_statement_payment/<int:statement_id>', methods=('POST',))
@login_required
def update_statement_payment(statement_id):
    sh = StatementHandler()
    # Get the autocomplete field from the AJAX request
    payment_date = request.get_json()
    # Update the statement in the database
    sh.update_statement_payment(statement_id, payment_date)
    # Get the statement information from the database
    fields = ('bank', 'last_four_digits', 'issue_date', 'due_date', 'paid',
              'payment_date', 'COALESCE(SUM(price), 0) total')
    statement = sh.get_statement(statement_id, fields=fields)
    return render_template('credit/statement_info.html',
                           statement=statement)


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
                           filter_cards=cards,
                           sort_order=sort_order,
                           transactions=transactions)


@bp.route('/_update_transactions_display', methods=('POST',))
@login_required
def update_transactions_display():
    ch, th = CardHandler(), TransactionHandler()
    # Separate the arguments of the POST method
    post_args = request.get_json()
    filter_ids = post_args['filter_ids']
    sort_order = 'ASC' if post_args['sort_order'] == 'asc' else 'DESC'
    # Determine the card IDs from the arguments of POST method
    cards = [ch.find_card(*tag.split('-')) for tag in filter_ids]
    # Filter selected transactions from the database
    transactions = th.get_transactions(fields=DISPLAY_FIELDS.keys(),
                                       card_ids=[card['id'] for card in cards],
                                       sort_order=sort_order)
    return render_template('credit/transactions.html',
                           sort_order=sort_order,
                           transactions=transactions)


@bp.route('/transaction/<int:transaction_id>')
@login_required
def show_transaction(transaction_id):
    th = TransactionHandler()
    # Get the transaction information from the database
    transaction = th.get_transaction(transaction_id)
    return render_template('credit/transaction_page.html',
                           transaction=transaction)


@bp.route('/new_transaction', defaults={'statement_id': None},
          methods=('GET', 'POST'))
@bp.route('/new_transaction/<int:statement_id>', methods=('GET', 'POST'))
@login_required
def new_transaction(statement_id):
    # Define a form for a transaction
    form = TransactionForm()
    # Load statement parameters if the request came from a specific statement
    if statement_id:
        sh = StatementHandler()
        # Get the necessary fields from the database
        fields = ('bank', 'last_four_digits', 'issue_date')
        statement = sh.get_statement(statement_id, fields=fields)
        form.bank.data = statement['bank']
        form.last_four_digits.data = statement['last_four_digits']
        form.issue_date.data = statement['issue_date']
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
            # Show an error to the user and print the errors for the admin
            flash(form_err_msg)
            print(form.errors)
    # Display the form for accepting user input
    return render_template('credit/transaction_form_page_new.html', form=form)


@bp.route('/update_transaction/<int:transaction_id>', methods=('GET', 'POST'))
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
            # Show an error to the user and print the errors for the admin
            flash(form_err_msg)
            print(form.errors)
    # Display the form for accepting user input
    return render_template('credit/transaction_form_page_update.html',
                           transaction_id=transaction_id, form=form)


@bp.route('/delete_transaction/<int:transaction_id>', methods=('POST',))
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
    post_args = request.get_json()
    field = post_args['field']
    vendor = post_args['vendor']
    if field not in ('bank', 'last_four_digits', 'vendor', 'notes'):
        raise ValueError(f"'{field}' does not support autocompletion.")
    # Get information from the database to use for autocompletion
    if field != 'notes':
        transactions = th.get_transactions(fields=(field,))
    else:
        transactions = th.get_transactions(fields=('vendor', 'notes'))
        # Generate a map of notes for the current vendor
        note_by_vendor = {}
        for transaction in transactions:
            note = transaction['notes']
            if not note_by_vendor.get(note):
                note_by_vendor[note] = (transaction['vendor'] == vendor)
    items = [row[field] for row in transactions]
    # Order the returned values by their frequency in the database
    item_counts = Counter(items)
    unique_items = set(items)
    suggestions = sorted(unique_items, key=item_counts.get, reverse=True)
    # Also sort note fields by vendor
    if field == 'notes':
        suggestions.sort(key=note_by_vendor.get, reverse=True)
    return jsonify(suggestions)


@bp.route('/_infer_card', methods=('POST',))
@login_required
def infer_card():
    ch = CardHandler()
    # Separate the arguments of the POST method
    post_args = request.get_json()
    bank = post_args['bank']
    if 'digits' in post_args:
        last_four_digits = post_args['digits']
        # Try to infer card from digits alone
        cards = ch.get_cards(last_four_digits=(last_four_digits,), active=True)
        if len(cards) != 1:
            # Infer card from digits and bank if necessary
            cards = ch.get_cards(banks=(bank,),
                                 last_four_digits=(last_four_digits,),
                                 active=True)
    elif 'bank' in post_args:
        # Try to infer card from bank alone
        cards = ch.get_cards(banks=(bank,), active=True)
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
    bank = post_args['bank']
    last_four_digits = post_args['digits']
    transaction_date = parse_date(post_args['transaction_date'])
    # Determine the card used for the transaction from the given info
    cards = ch.get_cards(banks=(bank,),
                         last_four_digits=(last_four_digits,),
                         active=True)
    if len(cards) == 1:
        # Determine the statement corresponding to the card and date
        card = cards[0]
        statement_date = determine_statement_date(card['statement_issue_day'],
                                                  transaction_date)
        statement = sh.find_statement(card['id'], issue_date=statement_date)
        # Check that a statement was found and that it belongs to the user
        if not statement:
            abort(404, 'A statement matching the criteria was not found.')
        return str(statement['issue_date'])
    else:
        return ''
