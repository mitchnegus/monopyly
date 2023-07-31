"""
Routes for banking financials.
"""
from flask import jsonify, redirect, render_template, request, url_for
from fuisce.database import db_transaction

from ..auth.tools import login_required
from ..common.forms.utils import extend_field_list_for_ajax
from ..common.transactions import get_linked_transaction
from .accounts import BankAccountHandler, BankAccountTypeHandler, save_account
from .actions import get_balance_chart_data, get_bank_account_type_grouping
from .banks import BankHandler
from .blueprint import bp
from .forms import BankAccountForm, BankTransactionForm
from .transactions import BankTransactionHandler, save_transaction


@bp.route("/accounts")
@login_required
def load_accounts():
    banks = BankHandler.get_banks()
    account_types = BankAccountTypeHandler.get_account_types()
    return render_template(
        "banking/accounts_page.html", banks=banks, account_types=account_types
    )


@bp.route("/add_account", defaults={"bank_id": None}, methods=("GET", "POST"))
@bp.route("/add_account/<int:bank_id>", methods=("GET", "POST"))
@login_required
@db_transaction
def add_account(bank_id):
    form = BankAccountForm()
    # Check if an account was submitted and add it to the database
    if request.method == "POST":
        account = save_account(form)
        return redirect(url_for("banking.load_accounts"))
    else:
        if bank_id:
            bank = BankHandler.get_entry(bank_id)
            form = form.prepopulate(bank)
    return render_template("banking/account_form/account_form_page_new.html", form=form)


@bp.route("/delete_account/<int:account_id>")
@login_required
@db_transaction
def delete_account(account_id):
    BankAccountHandler.delete_entry(account_id)
    return redirect(url_for("banking.load_accounts"))


@bp.route("/account_summaries/<int:bank_id>")
@login_required
def load_account_summaries(bank_id):
    bank = BankHandler.get_entry(bank_id)
    bank_balance = BankAccountHandler.get_bank_balance(bank_id)
    type_accounts = get_bank_account_type_grouping(bank)
    return render_template(
        "banking/account_summaries_page.html",
        bank=bank,
        bank_balance=bank_balance,
        type_accounts=type_accounts,
    )


@bp.route("/account/<int:account_id>")
@login_required
def load_account_details(account_id):
    account = BankAccountHandler.get_entry(account_id)
    transactions = list(
        BankTransactionHandler.get_transactions(
            account_ids=(account_id,), sort_order="DESC"
        )
    )
    # Only display the first 100 transactions
    return render_template(
        "banking/account_page.html",
        account=account,
        account_transactions=transactions[:100],
        chart_data=get_balance_chart_data(transactions),
    )


@bp.route("/_expand_transaction", methods=("POST",))
@login_required
def expand_transaction():
    # Get the transaction ID from the AJAX request
    transaction_id = int(request.get_json())
    transaction = BankTransactionHandler.get_entry(transaction_id)
    return render_template(
        "common/transactions_table/subtransactions.html",
        subtransactions=transaction.subtransactions,
    )


@bp.route("/_show_linked_transaction", methods=("POST",))
@login_required
def show_linked_transaction():
    post_args = request.get_json()
    transaction_id = int(post_args["transaction_id"])
    transaction = BankTransactionHandler.get_entry(transaction_id)
    linked_transaction = get_linked_transaction(transaction)
    return render_template(
        "common/transactions_table/linked_transaction_overlay.html",
        selected_transaction_type="bank",
        transaction=transaction,
        linked_transaction=linked_transaction,
    )


@bp.route(
    "/add_transaction",
    defaults={"bank_id": None, "account_id": None},
    methods=("GET", "POST"),
)
@bp.route(
    "/add_transaction/<int:bank_id>",
    defaults={"account_id": None},
    methods=("GET", "POST"),
)
@bp.route("/add_transaction/<int:bank_id>/<int:account_id>", methods=("GET", "POST"))
@login_required
@db_transaction
def add_transaction(bank_id, account_id):
    form = BankTransactionForm()
    # Check if a transaction was submitted (and add it to the database)
    if request.method == "POST":
        transaction = save_transaction(form)
        return redirect(
            url_for("banking.load_account_details", account_id=transaction.account_id)
        )
    else:
        if account_id:
            account = BankAccountHandler.get_entry(account_id)
            form = form.prepopulate(account)
        elif bank_id:
            bank = BankHandler.get_entry(bank_id)
            form = form.prepopulate(bank)
    # Display the form for accepting user input
    return render_template(
        "banking/transaction_form/transaction_form_page_new.html",
        form=form,
        update=False,
    )


@bp.route("/update_transaction/<int:transaction_id>", methods=("GET", "POST"))
@login_required
@db_transaction
def update_transaction(transaction_id):
    form = BankTransactionForm()
    # Check if a transaction was updated (and update it in the database)
    if request.method == "POST":
        transaction = save_transaction(form, transaction_id)
        return redirect(
            url_for("banking.load_account_details", account_id=transaction.account_id)
        )
    else:
        transaction = BankTransactionHandler.get_entry(transaction_id)
        form = form.prepopulate(transaction)
    # Display the form for accepting user input
    update = "transfer" if transaction.internal_transaction_id else True
    return render_template(
        "banking/transaction_form/transaction_form_page_update.html",
        transaction_id=transaction_id,
        form=form,
        update=update,
    )


@bp.route("/_add_subtransaction_fields", methods=("POST",))
@login_required
def add_subtransaction_fields():
    post_args = request.get_json()
    subtransaction_count = int(post_args["subtransaction_count"])
    # Add a new subtransaction to the form
    new_subform = extend_field_list_for_ajax(
        BankTransactionForm,
        "subtransactions",
        subtransaction_count,
    )
    return render_template(
        "common/transaction_form/subtransaction_subform.html",
        subform=new_subform,
        field_list_optional_member=True,
    )


@bp.route("/_add_transfer_field", methods=("POST",))
@login_required
def add_transfer_field():
    # Add a new transfer field to the form
    new_subform = extend_field_list_for_ajax(
        BankTransactionForm,
        "transfer_accounts_info",
        field_list_count=0,
    )
    return render_template(
        "banking/transaction_form/transfer_form.html",
        subform=new_subform,
        id_prefix="transfer",
        field_list_optional_member=True,
    )


@bp.route("/delete_transaction/<int:transaction_id>")
@login_required
@db_transaction
def delete_transaction(transaction_id):
    # Get the account for the transaction to guide the page redirect
    account_id = BankTransactionHandler.get_entry(transaction_id).account_id
    BankTransactionHandler.delete_entry(transaction_id)
    return redirect(url_for("banking.load_account_details", account_id=account_id))


@bp.route("/_suggest_transaction_autocomplete", methods=("POST",))
@login_required
def suggest_transaction_autocomplete():
    # Get the autocomplete field from the AJAX request
    post_args = request.get_json()
    field = post_args["field"]
    if field == "tags":
        suggestions = BankTransactionForm.autocomplete("tags", db_field_name="tag_name")
    else:
        suggestions = BankTransactionForm.autocomplete(field)
    return jsonify(suggestions)


@bp.route("/_update_bank_name/<int:bank_id>", methods=("POST",))
@login_required
@db_transaction
def update_bank_name(bank_id):
    # Get the bank name from the AJAX request
    bank_name = request.get_json()
    BankHandler.update_entry(bank_id, bank_name=bank_name)
    return bank_name


@bp.route("/delete_bank/<int:bank_id>")
@login_required
@db_transaction
def delete_bank(bank_id):
    BankHandler.delete_entry(bank_id)
    return redirect(url_for("core.load_profile"))
