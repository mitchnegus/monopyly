"""
Routes for banking financials.
"""
from collections import Counter

from flask import redirect, render_template, request, url_for, jsonify

from ..auth.tools import login_required
from ..common.transactions import get_linked_transaction
from ..common.actions import get_user_database_entries, delete_database_entry
from . import banking_bp
from .forms import *
from .banks import BankHandler
from .accounts import BankAccountTypeHandler, BankAccountHandler, save_account
from .transactions import (
    BankTransactionHandler, BankSubtransactionHandler, save_transaction
)
from .actions import *


@banking_bp.route('/accounts')
@login_required
def load_accounts():
    bank_accounts = get_user_bank_account_groupings()
    account_types = get_user_database_entries(BankAccountTypeHandler)
    return render_template('banking/accounts_page.html',
                           bank_accounts=bank_accounts,
                           account_types=account_types)


@banking_bp.route('/add_account',
               defaults={'bank_id': None},
               methods=('GET', 'POST'))
@banking_bp.route('/add_account/<int:bank_id>', methods=('GET', 'POST'))
@login_required
def add_account(bank_id):
    form = BankAccountForm.generate_new(bank_id)
    # Check if an account was submitted and add it to the database
    if request.method == 'POST':
        account = save_account(form)
        return redirect(url_for('banking.load_accounts'))
    return render_template('banking/account_form/account_form_page_new.html',
                           form=form)


@banking_bp.route('/delete_account/<int:account_id>')
@login_required
def delete_account(account_id):
    delete_database_entry(BankAccountHandler, account_id)
    return redirect(url_for('banking.load_accounts'))


@banking_bp.route('/account_summaries/<int:bank_id>')
@login_required
def load_account_summaries(bank_id):
    bank_db = BankHandler()
    bank = bank_db.get_entry(bank_id)
    bank_balance, type_accounts = get_bank_account_summaries(bank_id)
    return render_template('banking/account_summaries_page.html',
                           bank=bank,
                           bank_balance=bank_balance,
                           type_accounts=type_accounts)


@banking_bp.route('/account/<int:account_id>')
@login_required
def load_account_details(account_id):
    account, transactions = get_bank_account_details(account_id)
    return render_template('banking/account_page.html',
                           account=account,
                           account_transactions=transactions)


@banking_bp.route('/_expand_transaction', methods=('POST',))
@login_required
def expand_transaction():
    subtransaction_db = BankSubtransactionHandler()
    # Get the transaction ID from the AJAX request
    transaction_id = request.get_json().split('-')[-1]
    # Get the subtransactions
    subtransactions = subtransaction_db.get_entries((transaction_id,))
    return render_template('credit/transactions_table/subtransactions.html',
                           subtransactions=subtransactions)


@banking_bp.route('/_show_linked_transaction', methods=('POST',))
@login_required
def show_linked_transaction():
    post_args = request.get_json()
    transaction_id = post_args['transaction_id']
    db = BankTransactionHandler()
    transaction = db.get_entry(transaction_id)
    linked_transaction = get_linked_transaction(transaction)
    return render_template('common/transactions_table/'
                           'linked_transaction_overlay.html',
                           selected_transaction_type='bank',
                           transaction=transaction,
                           linked_transaction=linked_transaction)


@banking_bp.route('/add_transaction',
               defaults={'bank_id': None, 'account_id': None},
               methods=('GET', 'POST'))
@banking_bp.route('/add_transaction/<int:bank_id>',
               defaults={'account_id': None},
               methods=('GET', 'POST'))
@banking_bp.route('/add_transaction/<int:bank_id>/<int:account_id>',
               methods=('GET', 'POST'))
@login_required
def add_transaction(bank_id, account_id):
    form = BankTransactionForm.generate_new(bank_id, account_id)
    # Check if a transaction was submitted (and add it to the database)
    if request.method == 'POST':
        transaction, subtransactions = save_transaction(form)
        return redirect(url_for('banking.load_account_details',
                                account_id=transaction['account_id']))
    # Display the form for accepting user input
    return render_template('banking/transaction_form/'
                           'transaction_form_page_new.html', form=form,
                           update=False)


@banking_bp.route('/update_transaction/<int:transaction_id>',
              methods=('GET', 'POST'))
@login_required
def update_transaction(transaction_id):
    form = BankTransactionForm.generate_update(transaction_id)
    # Check if a transaction was updated (and update it in the database)
    if request.method == 'POST':
        transaction, subtransactions = save_transaction(form, transaction_id)
        return redirect(url_for('banking.load_account_details',
                                account_id=transaction['account_id']))
    # Display the form for accepting user input
    update = 'transfer' if transaction['internal_transaction_id'] else True
    return render_template('banking/transaction_form/'
                           'transaction_form_page_update.html',
                           transaction_id=transaction_id, form=form,
                           update=update)


@banking_bp.route('/_add_subtransaction_fields', methods=('POST',))
@login_required
def add_subtransaction_fields():
    post_args = request.get_json()
    new_index = post_args['subtransaction_count'] + 1
    # Redefine the form for the transaction (including using entered info)
    # NOTE: This is a hack (since `append_entry` method cannot be used in AJAX
    #       without reloading the form...)
    form_id = f'subtransactions-{new_index}'
    sub_form = BankTransactionForm.SubtransactionSubform(prefix=form_id)
    sub_form.id = form_id
    return render_template('banking/transaction_form/subtransaction_form.html',
                           sub_form=sub_form)


@banking_bp.route('/_add_transfer_fields', methods=('POST',))
@login_required
def add_transfer_fields():
    # Redefine the form for the transaction (including the new transfer fields)
    # NOTE: this is a hack (since `append_entry` method cannot be used in AJAX)
    form_id = 'transfer_account_info-0'
    sub_form = BankTransactionForm.AccountSubform(prefix=form_id)
    sub_form.id = form_id
    return render_template('banking/transaction_form/transfer_form.html',
                           sub_form=sub_form, id_prefix='transfer')


@banking_bp.route('/delete_transaction/<int:transaction_id>')
@login_required
def delete_transaction(transaction_id):
    # Get the account for the transaction to guide the page redirect
    account_id = delete_database_entry(BankTransactionHandler, transaction_id,
                                       return_field='account_id')
    return redirect(url_for('banking.load_account_details',
                            account_id=account_id))


@banking_bp.route('/_suggest_transaction_autocomplete', methods=('POST',))
@login_required
def suggest_transaction_autocomplete():
    # Get the autocomplete field from the AJAX request
    post_args = request.get_json()
    field = post_args['field']
    suggestions = BankTransactionForm.autocomplete(field)
    return jsonify(suggestions)

