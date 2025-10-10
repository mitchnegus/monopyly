"""
Routes for credit card financials.
"""

from dry_foundation.database import db_transaction
from flask import (
    abort,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from sqlalchemy.exc import MultipleResultsFound

from ..auth.tools import login_required
from ..banking.accounts import BankAccountHandler
from ..banking.banks import BankHandler
from ..common.forms.utils import extend_field_list_for_ajax
from ..common.transactions import (
    categorize,
    get_linked_transaction,
    highlight_unmatched_transactions,
)
from ..common.utils import dedelimit_float, parse_date
from .accounts import CreditAccountHandler
from .actions import (
    get_card_statement_grouping,
    get_potential_preceding_card,
    get_statement_and_transactions,
    make_payment,
    parse_request_transaction_data,
    transfer_credit_card_statement,
)
from .blueprint import bp
from .cards import CreditCardHandler, save_card
from .forms import CardStatementTransferForm, CreditCardForm, CreditTransactionForm
from .statements import CreditStatementHandler
from .transactions import CreditTransactionHandler, save_transaction
from .transactions.activity import (
    ActivityMatchmaker,
    TransactionActivities,
    parse_transaction_activity_file,
)

# Set a limit on the number of transactions loaded at one time for certain routes
TRANSACTION_LIMIT = 100


@bp.route("/cards")
@login_required
def load_cards():
    cards = CreditCardHandler.get_cards()
    return render_template("credit/cards_page.html", cards=cards)


@bp.route("/add_card", methods=("GET", "POST"))
@login_required
@db_transaction
def add_card():
    # Define a form for a credit card
    form = CreditCardForm()
    # Check if a card was submitted and add it to the database
    if request.method == "POST":
        card = save_card(form)
        preceding_card = get_potential_preceding_card(card)
        if preceding_card:
            # Disable the form submit button
            form.submit.render_kw = {"disabled": True}
            transfer_form = CardStatementTransferForm()
            return render_template(
                "credit/card_form/card_form_page_new.html",
                form=form,
                card=card,
                prior_card=preceding_card,
                transfer_statement_form=transfer_form,
            )
        return redirect(url_for("credit.load_account", account_id=card.account_id))
    return render_template("credit/card_form/card_form_page_new.html", form=form)


@bp.route(
    "/_transfer_card_statement/<int:account_id>/<int:card_id>/<int:prior_card_id>",
    methods=("POST",),
)
@login_required
@db_transaction
def transfer_statement(account_id, card_id, prior_card_id):
    # Define and validate the form
    form = CardStatementTransferForm()
    transfer_credit_card_statement(form, card_id, prior_card_id)
    return redirect(url_for("credit.load_account", account_id=account_id))


@bp.route("/account/<int:account_id>")
@login_required
def load_account(account_id):
    # Get the account information from the database
    account = CreditAccountHandler.get_entry(account_id)
    # Get all cards with active cards at the end of the list
    cards = CreditCardHandler.get_cards(account_ids=(account_id,)).all()
    return render_template(
        "credit/account_page.html", account=account, cards=reversed(cards)
    )


@bp.route("/_update_card_status", methods=("POST",))
@login_required
@db_transaction
def update_card_status():
    # Get the field from the AJAX request
    post_args = request.get_json()
    card_id = int(post_args["card_id"])
    active = int(post_args["active"])
    # Update the card in the database
    card = CreditCardHandler.update_entry(card_id, active=active)
    return render_template("credit/card_graphic/card_front.html", card=card)


@bp.route("/delete_card/<int:card_id>")
@login_required
@db_transaction
def delete_card(card_id):
    account_id = CreditCardHandler.get_entry(card_id).account_id
    CreditCardHandler.delete_entry(card_id)
    return redirect(url_for("credit.load_account", account_id=account_id))


@bp.route("/_update_account_statement_issue_day/<int:account_id>", methods=("POST",))
@login_required
@db_transaction
def update_account_statement_issue_day(account_id):
    # Get the field from the AJAX request
    issue_day = int(request.get_json())
    # Update the account in the database
    account = CreditAccountHandler.update_entry(
        account_id,
        statement_issue_day=issue_day,
    )
    return str(account.statement_issue_day)


@bp.route("/_update_account_statement_due_day/<int:account_id>", methods=("POST",))
@login_required
@db_transaction
def update_account_statement_due_day(account_id):
    # Get the field from the AJAX request
    due_day = int(request.get_json())
    # Update the account in the database
    account = CreditAccountHandler.update_entry(
        account_id,
        statement_due_day=due_day,
    )
    return str(account.statement_due_day)


@bp.route("/delete_account/<int:account_id>")
@login_required
@db_transaction
def delete_account(account_id):
    CreditAccountHandler.delete_entry(account_id)
    return redirect(url_for("credit.load_cards"))


@bp.route("/statements")
@login_required
def load_statements():
    # Get all of the user's credit cards from the database
    all_cards = CreditCardHandler.get_cards()
    active_cards = CreditCardHandler.get_cards(active=True)
    card_statements = get_card_statement_grouping(active_cards)
    return render_template(
        "credit/statements_page.html",
        filter_cards=all_cards,
        card_statements=card_statements,
    )


@bp.route("/_update_statements_display", methods=("POST",))
@login_required
def update_statements_display():
    # Separate the arguments of the POST method
    post_args = request.get_json()
    card_ids = map(int, post_args["card_ids"])
    # Determine the cards from the arguments of POST method
    cards = [CreditCardHandler.get_entry(card_id) for card_id in card_ids]
    card_statements = get_card_statement_grouping(cards)
    # Filter selected statements from the database
    return render_template("credit/statements.html", card_statements=card_statements)


@bp.route("/statement/<int:statement_id>")
@login_required
def load_statement_details(statement_id):
    statement, transactions = get_statement_and_transactions(statement_id)
    categories = categorize(transactions)
    # Get bank accounts for potential payments
    bank_accounts = BankAccountHandler.get_accounts()
    # Save a pointer to this statement to allow easy returns
    session["statement_focus"] = statement_id
    return render_template(
        "credit/statement_page.html",
        statement=statement,
        transactions=transactions,
        bank_accounts=bank_accounts,
        chart_data=categories.assemble_chart_data(exclude=["Credit payments"]),
    )


@bp.before_app_request
def clear_statement_focus():
    exempt_endpoints = (
        "credit.expand_transaction",
        "credit.delete_transaction",
        "static",
        None,
    )
    if request.endpoint not in exempt_endpoints:
        session.pop("statement_focus", None)


@bp.route("/_update_statement_due_date/<int:statement_id>", methods=("POST",))
@login_required
@db_transaction
def update_statement_due_date(statement_id):
    # Get the field from the AJAX request
    due_date = parse_date(request.get_json())
    # Update the statement in the database
    statement = CreditStatementHandler.update_entry(
        statement_id,
        due_date=due_date,
    )
    return str(statement.due_date)


@bp.route("/_pay_credit_card/<int:card_id>/<int:statement_id>", methods=("POST",))
@login_required
@db_transaction
def pay_credit_card(card_id, statement_id):
    # Get the fields from the AJAX request
    post_args = request.get_json()
    payment_amount = dedelimit_float(post_args["payment_amount"])
    payment_date = parse_date(post_args["payment_date"])
    payment_account_id = int(post_args["payment_bank_account"])
    # Pay towards the card balance
    make_payment(card_id, payment_account_id, payment_date, payment_amount)
    # Get the current statement information from the database
    statement = CreditStatementHandler.get_entry(statement_id)
    transactions = CreditTransactionHandler.get_transactions(
        statement_ids=(statement_id,)
    )
    bank_accounts = BankAccountHandler.get_accounts()
    summary_template = render_template(
        "credit/statement_summary.html",
        statement=statement,
        bank_accounts=bank_accounts,
    )
    transactions_table_template = render_template(
        "credit/transactions_table/table.html",
        transactions=transactions,
    )
    return jsonify((summary_template, transactions_table_template))


@bp.route("/_reconcile_activity/<int:statement_id>")
@login_required
def reconcile_activity(statement_id):
    return render_template(
        "credit/statement_reconciliation/statement_reconciliation_inquiry.html",
        statement_id=statement_id,
    )


@bp.route("/reconciliation/<int:statement_id>", methods=("GET", "POST"))
@login_required
def load_statement_reconciliation_details(statement_id):
    if request.method == "POST":
        activity_file = request.files.get("activity-file")
        # Parse the data and match transactions to activities
        if activities := parse_transaction_activity_file(activity_file):
            session["reconciliation_info"] = (statement_id, activities.jsonify())
    else:
        activity_data = session.get("reconciliation_info", (None, []))[1]
        activities = TransactionActivities(activity_data)
    if activities:
        statement, transactions = get_statement_and_transactions(statement_id)
        matchmaker = ActivityMatchmaker(transactions, activities)
        non_matches = matchmaker.unmatched_transactions
        transactions = list(highlight_unmatched_transactions(transactions, non_matches))
        # Calculate the amount charged/refunded during this statement timeframe
        prior_statement = CreditStatementHandler.get_prior_statement(statement)
        prior_statement_balance = prior_statement.balance if prior_statement else 0
        statement_transaction_balance = statement.balance - prior_statement_balance
        return render_template(
            "credit/statement_reconciliation/statement_reconciliation_page.html",
            statement=statement,
            transactions=transactions,
            discrepant_records=matchmaker.match_discrepancies,
            discrepant_amount=abs(statement_transaction_balance - activities.total),
            unrecorded_activities=matchmaker.unmatched_activities,
        )
    else:
        flash("ERROR")
        return redirect(
            url_for("credit.load_statement_details", statement_id=statement_id)
        )


@bp.before_app_request
def clear_reconciliation_info():
    exempt_endpoints = (
        "credit.reconcile_activity",
        "credit.load_statement_reconciliation_details",
        "credit.expand_transaction",
        "credit.add_transaction",
        "credit.update_transaction",
        "credit.infer_statement",
        "credit.suggest_transaction_autocomplete",
        "credit.add_subtransaction_fields",
        "credit.delete_transaction",
        "static",
        None,
    )
    if request.endpoint not in exempt_endpoints:
        session.pop("reconciliation_info", None)


@bp.route("/transactions", defaults={"card_id": None})
@bp.route("/transactions/<int:card_id>")
@login_required
def load_transactions(card_id):
    # Get all of the user's credit cards from the database (for the filter)
    cards = CreditCardHandler.get_cards()
    # Identify cards to be selected in the filter on page load
    if card_id:
        selected_card_ids = [card_id]
    else:
        active_cards = CreditCardHandler.get_cards(active=True)
        selected_card_ids = [card.id for card in active_cards]
    # Get all of the user's transactions for the selected cards
    sort_order = "DESC"
    transactions = CreditTransactionHandler.get_transactions(
        card_ids=selected_card_ids, sort_order=sort_order
    ).all()
    return render_template(
        "credit/transactions_page.html",
        filter_cards=cards,
        selected_card_ids=selected_card_ids,
        sort_order=sort_order,
        transactions=transactions[:TRANSACTION_LIMIT],
        total_transactions=len(transactions),
    )


@bp.route("/_extra_transactions", methods=("POST",))
@login_required
def load_more_transactions():
    # Get info about the transactions being displayed from the AJAX request
    post_args = request.get_json()
    selected_card_ids = map(int, post_args["selected_card_ids"])
    sort_order = "ASC" if post_args["sort_order"] == "asc" else "DESC"
    block_index = post_args["block_count"] - 1
    full_view = post_args["full_view"]
    # Get a subset of the remaining transactions to load
    more_transactions = CreditTransactionHandler.get_transactions(
        card_ids=selected_card_ids,
        sort_order=sort_order,
        offset=block_index * TRANSACTION_LIMIT,
        limit=TRANSACTION_LIMIT,
    )
    return render_template(
        "credit/transactions_table/transactions.html",
        transactions=more_transactions,
        full_view=full_view,
    )


@bp.route("/_update_transactions_display", methods=("POST",))
@login_required
def update_transactions_display():
    # Separate the arguments of the POST method
    post_args = request.get_json()
    card_ids = map(int, post_args["card_ids"])
    sort_order = "ASC" if post_args["sort_order"] == "asc" else "DESC"
    # Filter selected transactions from the database
    transactions = CreditTransactionHandler.get_transactions(
        card_ids=card_ids, sort_order=sort_order, limit=100
    )
    return render_template(
        "credit/transactions_table/table.html",
        sort_order=sort_order,
        transactions=transactions,
        full_view=True,
    )


@bp.route("/_expand_transaction", methods=("POST",))
@login_required
def expand_transaction():
    # Get the transaction ID from the AJAX request
    transaction_id = int(request.get_json())
    transaction = CreditTransactionHandler.get_entry(transaction_id)
    # Get the subtransactions
    subtransactions = transaction.subtransactions
    return render_template(
        "common/transactions_table/subtransactions.html",
        subtransactions=subtransactions,
    )


@bp.route("/_show_linked_transaction", methods=("POST",))
@login_required
def show_linked_transaction():
    post_args = request.get_json()
    transaction_id = int(post_args["transaction_id"])
    transaction = CreditTransactionHandler.get_entry(transaction_id)
    linked_transaction = get_linked_transaction(transaction)
    return render_template(
        "common/transactions_table/linked_transaction_overlay.html",
        selected_transaction_type="credit",
        transaction=transaction,
        linked_transaction=linked_transaction,
    )


@bp.route(
    "/add_transaction",
    defaults={"card_id": None, "statement_id": None},
    methods=("GET", "POST"),
)
@bp.route(
    "/add_transaction/<int:card_id>",
    defaults={"statement_id": None},
    methods=("GET", "POST"),
)
@bp.route("/add_transaction/<int:card_id>/<int:statement_id>", methods=("GET", "POST"))
@login_required
@db_transaction
def add_transaction(card_id, statement_id):
    form = CreditTransactionForm()
    # Check if a transaction was submitted (and add it to the database)
    if request.method == "POST":
        transaction = save_transaction(form)
        return render_template(
            "credit/transaction_submission_page.html",
            transaction=transaction,
            subtransactions=transaction.subtransactions,
            update=False,
        )
    else:
        transaction_data = parse_request_transaction_data(request.args)
        if statement_id:
            entry = CreditStatementHandler.get_entry(statement_id)
        elif card_id:
            entry = CreditCardHandler.get_entry(card_id)
        else:
            entry = None
        form = form.prepopulate(
            entry, data=transaction_data, suggestion_fields=["merchant"]
        )
    # Display the form for accepting user input
    return render_template(
        "credit/transaction_form/transaction_form_page_new.html", form=form
    )


@bp.route("/update_transaction/<int:transaction_id>", methods=("GET", "POST"))
@login_required
@db_transaction
def update_transaction(transaction_id):
    form = CreditTransactionForm()
    # Check if a transaction was updated (and update it in the database)
    if request.method == "POST":
        transaction = save_transaction(form, transaction_id)
        return render_template(
            "credit/transaction_submission_page.html",
            transaction=transaction,
            subtransactions=transaction.subtransactions,
            update=True,
        )
    else:
        transaction_data = parse_request_transaction_data(request.args)
        transaction = CreditTransactionHandler.get_entry(transaction_id)
        form = form.prepopulate(
            transaction, data=transaction_data, suggestion_fields=["amount"]
        )
    # Display the form for accepting user input
    return render_template(
        "credit/transaction_form/transaction_form_page_update.html",
        transaction_id=transaction_id,
        form=form,
    )


@bp.route("/_add_subtransaction_fields", methods=("POST",))
@login_required
def add_subtransaction_fields():
    post_args = request.get_json()
    subtransaction_count = int(post_args["subtransaction_count"])
    # Add a new subtransaction to the form
    new_subform = extend_field_list_for_ajax(
        CreditTransactionForm,
        "subtransactions",
        subtransaction_count,
    )
    return render_template(
        "common/transaction_form/subtransaction_subform.html",
        subform=new_subform,
        field_list_optional_member=True,
    )


@bp.route("/delete_transaction/<int:transaction_id>")
@login_required
@db_transaction
def delete_transaction(transaction_id):
    CreditTransactionHandler.delete_entry(transaction_id)
    if (statement_id := session.pop("statement_focus", None)) is not None:
        statement = CreditStatementHandler.get_entry(statement_id)
        # Delete the statement if it has no more transactions
        if statement.balance is not None:
            return redirect(
                url_for("credit.load_statement_details", statement_id=statement.id)
            )
        CreditStatementHandler.delete_entry(statement.id)
    return redirect(url_for("credit.load_transactions"))


@bp.route("/_suggest_transaction_autocomplete", methods=("POST",))
@login_required
def suggest_transaction_autocomplete():
    # Get the autocomplete field from the AJAX request
    post_args = request.get_json()
    field = post_args["field"]
    if field == "note":
        merchant = post_args["merchant"]
        suggestions = CreditTransactionForm.autocomplete("note", merchant=merchant)
    elif field == "tags":
        suggestions = CreditTransactionForm.autocomplete(
            "tags", db_field_name="tag_name"
        )
    else:
        suggestions = CreditTransactionForm.autocomplete(field)
    return jsonify(suggestions)


@bp.route("/_infer_card", methods=("POST",))
@login_required
def infer_card():
    # Separate the arguments of the POST method
    post_args = request.get_json()
    bank_name = post_args["bank_name"]
    bank = BankHandler.get_banks(bank_names=(bank_name,)).first()
    # Determine criteria for drawing inference
    criteria = {"active": True}
    if bank:
        criteria["bank_ids"] = (bank.id,)
    if "digits" in post_args:
        criteria["last_four_digits"] = (post_args["digits"],)
    # Determine the card used for the transaction from the given info
    cards = CreditCardHandler.get_cards(**criteria)
    try:
        card = cards.one_or_none()
    except MultipleResultsFound:
        card = None
    # Return an inferred card if a single card is identified
    if card:
        response = {
            "bank_name": card.account.bank.bank_name,
            "digits": card.last_four_digits,
        }
        return jsonify(response)
    else:
        return ""


@bp.route("/_infer_statement", methods=("POST",))
@login_required
def infer_statement():
    # Separate the arguments of the POST method
    post_args = request.get_json()
    bank_name = post_args["bank_name"]
    bank = BankHandler.get_banks(bank_names=(bank_name,)).first()
    # Determine criteria for drawing inference
    card_criteria = {"active": True}
    if bank:
        card_criteria["bank_ids"] = (bank.id,)
    if "digits" in post_args:
        card_criteria["last_four_digits"] = (post_args["digits"],)
    # Determine the card used for the transaction from the given info
    cards = CreditCardHandler.get_cards(**card_criteria)
    try:
        card = cards.one_or_none()
    except MultipleResultsFound:
        card = None
    if card and "transaction_date" in post_args:
        # Determine the statement corresponding to the card and date
        transaction_date = parse_date(post_args["transaction_date"])
        statement = CreditStatementHandler.infer_statement(card, transaction_date)
        # Check that a statement was found and that it belongs to the user
        if not statement:
            abort(404, "A statement matching the criteria was not found.")
        return str(statement.issue_date)
    else:
        return ""
