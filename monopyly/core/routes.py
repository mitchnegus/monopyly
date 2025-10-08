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
from .actions import convert_changelog_to_html_template, convert_readme_to_html_template
from .blueprint import bp

APP_ROOT_DIR = Path(__file__).parents[1]


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
        "core/index.html", bank_accounts=bank_accounts, cards=active_cards
    )


@bp.route("/_hide_homepage_block")
@login_required
def hide_homepage_block():
    session["show_homepage_block"] = False
    return ""


@bp.route("/about")
def about():
    readme_path = APP_ROOT_DIR / "README.md"
    about_page_template = convert_readme_to_html_template(readme_path)
    return render_template_string(about_page_template)


@bp.route("/changelog")
def changelog():
    changelog_path = APP_ROOT_DIR / "CHANGELOG.md"
    changelog_page_template = convert_changelog_to_html_template(changelog_path)
    return render_template_string(changelog_page_template)


@bp.route("/story")
@login_required
def story():
    return render_template("core/story.html")


@bp.route("/credits")
def application_credits():
    return render_template("core/credits.html")


@bp.route("/profile")
@login_required
def load_profile():
    banks = BankHandler.get_banks()
    # Return banks as a list to allow multiple reuse
    return render_template("core/profile.html", banks=list(banks))
