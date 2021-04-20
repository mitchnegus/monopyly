"""
Routes for banking financials.
"""
from flask import redirect, render_template, flash, request, url_for

from ..auth.tools import login_required
from ..form_utils import form_err_msg
from . import banking
from .forms import *
from .banks import BankHandler
from .accounts import BankAccountHandler
from .transactions import BankTransactionHandler


@banking.route('/accounts')
@login_required
def load_accounts():
    bank_db = BankHandler()
    account_db = BankAccountHandler()
    # Get the user's banks from the database
    banks = bank_db.get_entries()
    # Get all of the user's bank accounts from the database
    grouped_accounts = {}
    for bank in banks:
        bank_name = bank['bank_name']
        grouped_accounts[bank_name] = account_db.get_entries((bank_name,))
    return render_template('banking/accounts_page.html',
                           grouped_accounts=grouped_accounts)


@banking.route('/add_account', methods=('GET', 'POST'))
@login_required
def add_account():
    # Define a form for a bank account
    form = BankAccountForm()
    form.bank_id.choices = prepare_bank_id_choices()
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


@banking.route('/load_transactions/<int:bank_id>')
@login_required
def load_transactions(bank_id):
    return render_template('banking/transactions_page.html',
                           bank_id=bank_id)


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
    """Prepare account choices for the bank account form dropdown."""
    bank_db = BankHandler()
    # Colect all available user banks
    user_banks = bank_db.get_entries()
    choices = [(-1, '-'), (0, 'New bank')]
    for bank in user_banks:
        choices.append((bank['id'], bank['bank_name']))
    return choices