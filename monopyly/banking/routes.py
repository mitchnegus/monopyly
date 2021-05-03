"""
Routes for banking financials.
"""
from flask import redirect, render_template, flash, request, url_for

from ..auth.tools import login_required
from ..form_utils import form_err_msg
from . import banking
from .forms import *
from .banks import BankHandler
from .accounts import BankAccountTypeHandler, BankAccountHandler
from .transactions import BankTransactionHandler


@banking.route('/accounts')
@login_required
def load_accounts():
    bank_db = BankHandler()
    account_db = BankAccountHandler()
    account_type_db = BankAccountTypeHandler()
    # Get the user's banks from the database
    banks = bank_db.get_entries()
    # Get all of the user's bank accounts from the database
    grouped_accounts = {}
    for bank in banks:
        bank_name = bank['bank_name']
        bank_accounts = account_db.get_entries((bank_name,))
        if bank_accounts:
            grouped_accounts[bank_name] = bank_accounts
    # Get all of the user's bank account types from the database
    account_types = account_type_db.get_entries()
    return render_template('banking/accounts_page.html',
                           grouped_accounts=grouped_accounts,
                           account_types=account_types)


@banking.route('/add_account', methods=('GET', 'POST'))
@login_required
def add_account():
    # Define a form for a bank account
    form = BankAccountForm()
    form.bank_id.choices = prepare_bank_id_choices()
    form.account_type_id.choices = prepare_bank_account_type_choices()
    # Check if an account was submitted and add it to the database
    if request.method == 'POST':
        if form.validate():
            account_db = BankAccountHandler()
            # Insert the new bank account into the database
            account = account_db.add_entry(form.account_data)
            return redirect(url_for('banking.load_accounts'))
        else:
            flash(form_err_msg)
            print(form.errors)
    return render_template('banking/account_form_page_new.html', form=form)


@banking.route('/delete_account/<int:account_id>')
@login_required
def delete_account(account_id):
    account_db = BankAccountHandler()
    # Remove the account from the database
    account_db.delete_entries((account_id,))
    return redirect(url_for('banking.load_accounts'))


@banking.route('/account_summary/<int:bank_id>')
@login_required
def load_summary(bank_id):
    transaction_db = BankTransactionHandler()
    # Get all of the user's transactions for the selected bank and account type
    sort_order  = 'DESC'
    transaction_fields = ('transaction_date', 'amount', 'notes')
    transactions = []
    return render_template('banking/account_summary_page.html',
                           bank_id=bank_id,
                           sort_order=sort_order,
                           transactions=transactions)


@banking.route('/add_transaction',
               defaults={'bank_id': None},
               methods=('GET', 'POST'))
@banking.route('/add_transaction/<int:bank_id>',
               methods=('GET', 'POST'))
@login_required
def add_transaction(bank_id):
    # Define a form for a transaction
    form = BankTransactionForm()
    # Prepare known form entries if bank is known
    if bank_id:
        bank_db = BankHandler()
        # Get the necessary fields from the database
        bank_fields = ('bank_name',)
        bank = bank_db.get_entry(bank_id, fields=bank_fields)
        data = {field: bank[field] for field in bank_fields}
        form.process(data=data)
    # Check if a transaction was submitted and add it to the database
    if request.method == 'POST':
        if form.validate():
            transaction_db = BankTransactionHandler()
            # Insert the new transaction into the database
            transaction_data = form.transaction_data
            entry = transaction_db.add_entry(transaction_data)
            return 'Added transaction'
        else:
            # Show an error to the user and print the errors for the admin
            flash(form_err_msg)
            print(form.errors)
    # Display the form for accepting user input
    return render_template('banking/transaction_form/'
                           'transaction_form_page_new.html', form=form)


@banking.route('/_suggest_transaction_autocomplete', methods=('POST',))
@login_required
def suggest_transaction_autocomplete():
    # Get the autocomplete field from the AJAX request
    return None
    #post_args = request.get_json()
    #field = post_args['field']
    #if field not in ('bank_name'):
    #    raise ValueError(f"'{field}' does not support autocompletion.")
    ## Get information from the database to use for autocompletion
    #bank_db = BankHandler()
    #banks = bank_db.get_entries(fields=(field,))
    #suggestions = [bank['bank_name'] for bank in banks]
    #return jsonify(suggestions)


def prepare_bank_id_choices():
    """Prepare bank choices for the bank account form."""
    bank_db = BankHandler()
    # Colect all available user banks
    user_banks = bank_db.get_entries()
    choices = [(-1, '-')]
    for bank in user_banks:
        choices.append((bank['id'], bank['bank_name']))
    choices.append((0, 'New bank'))
    return choices

def prepare_bank_account_type_choices():
    """Prepare account type choices for the bank account form."""
    account_type_db = BankAccountTypeHandler()
    # Collect all available user account types
    user_account_types = account_type_db.get_entries()
    choices = [(-1, '-')]
    for account_type in user_account_types:
        choices.append((account_type['id'], account_type['type_name']))
    choices.append((0, 'New account type'))
    return choices
