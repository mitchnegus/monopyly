"""
Routes for core functionality.
"""
from flask import g, render_template

from ..auth.tools import login_required
from ..banking.banks import BankHandler
from ..banking.accounts import BankAccountHandler
from ..credit.cards import CreditCardHandler
from ..credit.statements import CreditStatementHandler
from .blueprint import bp


@bp.route('/')
def index():
    if g.user:
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
        bank_accounts, active_cards = None, None
    return render_template('index.html',
                           bank_accounts=bank_accounts,
                           cards=active_cards)


@bp.route('/about')
def about():
    return render_template('about.html')


@bp.route('/credits')
def credits():
    return render_template('credits.html')


@bp.route('/settings')
@login_required
def settings():
    return render_template('settings.html')
