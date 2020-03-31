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
from ..utils import parse_date
from .forms import *
from .accounts import AccountHandler
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


@bp.route('/new_card', methods=('GET', 'POST'))
@login_required
def new_card():
    # Define a form for a credit card
    form = CardForm()
    form.account_id.choices = prepare_account_choices()
    # Check if a card was submitted and add it to the database
    if request.method == 'POST':
        if form.validate():
            ch = CardHandler()
            # Insert the new credit card into the database
            card = ch.process_card_form(form)
            return render_template('credit/card_submission_page.html',
                                   update=False)
        else:
            flash(form_err_msg)
            print(form.errors)
    return render_template('credit/card_form_page_new.html', form=form)


@bp.route('/delete_card/<int:card_id>', methods=('POST',))
@login_required
def delete_card(card_id):
    ch = CardHandler()
    # Remove the credit card from the database
    ch.delete_entries((card_id,))
    return redirect(url_for('credit.show_cards'))


@bp.route('/account/<int:account_id>')
@login_required
def show_account(account_id):
    ah, ch = AccountHandler(), CardHandler()
    # Get the account information from the database
    account = ah.get_entry(account_id)
    # Get all cards with active cards at the end of the list
    cards = ch.get_cards(accounts=(account_id,))[::-1]
    return render_template('credit/account_page.html',
                           account=account,
                           cards=cards)


@bp.route('/_update_account_statement_issue_day/<int:account_id>',
          methods=('POST',))
@login_required
def update_account_statement_issue_day(account_id):
    ah = AccountHandler()
    # Get the autocomplete field from the AJAX request
    issue_day = request.get_json()
    # Update the account in the database
    mapping = {'statement_issue_day': int(issue_day)}
    account = ah.update_entry(account_id, mapping)
    return str(account['statement_issue_day'])


@bp.route('/_update_account_statement_due_day/<int:account_id>',
          methods=('POST',))
@login_required
def update_account_statement_due_day(account_id):
    ah = AccountHandler()
    # Get the autocomplete field from the AJAX request
    due_day = request.get_json()
    # Update the account in the database
    mapping = {'statement_due_day': int(due_day)}
    account = ah.update_entry(account_id, mapping)
    return str(account['statement_due_day'])


@bp.route('/delete_account/<int:account_id>')
@login_required
def delete_account(account_id):
    flash('This functionality is not currently available.')
    return redirect(url_for('credit.show_account', account_id=account_id))


@bp.route('/statements')
@login_required
def show_statements():
    ch, sh = CardHandler(), StatementHandler()
    # Get all of the user's credit cards from the database
    all_cards = ch.get_cards()
    active_cards = ch.get_cards(active=True)
    # Get all of the user's statements for active cards from the database
    fields = ('card_id', 'issue_date', 'due_date', 'paid', 'payment_date',
              'balance')
    statements = sh.get_statements(fields=fields, active=True)
    return render_template('credit/statements_page.html',
                           filter_cards=all_cards,
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
              'balance')
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
    statement_fields = ('bank', 'last_four_digits', 'issue_date', 'due_date',
                        'paid', 'payment_date', 'balance')
    statement = sh.get_entry(statement_id, fields=statement_fields)
    # Get all of the transactions for the statement from the database
    sort_order = 'DESC'
    transaction_fields = ('transaction_date', 'vendor', 'amount')
    transactions = th.get_transactions(fields=transaction_fields,
                                       sort_order=sort_order,
                                       statement_ids=(statement['id'],))
    return render_template('credit/statement_page.html',
                           statement=statement,
                           statement_transactions=transactions)


@bp.route('/_update_statement_due_date/<int:statement_id>', methods=('POST',))
@login_required
def update_statement_due_date(statement_id):
    sh = StatementHandler()
    # Get the field from the AJAX request
    due_date = request.get_json()
    # Update the statement in the database
    mapping = {'due_date': parse_date(due_date)}
    statement = sh.update_entry(statement_id, mapping)
    return str(statement['due_date'])


@bp.route('/_update_statement_payment/<int:statement_id>', methods=('POST',))
@login_required
def update_statement_payment(statement_id):
    sh = StatementHandler()
    # Get the field from the AJAX request
    payment_date = request.get_json()
    # Update the statement in the database
    mapping = {'paid': 1, 'payment_date': parse_date(payment_date)}
    sh.update_entry(statement_id, mapping)
    # Get the statement information from the database
    fields = ('bank', 'last_four_digits', 'issue_date', 'due_date', 'paid',
              'payment_date', 'balance')
    statement = sh.get_entry(statement_id, fields=fields)
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
    transaction_fields = ('bank', 'last_four_digits', 'transaction_date',
                           'vendor', 'amount', 'notes', 'issue_date')
    transactions = th.get_transactions(fields=transaction_fields,
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
    transaction_fields = ('bank', 'last_four_digits', 'transaction_date',
                           'vendor', 'amount', 'notes', 'issue_date')
    transactions = th.get_transactions(fields=transaction_fields,
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
    transaction = th.get_entry(transaction_id)
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
        statement_fields = ('bank', 'last_four_digits', 'issue_date')
        statement = sh.get_entry(statement_id, fields=statement_fields)
        form.process(data=statement)
    # Check if a transaction was submitted and add it to the database
    if request.method == 'POST':
        if form.validate():
            th = TransactionHandler()
            # Insert the new transaction into the database
            transaction = th.new_entry(form.database_data)
            return render_template('credit/transaction_submission_page.html',
                                   transaction=transaction, update=False)
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
    transaction = th.get_entry(transaction_id)
    # Define a form for a transaction
    form = TransactionForm(data=transaction)
    # Check if a transaction was updated and update it in the database
    if request.method == 'POST':
        if form.validate():
            # Update the database with the updated transaction
            transaction = th.process_transaction_form(form, transaction_id)
            return render_template('credit/transaction_submission_page.html',
                                   transaction=transaction, update=True)
        else:
            # Show an error to the user and print the errors for the admin
            flash(form_err_msg)
            print(form.errors)
    # Display the form for accepting user input
    return render_template('credit/transaction_form_page_update.html',
                           transaction_id=transaction_id, form=form)


@bp.route('/delete_transaction/<int:transaction_id>')
@login_required
def delete_transaction(transaction_id):
    th = TransactionHandler()
    # Remove the transaction from the database
    th.delete_entries((transaction_id,))
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
                         last_four_digits=(last_four_digits,))
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


@bp.route('/_infer_bank', methods=('POST',))
@login_required
def infer_bank():
    ah = AccountHandler()
    # Separate the arguments of the POST method
    post_args = request.get_json()
    account_id = post_args['account_id']
    account = ah.get_entry(account_id)
    if not account:
        abort(404, 'An account with the given ID was not found.')
    return account['bank']


def prepare_account_choices():
    """Prepare account choices for the card form dropdown."""
    ah, ch = AccountHandler(), CardHandler()
    # Collect all available user accounts
    user_accounts = ah.get_accounts()
    choices = [(-1, '-'), (0, 'New account')]
    for account in user_accounts:
        cards = ch.get_cards(accounts=(account['id'],))
        digits = [f"*{card['last_four_digits']}" for card in cards]
        # Create a description for the account using the bank and card digits
        description = f"{account['bank']} (cards: {', '.join(digits)})"
        choices.append((account['id'], description))
    return choices
