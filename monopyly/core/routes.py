"""
Routes for core functionality.
"""
from pathlib import Path

from flask import g, render_template, render_template_string, session

from ..auth.tools import login_required
from ..banking.accounts import BankAccountHandler
from ..banking.banks import BankHandler
from ..credit.cards import CreditCardHandler
from ..credit.statements import CreditStatementHandler
from .actions import format_readme_as_html_template
from .blueprint import bp


@bp.route("/")
def index():
    if g.user:
        # Set the homepage to show the welcome statement (unless otherwise set)
        session.setdefault("show_homepage_block", True)
        # Get the user's banks and credit cards from the database
        banks = BankHandler.get_banks()
        bank_accounts = {}
        for bank in banks:
            accounts = BankAccountHandler.get_accounts((bank.id,)).all()
            # Only return banks which have bank accounts
            if accounts:
                bank_accounts[bank] = accounts
        active_cards = CreditCardHandler.get_cards(active=True).all()
        for card in active_cards:
            statements = CreditStatementHandler.get_statements((card.id,))
            last_statement = statements.first()
            if last_statement:
                card.last_statement_id = last_statement.id
            else:
                card.last_statement_id = None
    else:
        session["show_homepage_block"] = True
        bank_accounts, active_cards = None, None
    return render_template(
        "index.html", bank_accounts=bank_accounts, cards=active_cards
    )


@bp.route("/_hide_homepage_block")
@login_required
def hide_homepage_block():
    session["show_homepage_block"] = False
    return ""


@bp.route("/about")
def about():
    readme_path = Path(__file__).parents[1] / "README.md"
    with readme_path.open(encoding="utf-8") as readme_file:
        raw_readme_text = readme_file.read()
    about_page_template = format_readme_as_html_template(raw_readme_text)
    return render_template_string(about_page_template)


@bp.route("/story")
@login_required
def story():
    return render_template("story.html")


@bp.route("/credits")
def credits():
    return render_template("credits.html")


@bp.route("/profile")
@login_required
def load_profile():
    banks = BankHandler.get_banks()
    # Return banks as a list to allow multiple reuse
    return render_template("profile.html", banks=list(banks))
