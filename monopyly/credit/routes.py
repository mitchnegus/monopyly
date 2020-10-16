"""
Routes for credit card financials.
"""
from collections import Counter

from flask import (
    g, redirect, render_template, flash, request, url_for, jsonify
)
from werkzeug.exceptions import abort

from ..db import get_db
from ..utils import parse_date, dedelimit_float
from ..auth.tools import login_required
from . import credit
from .forms import *
from .accounts import AccountHandler
from .cards import CardHandler
from .statements import (
    StatementHandler, determine_statement_issue_date,
    determine_statement_issue_date
)
from .transactions import TransactionHandler, SubtransactionHandler, TagHandler


# Define a custom form error messaage
form_err_msg = 'There was an improper value in your form. Please try again.'


@credit.route('/cards')
@login_required
def load_cards():
    card_db = CardHandler()
    # Get all of the user's credit cards from the database
    cards = card_db.get_entries()
    return render_template('credit/cards_page.html', cards=cards)


@credit.route('/add_card', methods=('GET', 'POST'))
@login_required
def add_card():
    # Define a form for a credit card
    form = CardForm()
    form.account_id.choices = prepare_account_choices()
    # Check if a card was submitted and add it to the database
    if request.method == 'POST':
        if form.validate():
            card_db = CardHandler()
            # Insert the new credit card into the database
            card = card_db.add_entry(form.card_data)
            return redirect(url_for('credit.load_account',
                                    account_id=card['account_id']))
        else:
            flash(form_err_msg)
            print(form.errors)
    return render_template('credit/card_form_page_new.html', form=form)


@credit.route('/account/<int:account_id>')
@login_required
def load_account(account_id):
    account_db, card_db = AccountHandler(), CardHandler()
    # Get the account information from the database
    account = account_db.get_entry(account_id)
    # Get all cards with active cards at the end of the list
    cards = card_db.get_entries(account_ids=(account_id,))[::-1]
    return render_template('credit/account_page.html',
                           account=account,
                           cards=cards)


@credit.route('/_update_card_status', methods=('POST',))
@login_required
def update_card_status():
    card_db = CardHandler()
    # Get the field from the AJAX request
    post_args = request.get_json()
    input_id = post_args['input_id']
    active = post_args['active']
    # Get the card ID as the second component of the input's ID attribute
    card_id = input_id.split('-')[1]
    # Update the card in the database
    mapping = {'active': int(active)}
    card = card_db.update_entry(card_id, mapping)
    return render_template('credit/card_front.html',
                           card=card)


@credit.route('/delete_card/<int:card_id>')
@login_required
def delete_card(card_id):
    card_db = CardHandler()
    account_id = card_db.get_entry(card_id)['account_id']
    # Remove the credit card from the database
    card_db.delete_entries((card_id,))
    return redirect(url_for('credit.load_account', account_id=account_id))


@credit.route('/_update_account_statement_issue_day/<int:account_id>',
          methods=('POST',))
@login_required
def update_account_statement_issue_day(account_id):
    account_db = AccountHandler()
    # Get the field from the AJAX request
    issue_day = request.get_json()
    # Update the account in the database
    mapping = {'statement_issue_day': int(issue_day)}
    account = account_db.update_entry(account_id, mapping)
    return str(account['statement_issue_day'])


@credit.route('/_update_account_statement_due_day/<int:account_id>',
          methods=('POST',))
@login_required
def update_account_statement_due_day(account_id):
    account_db = AccountHandler()
    # Get the field from the AJAX request
    due_day = request.get_json()
    # Update the account in the database
    mapping = {'statement_due_day': int(due_day)}
    account = account_db.update_entry(account_id, mapping)
    return str(account['statement_due_day'])


@credit.route('/delete_account/<int:account_id>')
@login_required
def delete_account(account_id):
    account_db = AccountHandler()
    # Remove the account from the database
    account_db.delete_entries((account_id,))
    return redirect(url_for('credit.load_cards'))


@credit.route('/statements')
@login_required
def load_statements():
    card_db, statement_db = CardHandler(), StatementHandler()
    # Get all of the user's credit cards from the database
    all_cards = card_db.get_entries()
    active_cards = card_db.get_entries(active=True)
    # Get all of the user's statements for active cards from the database
    fields = ('card_id', 'issue_date', 'due_date', 'balance', 'payment_date')
    statements = statement_db.get_entries(active=True, fields=fields)
    return render_template('credit/statements_page.html',
                           filter_cards=all_cards,
                           selected_cards=active_cards,
                           statements=statements)


@credit.route('/_update_statements_display', methods=('POST',))
@login_required
def update_statements_display():
    card_db, statement_db = CardHandler(), StatementHandler()
    # Separate the arguments of the POST method
    post_args = request.get_json()
    filter_ids = post_args['filter_ids']
    # Determine the card IDs from the arguments of POST method
    cards = [card_db.find_card(*tag.split('-')) for tag in filter_ids]
    # Filter selected statements from the database
    fields = ('card_id', 'issue_date', 'due_date', 'balance', 'payment_date')
    statements = statement_db.get_entries([card['id'] for card in cards],
                                          fields=fields)
    return render_template('credit/statements.html',
                           selected_cards=cards,
                           statements=statements)


@credit.route('/statement/<int:statement_id>')
@login_required
def load_statement(statement_id):
    statement_db = StatementHandler()
    transaction_db = TransactionHandler()
    tag_db = TagHandler()
    # Get the statement information from the database
    statement_fields = ('account_id', 'card_id', 'bank', 'last_four_digits',
                        'issue_date', 'due_date', 'balance', 'payment_date')
    statement = statement_db.get_entry(statement_id, fields=statement_fields)
    # Get all of the transactions for the statement from the database
    sort_order = 'DESC'
    transaction_fields = ('transaction_date', 'vendor', 'total', 'notes')
    transactions = transaction_db.get_entries(statement_ids=(statement['id'],),
                                              sort_order=sort_order,
                                              fields=transaction_fields)
    tag_totals = tag_db.get_totals(statement_ids=(statement['id'],))
    tag_totals = {row['tag_name']: row['total'] for row in tag_totals}
    tag_avgs = tag_db.get_statement_average_totals()
    tag_avgs = {row['tag_name']: row['average_total'] for row in tag_avgs}
    return render_template('credit/statement_page.html',
                           statement=statement,
                           statement_transactions=transactions,
                           tag_totals=tag_totals,
                           tag_average_totals=tag_avgs)


@credit.route('/_update_statement_due_date/<int:statement_id>',
              methods=('POST',))
@login_required
def update_statement_due_date(statement_id):
    statement_db = StatementHandler()
    # Get the field from the AJAX request
    due_date = request.get_json()
    # Update the statement in the database
    mapping = {'due_date': parse_date(due_date)}
    statement = statement_db.update_entry(statement_id, mapping)
    return str(statement['due_date'])


@credit.route('/_make_payment/<int:card_id>/<int:statement_id>',
              methods=('POST',))
@login_required
def make_payment(card_id, statement_id):
    card_db = CardHandler()
    statement_db = StatementHandler()
    transaction_db = TransactionHandler()
    # Get the field from the AJAX request
    post_args = request.get_json()
    payment_amount = dedelimit_float(post_args['payment_amount'])
    payment_date = parse_date(post_args['payment_date'])
    # Add the paymnet as a transaction in the database
    card = card_db.get_entry(card_id)
    statement = statement_db.infer_statement(card, payment_date, creation=True)
    mapping = {
        'statement_id': statement['id'],
        'transaction_date': payment_date,
        'vendor': card['bank'],
        'subtransactions': [{
            'subtotal': -payment_amount,
            'note': 'Card payment',
            'tags': ['Payments'],
        }],
    }
    transaction_db.add_entry(mapping)
    # Get the statement information from the database
    fields = ('card_id', 'bank', 'last_four_digits', 'issue_date',
              'due_date', 'balance', 'payment_date')
    statement = statement_db.get_entry(statement_id, fields=fields)
    return render_template('credit/statement_info.html',
                           statement=statement)


@credit.route('/transactions')
@login_required
def load_transactions():
    card_db, transaction_db = CardHandler(), TransactionHandler()
    # Get all of the user's credit cards from the database
    cards = card_db.get_entries()
    # Get all of the user's transactions for active cards from the database
    sort_order = 'DESC'
    transaction_fields = ('account_id', 'bank', 'last_four_digits',
                          'transaction_date', 'vendor', 'total', 'notes',
                          'statement_id', 'issue_date')
    transactions = transaction_db.get_entries(active=True,
                                              sort_order=sort_order,
                                              fields=transaction_fields)
    return render_template('credit/transactions_page.html',
                           filter_cards=cards,
                           sort_order=sort_order,
                           transactions=transactions)


@credit.route('/_expand_transaction', methods=('POST',))
@login_required
def expand_transaction():
    subtransaction_db, tag_db = SubtransactionHandler(), TagHandler()
    # Get the transaction ID from the AJAX request
    transaction_id = request.get_json().split('-')[-1]
    # Get the subtransactions
    subtransactions = []
    for subtransaction in subtransaction_db.get_entries((transaction_id,)):
        # Collect the subtransaction information and pair it with matching tags 
        tags = tag_db.get_entries(subtransaction_ids=(subtransaction['id'],),
                                  fields=('tag_name',))
        tag_names = [tag['tag_name'] for tag in tags]
        subtransactions.append({**subtransaction, 'tags': tag_names})
    return render_template('credit/transactions_table/subtransactions.html',
                           subtransactions=subtransactions)


@credit.route('/_update_transactions_display', methods=('POST',))
@login_required
def update_transactions_display():
    card_db, transaction_db = CardHandler(), TransactionHandler()
    # Separate the arguments of the POST method
    post_args = request.get_json()
    filter_ids = post_args['filter_ids']
    sort_order = 'ASC' if post_args['sort_order'] == 'asc' else 'DESC'
    # Determine the card IDs from the arguments of POST method
    cards = [card_db.find_card(*tag.split('-')) for tag in filter_ids]
    # Filter selected transactions from the database
    transaction_fields = ('account_id', 'bank', 'last_four_digits',
                          'transaction_date', 'vendor', 'total', 'notes',
                          'statement_id', 'issue_date')
    transactions = transaction_db.get_entries([card['id'] for card in cards],
                                              sort_order=sort_order,
                                              fields=transaction_fields)
    return render_template('credit/transactions_table/transactions.html',
                           sort_order=sort_order,
                           transactions=transactions)


@credit.route('/add_transaction', defaults={'statement_id': None},
          methods=('GET', 'POST'))
@credit.route('/add_transaction/<int:statement_id>', methods=('GET', 'POST'))
@login_required
def add_transaction(statement_id):
    # Define a form for a transaction
    form = TransactionForm()
    # Load statement parameters if the request came from a specific statement
    if statement_id:
        statement_db = StatementHandler()
        # Get the necessary fields from the database
        statement_fields = ('bank', 'last_four_digits', 'issue_date')
        statement = statement_db.get_entry(statement_id,
                                           fields=statement_fields)
        form.process(data=statement)
    # Check if a transaction was submitted and add it to the database
    if request.method == 'POST':
        if form.validate():
            transaction_db = TransactionHandler()
            # Insert the new transaction into the database
            transaction_data = form.transaction_data
            entry = transaction_db.add_entry(transaction_data)
            transaction, subtransactions = entry
            return render_template('credit/transaction_submission_page.html',
                                   transaction=transaction,
                                   subtransactions=subtransactions,
                                   update=False)
        else:
            # Show an error to the user and print the errors for the admin
            flash(form_err_msg)
            print(form.errors)
    # Display the form for accepting user input
    return render_template('credit/transaction_form/'
                           'transaction_form_page_new.html', form=form)


@credit.route('/update_transaction/<int:transaction_id>',
              methods=('GET', 'POST'))
@login_required
def update_transaction(transaction_id):
    transaction_db = TransactionHandler()
    subtransaction_db = SubtransactionHandler()
    tag_db = TagHandler()
    # Get the transaction information from the database
    transaction = transaction_db.get_entry(transaction_id)
    subtransactions = subtransaction_db.get_entries((transaction_id,))
    subtransactions_data = []
    for subtransaction in subtransactions:
        tags = tag_db.get_entries(subtransaction_ids=(subtransaction['id'],),
                                  fields=('tag_name',), ancestors=False)
        tag_list = ', '.join([tag['tag_name'] for tag in tags])
        subtransaction_data = {**subtransaction}
        subtransaction_data['tags'] = tag_list
        subtransactions_data.append(subtransaction_data)
    form_data = {**transaction, 'subtransactions': subtransactions_data}
    # Define a form for a transaction
    form = TransactionForm(data=form_data)
    # Check if a transaction was updated and update it in the database
    if request.method == 'POST':
        if form.validate():
            # Update the database with the updated transaction
            transaction_data = form.transaction_data
            entry = transaction_db.update_entry(transaction_id,
                                                transaction_data)
            transaction, subtransactions = entry
            return render_template('credit/transaction_submission_page.html',
                                   transaction=transaction,
                                   subtransactions=subtransactions,
                                   update=True)
        else:
            # Show an error to the user and print the errors for the admin
            flash(form_err_msg)
            print(form.errors)
    # Display the form for accepting user input
    return render_template('credit/transaction_form/'
                           'transaction_form_page_update.html',
                           transaction_id=transaction_id, form=form)

@credit.route('/_add_subtransaction_field', methods=('POST',))
@login_required
def add_subtransaction_field():
    post_args = request.get_json()
    new_index = post_args['subtransaction_count'] + 1
    # Redefine the form for the transaction (including using entered info)
    form_id = f'subtransactions-{new_index}'
    sub_form = TransactionForm.SubtransactionForm(prefix=form_id)
    sub_form.id = form_id
    return render_template('credit/transaction_form/subtransaction_form.html',
                           sub_form=sub_form)

@credit.route('/delete_transaction/<int:transaction_id>')
@login_required
def delete_transaction(transaction_id):
    transaction_db = TransactionHandler()
    # Remove the transaction from the database
    transaction_db.delete_entries((transaction_id,))
    return redirect(url_for('credit.load_transactions'))


@credit.route('/tags')
@login_required
def load_tags():
    tag_db = TagHandler()
    # Get the tag heirarchy from the database
    heirarchy = tag_db.get_heirarchy()
    return render_template('credit/tags_page.html',
                           tags_heirarchy=heirarchy)

@credit.route('/_add_tag', methods=('POST',))
@login_required
def add_tag():
    tag_db = TagHandler()
    # Get the new tag (and potentially parent category) from the AJAX request
    post_args = request.get_json()
    tag_name = post_args['tag_name']
    parent_name = post_args.get('parent')
    # Check that the tag name does not already exist
    if tag_db.get_entries(tag_names=(tag_name,)):
        raise ValueError('The given tag name already exists. Tag names must '
                         'be unique.')
    if parent_name:
        parent_id = tag_db.find_tag(parent_name, fields=())['id']
    else:
        parent_id = None
    tag_data = {'parent_id': parent_id,
                'user_id': g.user['id'],
                'tag_name': tag_name}
    tag = tag_db.add_entry(tag_data)
    return render_template('credit/subtag_tree.html',
                           tag=tag,
                           tags_heirarchy={})


@credit.route('/_delete_tag/', methods=('POST',))
@login_required
def delete_tag():
    tag_db = TagHandler()
    # Get the tag to be deleted from the AJAX request
    post_args = request.get_json()
    tag_name = post_args['tag_name']
    tag = tag_db.find_tag(tag_name)
    # Remove the tag from the database
    tag_db.delete_entries((tag['id'],))
    return ''


@credit.route('/_suggest_autocomplete', methods=('POST',))
@login_required
def suggest_autocomplete():
    # Get the autocomplete field from the AJAX request
    post_args = request.get_json()
    field = post_args['field']
    vendor = post_args['vendor']
    if field not in ('bank', 'last_four_digits', 'vendor', 'note'):
        raise ValueError(f"'{field}' does not support autocompletion.")
    # Get information from the database to use for autocompletion
    if field != 'note':
        transaction_db = TransactionHandler()
        entries = transaction_db.get_entries(fields=(field,))
    else:
        subtransaction_db = SubtransactionHandler()
        fields = ('vendor', 'note')
        entries = subtransaction_db.get_entries(fields=fields)
        # Generate a map of notes for the current vendor
        note_by_vendor = {}
        for entry in entries:
            note = entry['note']
            if not note_by_vendor.get(note):
                note_by_vendor[note] = (entry['vendor'] == vendor)
    items = [entry[field] for entry in entries]
    # Order the returned values by their frequency in the database
    item_counts = Counter(items)
    unique_items = set(items)
    suggestions = sorted(unique_items, key=item_counts.get, reverse=True)
    # Also sort note fields by vendor
    if field == 'note':
        suggestions.sort(key=note_by_vendor.get, reverse=True)
    return jsonify(suggestions)


@credit.route('/_infer_card', methods=('POST',))
@login_required
def infer_card():
    card_db = CardHandler()
    # Separate the arguments of the POST method
    post_args = request.get_json()
    bank = post_args['bank']
    if 'digits' in post_args:
        last_four_digits = post_args['digits']
        # Try to infer card from digits alone
        cards = card_db.get_entries(last_four_digits=(last_four_digits,),
                               active=True)
        if len(cards) != 1:
            # Infer card from digits and bank if necessary
            cards = card_db.get_entries(banks=(bank,),
                                        last_four_digits=(last_four_digits,),
                                        active=True)
    elif 'bank' in post_args:
        # Try to infer card from bank alone
        cards = card_db.get_entries(banks=(bank,), active=True)
    # Return an inferred card if a single card is identified
    if len(cards) == 1:
        # Return the card info if its is found
        card = cards[0]
        response = {'bank': card['bank'],
                    'digits': card['last_four_digits']}
        return jsonify(response)
    else:
        return ''


@credit.route('/_infer_statement', methods=('POST',))
@login_required
def infer_statement():
    card_db = CardHandler()
    # Separate the arguments of the POST method
    post_args = request.get_json()
    bank = post_args['bank']
    last_four_digits = post_args['digits']
    transaction_date = parse_date(post_args['transaction_date'])
    # Determine the card used for the transaction from the given info
    cards = card_db.get_entries(banks=(bank,),
                                last_four_digits=(last_four_digits,))
    if len(cards) == 1:
        statement_db = StatementHandler()
        # Determine the statement corresponding to the card and date
        card = cards[0]
        statement = statement_db.infer_statement(card, transaction_date)
        # Check that a statement was found and that it belongs to the user
        if not statement:
            abort(404, 'A statement matching the criteria was not found.')
        return str(statement['issue_date'])
    else:
        return ''


@credit.route('/_infer_bank', methods=('POST',))
@login_required
def infer_bank():
    account_db = AccountHandler()
    # Separate the arguments of the POST method
    post_args = request.get_json()
    account_id = post_args['account_id']
    account = account_db.get_entry(account_id)
    if not account:
        abort(404, 'An account with the given ID was not found.')
    return account['bank']


def prepare_account_choices():
    """Prepare account choices for the card form dropdown."""
    account_db, card_db = AccountHandler(), CardHandler()
    # Collect all available user accounts
    user_accounts = account_db.get_entries()
    choices = [(-1, '-'), (0, 'New account')]
    for account in user_accounts:
        cards = card_db.get_entries(account_ids=(account['id'],))
        digits = [f"*{card['last_four_digits']}" for card in cards]
        # Create a description for the account using the bank and card digits
        description = f"{account['bank']} (cards: {', '.join(digits)})"
        choices.append((account['id'], description))
    return choices
