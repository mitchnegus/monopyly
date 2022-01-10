"""
Routes for banking financials.
"""
from collections import Counter

from flask import redirect, render_template, flash, request, url_for, jsonify
from wtforms.validators import ValidationError

from ..auth.tools import login_required
from ..utils import check_field, sort_by_frequency
from ..form_utils import form_err_msg
from . import banking
from .forms import *
from .banks import BankHandler
from .accounts import BankAccountTypeHandler, BankAccountHandler
from .transactions import BankTransactionHandler, save_transaction


@banking.route('/accounts')
@login_required
def load_accounts():
    bank_db = BankHandler()
    account_db = BankAccountHandler()
    account_type_db = BankAccountTypeHandler()
    # Get the user's banks from the database
    banks = bank_db.get_entries()
    # Get all of the user's bank accounts from the database
    bank_accounts = {}
    for bank in banks:
        accounts = account_db.get_entries((bank['id'],))
        if accounts:
            bank_accounts[bank] = accounts
    # Get all of the user's bank account types from the database
    account_types = account_type_db.get_entries()
    return render_template('banking/accounts_page.html',
                           bank_accounts=bank_accounts,
                           account_types=account_types)


@banking.route('/add_account',
               defaults={'bank_id': None},
               methods=('GET', 'POST'))
@banking.route('/add_account/<int:bank_id>', methods=('GET', 'POST'))
@login_required
def add_account(bank_id):
    # Define a form for a bank account
    form = BankAccountForm()
    form.prepare_choices()
    # Prepare known form entries if bank is known
    if bank_id:
        form.process(data={'bank_id': bank_id})
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
    return render_template('banking/account_form/account_form_page_new.html', form=form)


@banking.route('/delete_account/<int:account_id>')
@login_required
def delete_account(account_id):
    account_db = BankAccountHandler()
    # Remove the account from the database
    account_db.delete_entries((account_id,))
    return redirect(url_for('banking.load_accounts'))


@banking.route('/account_summaries/<int:bank_id>')
@login_required
def load_account_summaries(bank_id):
    bank_db = BankHandler()
    account_type_db = BankAccountTypeHandler()
    account_db = BankAccountHandler()
    # Get all of the user's matching bank accounts from the database
    bank_account_types = account_type_db.get_types_for_bank(bank_id)
    type_accounts = {}
    for account_type in bank_account_types:
        bank_ids = (bank_id,)
        type_ids = (account_type['id'],)
        accounts = account_db.get_entries(bank_ids, type_ids)
        type_accounts[account_type] = accounts
    # Get the bank info
    bank = bank_db.get_entry(bank_id)
    bank_balance = account_db.get_balance(bank_id)
    return render_template('banking/account_summaries_page.html',
                           bank=bank,
                           bank_balance=bank_balance,
                           type_accounts=type_accounts)


@banking.route('/account/<int:account_id>')
@login_required
def load_account_details(account_id):
    account_db = BankAccountHandler()
    transactions_db = BankTransactionHandler()
    # Get the user's bank account from the database
    account = account_db.get_entry(account_id)
    # Get all of the transactions for the statement from the database
    sort_order = 'DESC'
    transaction_fields = ('transaction_date', 'total', 'balance', 'note',
                          'internal_transaction_id')
    transactions = transactions_db.get_entries(account_ids=(account['id'],),
                                               sort_order=sort_order,
                                               fields=transaction_fields)
    return render_template('banking/account_page.html',
                           account=account,
                           account_transactions=transactions)


@banking.route('/_show_linked_transaction', methods=('POST',))
@login_required
def show_linked_transaction():
    post_args = request.get_json()
    transaction_id = post_args['transaction_id']
    db = BankTransactionHandler()
    transaction = db.get_entry(transaction_id)
    linked_transactions = db.get_associated_transaction(transaction_id)
    if linked_transactions['bank']:
        linked_transaction = linked_transactions['bank']
        linked_transaction_type = 'bank'
    elif linked_transactions['credit']:
        linked_transaction = linked_transactions['credit']
        linked_transaction_type = 'credit'
    else:
        raise ValueError('The linked transaction must be either a credit or '
                         'bank transaction.')
    return render_template('common/transactions_table/'
                           'linked_transaction_overlay.html',
                           selected_transaction_type='bank',
                           linked_transaction_type=linked_transaction_type,
                           transaction=transaction,
                           linked_transaction=linked_transaction)


@banking.route('/add_transaction',
               defaults={'bank_id': None, 'account_id': None},
               methods=('GET', 'POST'))
@banking.route('/add_transaction/<int:bank_id>',
               defaults={'account_id': None},
               methods=('GET', 'POST'))
@banking.route('/add_transaction/<int:bank_id>/<int:account_id>',
               methods=('GET', 'POST'))
@login_required
def add_transaction(bank_id, account_id):
    # Define a form for a transaction
    form = BankTransactionForm()
    # Prepare known form entries if bank is known
    if bank_id:
        bank_db = BankHandler()
        # Get the necessary fields from the database
        bank_fields = ('bank_name',)
        bank = bank_db.get_entry(bank_id, fields=bank_fields)
        data = {'account_info': {field: bank[field] for field in bank_fields}}
        # Prepare known form entries if account is known
        if account_id:
            account_db = BankAccountHandler()
            # Get the necessary fields from the database
            account_fields = ('last_four_digits', 'type_name')
            account = account_db.get_entry(account_id, fields=account_fields)
            for field in account_fields:
                data['account_info'][field] = account[field]
        form.process(data=data)
    # Check if a transaction was submitted (and add it to the database)
    if request.method == 'POST':
        transaction = save_transaction(form)
        return redirect(url_for('banking.load_account_details',
                                account_id=transaction['account_id']))
    # Display the form for accepting user input
    return render_template('banking/transaction_form/'
                           'transaction_form_page_new.html', form=form,
                           update=False)


@banking.route('/update_transaction/<int:transaction_id>',
              methods=('GET', 'POST'))
@login_required
def update_transaction(transaction_id):
    transaction_db = BankTransactionHandler()
    # Get the transaction information from the database
    account_info_data = {}
    transaction = transaction_db.get_entry(transaction_id)
    for field in ('bank_name', 'last_four_digits', 'type_name'):
        account_info_data[field] = transaction[field]
    transfer_account_data = {}
    form_data = {**transaction, 'account_info': account_info_data,
                 'transfer_account_info': transfer_account_data}
    # Define a form for a transaction
    form = BankTransactionForm(data=form_data)
    # Check if a transaction was updated (and update it in the database)
    if request.method == 'POST':
        transaction = save_transaction(form, transaction_id)
        return redirect(url_for('banking.load_account_details',
                                account_id=transaction['account_id']))
    # Display the form for accepting user input
    update = 'transfer' if transaction['internal_transaction_id'] else True
    return render_template('banking/transaction_form/'
                           'transaction_form_page_update.html',
                           transaction_id=transaction_id, form=form,
                           update=update)


@banking.route('/_add_transfer_fields', methods=('POST',))
@login_required
def add_transfer_fields():
    # Redefine the form for the transaction (including the new transfer fields)
    # NOTE: this is a hack (since `append_entry` method cannot be used in AJAX)
    form_id = 'transfer_account_info-0'
    sub_form = BankTransactionForm.BankAccountInfoForm(prefix=form_id)
    sub_form.id = form_id
    return render_template('banking/transaction_form/transfer_form.html',
                           sub_form=sub_form, id_prefix='transfer')


@banking.route('/delete_transaction/<int:transaction_id>')
@login_required
def delete_transaction(transaction_id):
    transaction_db = BankTransactionHandler()
    # Remove the transaction from the database
    account_id = transaction_db.get_entry(transaction_id)['account_id']
    transaction_db.delete_entries((transaction_id,))
    return redirect(url_for('banking.load_account_details',
                            account_id=account_id))


@banking.route('/_suggest_transaction_autocomplete', methods=('POST',))
@login_required
def suggest_transaction_autocomplete():
    # Get the autocomplete field from the AJAX request
    post_args = request.get_json()
    field = post_args['field']
    autocomplete_fields = ('bank_name', 'last_four_digits', 'type_name', 'note')
    check_field(field, autocomplete_fields)
    # Get information from the database to use for autocompletion
    if field == 'bank_name':
        db = BankHandler()
    elif field == 'last_four_digits':
        db = BankAccountHandler()
    elif field == 'type_name':
        db = BankAccountTypeHandler()
    elif field == 'note':
        db = BankTransactionHandler()
    fields = (field,)
    entries = db.get_entries(fields=fields)
    suggestions = sort_by_frequency([entry[field] for entry in entries])
    return jsonify(suggestions)

