"""
Routes for credit card financials.  """
from flask import (
    g, redirect, render_template, flash, request, url_for, jsonify
)
from werkzeug.exceptions import abort
from wtforms.validators import ValidationError

from ..auth.tools import login_required
from ..common.utils import parse_date, dedelimit_float, sort_by_frequency
from ..common.form_utils import form_err_msg
from ..common.transactions import get_linked_transaction
from ..common.actions import get_user_database_entries, delete_database_entry
from ..db.handler.queries import validate_field
from ..banking.banks import BankHandler
from ..banking.accounts import BankAccountHandler
from ..banking.transactions import BankTransactionHandler, record_new_transfer
from . import credit_bp
from .forms import *
from .accounts import CreditAccountHandler
from .cards import CreditCardHandler
from .statements import CreditStatementHandler
from .transactions import (
    CreditTransactionHandler, CreditSubtransactionHandler, CreditTagHandler,
    save_transaction
)
from .actions import *


@credit_bp.route('/cards')
@login_required
def load_cards():
    cards = get_user_database_entries(CreditCardHandler)
    return render_template('credit/cards_page.html', cards=cards)


@credit_bp.route('/add_card', methods=('GET', 'POST'))
@login_required
def add_card():
    # Define a form for a credit card
    form = CreditCardForm()
    # Check if a card was submitted and add it to the database
    if request.method == 'POST':
        if form.validate():
            card_db = CreditCardHandler()
            # Insert the new credit card into the database
            card = card_db.add_entry(form.card_data)
            card_to_replace = _get_card_to_replace(card)
            transfer_form = CardStatementTransferForm()
            if card_to_replace:
                # Disable the form submit button
                form.submit.render_kw = {'disabled': True}
                return render_template('credit/card_form/'
                                       'card_form_page_new.html',
                                       form=form,
                                       card=card,
                                       prior_card=card_to_replace,
                                       transfer_statement_form=transfer_form)
            else:
                return redirect(url_for('credit.load_account',
                                        account_id=card['account_id']))
        else:
            flash(form_err_msg)
            print(form.errors)
    return render_template('credit/card_form/card_form_page_new.html', form=form)


def _get_card_to_replace(card):
    """Get the card that this new card may be intended to replace (if any)."""
    # Card must be active
    if card['active']:
        # Only one other active card must exist for this account
        card_db = CreditCardHandler()
        active_cards = card_db.get_entries(account_ids=(card['account_id'],),
                                           active=True,
                                           fields=('last_four_digits',))
        other_active_cards = [_ for _ in active_cards if _['id'] != card['id']]
        if len(other_active_cards) == 1:
            other_card = other_active_cards[0]
            # That active card must have statements with an unpaid balance
            statement_db = CreditStatementHandler()
            statements = statement_db.get_entries(card_ids=(other_card['id'],),
                                                  fields=('balance',))
            if statements:
                latest_statement = statements[0]
                if latest_statement['balance'] > 0:
                    return other_card
    # Card does not meet all of these conditions
    return None


@credit_bp.route('/_transfer_card_statement/<int:card_id>/<int:prior_card_id>',
              methods=('POST',))
@login_required
def transfer_statement(card_id, prior_card_id):
    # Define and validate the form
    form = CardStatementTransferForm()
    form.validate()
    # Identify the account of the cards
    card_db = CreditCardHandler()
    card = card_db.get_entry(card_id)
    account_id = card['account_id']
    # If response is affirmative, transfer the statement to the new card
    if form['transfer'].data == 'yes':
        # Get the most recent statement
        statement_db = CreditStatementHandler()
        statement = statement_db.get_entries(card_ids=(prior_card_id,))[0]
        # Update the latest statement with the new card (mapping has no 'id')
        statement_mapping_fields = ('card_id', 'issue_date', 'due_date')
        statement_mapping = {_: statement[_] for _ in statement_mapping_fields}
        statement_mapping['card_id'] = card_id
        statement_db.update_entry(statement['id'], statement_mapping)
        # Deactivate the old card
        prior_card = card_db.get_entry(prior_card_id)
        card_mapping_fields = ('account_id', 'last_four_digits', 'active')
        prior_card_mapping = {_:prior_card[_] for _ in card_mapping_fields}
        prior_card_mapping['active'] = 0
        card_db.update_entry(prior_card_id, prior_card_mapping)
    return redirect(url_for('credit.load_account', account_id=account_id))


@credit_bp.route('/account/<int:account_id>')
@login_required
def load_account(account_id):
    account_db = CreditAccountHandler()
    card_db = CreditCardHandler()
    # Get the account information from the database
    account = account_db.get_entry(account_id)
    # Get all cards with active cards at the end of the list
    cards = card_db.get_entries(account_ids=(account_id,))[::-1]
    return render_template('credit/account_page.html',
                           account=account,
                           cards=cards)


@credit_bp.route('/_update_card_status', methods=('POST',))
@login_required
def update_card_status():
    card_db = CreditCardHandler()
    # Get the field from the AJAX request
    post_args = request.get_json()
    input_id = post_args['input_id']
    active = post_args['active']
    # Get the card ID as the second component of the input's ID attribute
    card_id = input_id.split('-')[1]
    # Update the card in the database
    mapping = {'active': int(active)}
    card = card_db.update_entry(card_id, mapping)
    return render_template('credit/card_graphic/card_front.html',
                           card=card)


@credit_bp.route('/delete_card/<int:card_id>')
@login_required
def delete_card(card_id):
    account_id = delete_database_entry(CreditCardHandler, card_id,
                                       return_field='account_id')
    return redirect(url_for('credit.load_account', account_id=account_id))


@credit_bp.route('/_update_account_statement_issue_day/<int:account_id>',
          methods=('POST',))
@login_required
def update_account_statement_issue_day(account_id):
    account_db = CreditAccountHandler()
    # Get the field from the AJAX request
    issue_day = request.get_json()
    # Update the account in the database
    mapping = {'statement_issue_day': int(issue_day)}
    account = account_db.update_entry(account_id, mapping)
    return str(account['statement_issue_day'])


@credit_bp.route('/_update_account_statement_due_day/<int:account_id>',
          methods=('POST',))
@login_required
def update_account_statement_due_day(account_id):
    account_db = CreditAccountHandler()
    # Get the field from the AJAX request
    due_day = request.get_json()
    # Update the account in the database
    mapping = {'statement_due_day': int(due_day)}
    account = account_db.update_entry(account_id, mapping)
    return str(account['statement_due_day'])


@credit_bp.route('/delete_account/<int:account_id>')
@login_required
def delete_account(account_id):
    delete_database_entry(CreditAccountHandler, account_id)
    return redirect(url_for('credit.load_cards'))


@credit_bp.route('/statements')
@login_required
def load_statements():
    card_db = CreditCardHandler()
    # Get all of the user's credit cards from the database
    all_cards = card_db.get_entries()
    active_cards = card_db.get_entries(active=True)
    # Get all of the user's statements for active cards from the database
    card_statements = get_card_statement_groupings(active_cards)
    return render_template('credit/statements_page.html',
                           filter_cards=all_cards,
                           card_statements=card_statements)


@credit_bp.route('/_update_statements_display', methods=('POST',))
@login_required
def update_statements_display():
    card_db = CreditCardHandler()
    # Separate the arguments of the POST method
    post_args = request.get_json()
    filter_ids = post_args['filter_ids']
    # Determine the cards from the arguments of POST method
    cards = [card_db.find_card(*tag.split('-')) for tag in filter_ids]
    # Filter selected statements from the database
    card_statements = get_card_statements(cards)
    return render_template('credit/statements.html',
                           card_statements=card_statements)


@credit_bp.route('/statement/<int:statement_id>')
@login_required
def load_statement_details(statement_id):
    bank_account_db = BankAccountHandler()
    statement_db = CreditStatementHandler()
    transaction_db = CreditTransactionHandler()
    tag_db = CreditTagHandler()
    # Get the statement information from the database
    statement_fields = ('account_id', 'card_id', 'bank_name',
                        'last_four_digits', 'issue_date', 'due_date',
                        'balance', 'payment_date')
    statement = statement_db.get_entry(statement_id, fields=statement_fields)
    # Get all of the transactions for the statement from the database
    sort_order = 'DESC'
    transaction_fields = ('transaction_date', 'vendor', 'total', 'notes',
                          'internal_transaction_id')
    transactions = transaction_db.get_entries(statement_ids=(statement['id'],),
                                              sort_order=sort_order,
                                              fields=transaction_fields)
    # Get bank accounts for potential payments
    bank_accounts = bank_account_db.get_entries()
    # Statistics
    tag_totals = tag_db.get_totals(statement_ids=(statement['id'],))
    tag_totals = {row['tag_name']: row['total'] for row in tag_totals}
    tag_avgs = tag_db.get_statement_average_totals()
    tag_avgs = {row['tag_name']: row['average_total'] for row in tag_avgs}
    return render_template('credit/statement_page.html',
                           statement=statement,
                           statement_transactions=transactions,
                           bank_accounts=bank_accounts,
                           tag_totals=tag_totals,
                           tag_average_totals=tag_avgs)


@credit_bp.route('/_update_statement_due_date/<int:statement_id>',
              methods=('POST',))
@login_required
def update_statement_due_date(statement_id):
    statement_db = CreditStatementHandler()
    # Get the field from the AJAX request
    due_date = request.get_json()
    # Update the statement in the database
    mapping = {'due_date': parse_date(due_date)}
    statement = statement_db.update_entry(statement_id, mapping)
    return str(statement['due_date'])


@credit_bp.route('/_make_payment/<int:statement_id>',
              methods=('POST',))
@login_required
def make_payment(statement_id):
    card_db = CreditCardHandler()
    statement_db = CreditStatementHandler()
    transaction_db = CreditTransactionHandler()
    # Get the field from the AJAX request
    post_args = request.get_json()
    payment_amount = dedelimit_float(post_args['payment_amount'])
    payment_date = parse_date(post_args['payment_date'])
    payment_account_id = int(post_args['payment_bank_account'])
    # Add the payment as a transaction in the database
    card_id = statement_db.get_entry(statement_id, fields=('card_id',))[1]
    card = card_db.get_entry(card_id)
    payment_statement = statement_db.infer_statement(card, payment_date,
                                                     creation=True)
    if payment_account_id:
        bank_account_db  = BankAccountHandler()
        # Ensure that the bank account belongs to the current user
        bank_account_db.get_entry(payment_account_id)
        # Populate a mapping for the transfer
        card_name = f"{card['bank_name']}-{card['last_four_digits']}"
        bank_mapping = {
            'account_id': payment_account_id,
            'transaction_date': payment_date,
            'subtransactions': [{
                'subtotal': -payment_amount,
                'note': f"Credit card payment ({card_name})",
            }]
        }
        transfer, subtransactions = record_new_transfer(bank_mapping)
        internal_transaction_id = transfer['internal_transaction_id']
    else:
        internal_transaction_id = None
    credit_mapping = {
        'internal_transaction_id': internal_transaction_id,
        'statement_id': payment_statement['id'],
        'transaction_date': payment_date,
        'vendor': card['bank_name'],
        'subtransactions': [{
            'subtotal': -payment_amount,
            'note': 'Card payment',
            'tags': ['Payments'],
        }],
    }
    transaction_db.add_entry(credit_mapping)
    # Get the current statement information from the database
    fields = ('card_id', 'bank_name', 'last_four_digits', 'issue_date',
              'due_date', 'balance', 'payment_date')
    statement = statement_db.get_entry(statement_id, fields=fields)
    return render_template('credit/statement_summary.html',
                           statement=statement)


@credit_bp.route('/transactions', defaults={'card_id': None})
@credit_bp.route('/transactions/<int:card_id>', methods=('GET', 'POST'))
@login_required
def load_transactions(card_id):
    card_db = CreditCardHandler()
    transaction_db = CreditTransactionHandler()
    # Get all of the user's credit cards from the database (for the filter)
    cards = card_db.get_entries()
    # Identify cards to be selected in the filter on page load
    if card_id:
        selected_card_ids = [card_id]
    else:
        active_cards = card_db.get_entries(active=True)
        selected_card_ids = [card['id'] for card in active_cards]
    # Get all of the user's transactions for the selected cards
    sort_order = 'DESC'
    transaction_fields = ('account_id', 'bank_name', 'last_four_digits',
                          'transaction_date', 'vendor', 'total', 'notes',
                          'statement_id', 'issue_date',
                          'internal_transaction_id')
    transactions = transaction_db.get_entries(card_ids=selected_card_ids,
                                              sort_order=sort_order,
                                              fields=transaction_fields)
    return render_template('credit/transactions_page.html',
                           filter_cards=cards,
                           selected_card_ids=selected_card_ids,
                           sort_order=sort_order,
                           transactions=transactions)


@credit_bp.route('/_expand_transaction', methods=('POST',))
@login_required
def expand_transaction():
    subtransaction_db = CreditSubtransactionHandler()
    tag_db = CreditTagHandler()
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


@credit_bp.route('/_show_linked_transaction', methods=('POST',))
@login_required
def show_linked_transaction():
    post_args = request.get_json()
    transaction_id = post_args['transaction_id']
    db = CreditTransactionHandler()
    transaction = db.get_entry(transaction_id)
    linked_transaction = get_linked_transaction(transaction)
    return render_template('common/transactions_table/'
                           'linked_transaction_overlay.html',
                           selected_transaction_type='credit',
                           transaction=transaction,
                           linked_transaction=linked_transaction)


@credit_bp.route('/_update_transactions_display', methods=('POST',))
@login_required
def update_transactions_display():
    card_db = CreditCardHandler()
    transaction_db = CreditTransactionHandler()
    # Separate the arguments of the POST method
    post_args = request.get_json()
    filter_ids = post_args['filter_ids']
    sort_order = 'ASC' if post_args['sort_order'] == 'asc' else 'DESC'
    # Determine the card IDs from the arguments of POST method
    cards = [card_db.find_card(*tag.split('-')) for tag in filter_ids]
    # Filter selected transactions from the database
    transaction_fields = ('account_id', 'bank_name', 'last_four_digits',
                          'transaction_date', 'vendor', 'total', 'notes',
                          'statement_id', 'issue_date')
    transactions = transaction_db.get_entries([card['id'] for card in cards],
                                              sort_order=sort_order,
                                              fields=transaction_fields)
    return render_template('credit/transactions_table/transactions.html',
                           sort_order=sort_order,
                           transactions=transactions)


@credit_bp.route('/add_transaction',
              defaults={'card_id': None, 'statement_id': None},
              methods=('GET', 'POST'))
@credit_bp.route('/add_transaction/<int:card_id>',
              defaults={'statement_id': None},
              methods=('GET', 'POST'))
@credit_bp.route('/add_transaction/<int:card_id>/<int:statement_id>',
              methods=('GET', 'POST'))
@login_required
def add_transaction(card_id, statement_id):
    form = CreditTransactionForm()
    # Check if a transaction was submitted (and add it to the database)
    if request.method == 'POST':
        transaction, subtransactions = save_transaction(form)
        return render_template('credit/transaction_submission_page.html',
                               transaction=transaction,
                               subtransactions=subtransactions,
                               update=False)
    else:
        if statement_id:
            statement = CreditStatementHandler().get_entry(statement_id)
            form.prepopulate(statement)
        elif card_id:
            card = CreditCardHandler().get_entry(card_id)
            form.prepopulate(card)
    # Display the form for accepting user input
    return render_template('credit/transaction_form/'
                           'transaction_form_page_new.html', form=form)


@credit_bp.route('/update_transaction/<int:transaction_id>',
              methods=('GET', 'POST'))
@login_required
def update_transaction(transaction_id):
    form = CreditTransactionForm()
    # Check if a transaction was updated (and update it in the database)
    if request.method == 'POST':
        transaction, subtransactions = save_transaction(form, transaction_id)
        return render_template('credit/transaction_submission_page.html',
                               transaction=transaction,
                               subtransactions=subtransactions,
                               update=True)
    else:
        transaction = CreditTransactionHandler().get_entry(transaction_id)
        form.prepopulate_transaction(transaction)
    # Display the form for accepting user input
    return render_template('credit/transaction_form/'
                           'transaction_form_page_update.html',
                           transaction_id=transaction_id, form=form)


@credit_bp.route('/_add_subtransaction_fields', methods=('POST',))
@login_required
def add_subtransaction_fields():
    post_args = request.get_json()
    new_index = post_args['subtransaction_count'] + 1
    # Redefine the form for the transaction (including using entered info)
    # NOTE: This is a hack (since `append_entry` method cannot be used in AJAX
    #       without reloading the form...)
    form_id = f'subtransactions-{new_index}'
    sub_form = CreditTransactionForm.CreditSubtransactionForm(prefix=form_id)
    sub_form.id = form_id
    return render_template('credit/transaction_form/subtransaction_form.html',
                           sub_form=sub_form)


@credit_bp.route('/delete_transaction/<int:transaction_id>')
@login_required
def delete_transaction(transaction_id):
    delete_database_entry(CreditTransactionHandler, transaction_id)
    return redirect(url_for('credit.load_transactions'))


@credit_bp.route('/tags')
@login_required
def load_tags():
    tag_db = CreditTagHandler()
    # Get the tag heirarchy from the database
    heirarchy = tag_db.get_heirarchy()
    return render_template('credit/tags_page.html',
                           tags_heirarchy=heirarchy)

@credit_bp.route('/_add_tag', methods=('POST',))
@login_required
def add_tag():
    tag_db = CreditTagHandler()
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
    return render_template('credit/tag_tree/subtag_tree.html',
                           tag=tag,
                           tags_heirarchy={})


@credit_bp.route('/_delete_tag/', methods=('POST',))
@login_required
def delete_tag():
    tag_db = CreditTagHandler()
    # Get the tag to be deleted from the AJAX request
    post_args = request.get_json()
    tag_name = post_args['tag_name']
    tag = tag_db.find_tag(tag_name)
    # Remove the tag from the database
    tag_db.delete_entries((tag['id'],))
    return ''


@credit_bp.route('/_suggest_transaction_autocomplete', methods=('POST',))
@login_required
def suggest_transaction_autocomplete():
    # Get the autocomplete field from the AJAX request
    post_args = request.get_json()
    field = post_args['field']
    if field != 'note':
        suggestions = CreditTransactionForm.autocomplete(field)
    else:
        vendor = post_args['vendor']
        suggestions = CreditTransactionForm.autocomplete_note(vendor)
    return jsonify(suggestions)


@credit_bp.route('/_suggest_card_autocomplete', methods=('POST',))
@login_required
def suggest_card_autocomplete():
    # Get the autocomplete field from the AJAX request
    post_args = request.get_json()
    field = post_args['field']
    suggestions = CreditCardForm.autocomplete(field)
    return jsonify(suggestions)


@credit_bp.route('/_infer_card', methods=('POST',))
@login_required
def infer_card():
    bank_db = BankHandler()
    card_db = CreditCardHandler()
    # Separate the arguments of the POST method
    post_args = request.get_json()
    bank_name = post_args['bank_name']
    bank = bank_db.get_entries(bank_names=(bank_name,))[0]
    if 'digits' in post_args:
        last_four_digits = post_args['digits']
        # Try to infer card from digits alone
        cards = card_db.get_entries(last_four_digits=(last_four_digits,),
                               active=True)
        if len(cards) != 1:
            # Infer card from digits and bank if necessary
            cards = card_db.get_entries(bank_ids=(bank['id'],),
                                        last_four_digits=(last_four_digits,),
                                        active=True)
    elif 'bank_name' in post_args:
        # Try to infer card from bank alone
        cards = card_db.get_entries(bank_ids=(bank['id'],), active=True)
    # Return an inferred card if a single card is identified
    if len(cards) == 1:
        # Return the card info if its is found
        card = cards[0]
        response = {'bank_name': card['bank_name'],
                    'digits': card['last_four_digits']}
        return jsonify(response)
    else:
        return ''


@credit_bp.route('/_infer_statement', methods=('POST',))
@login_required
def infer_statement():
    bank_db = BankHandler()
    card_db = CreditCardHandler()
    # Separate the arguments of the POST method
    post_args = request.get_json()
    bank_name = post_args['bank_name']
    last_four_digits = post_args['digits']
    transaction_date = parse_date(post_args['transaction_date'])
    # Determine the card used for the transaction from the given info
    bank = bank_db.get_entries(bank_names=(bank_name,))[0]
    cards = card_db.get_entries(bank_ids=(bank['id'],),
                                last_four_digits=(last_four_digits,))
    if len(cards) == 1 and transaction_date:
        statement_db = CreditStatementHandler()
        # Determine the statement corresponding to the card and date
        card = cards[0]
        statement = statement_db.infer_statement(card, transaction_date)
        # Check that a statement was found and that it belongs to the user
        if not statement:
            abort(404, 'A statement matching the criteria was not found.')
        return str(statement['issue_date'])
    else:
        return ''


@credit_bp.route('/_infer_bank', methods=('POST',))
@login_required
def infer_bank():
    account_db = CreditAccountHandler()
    # Separate the arguments of the POST method
    post_args = request.get_json()
    account_id = post_args['account_id']
    account = account_db.get_entry(account_id)
    if not account:
        abort(404, 'An account with the given ID was not found.')
    return account['bank_name']

