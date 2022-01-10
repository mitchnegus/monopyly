"""
Routes for core functionality.
"""
from flask import g, render_template

from . import core
from ..banking.banks import BankHandler
from ..banking.accounts import BankAccountHandler
from ..credit.cards import CreditCardHandler
from ..credit.statements import CreditStatementHandler


@core.route('/')
def index():
    if g.user:
        bank_db = BankHandler()
        account_db = BankAccountHandler()
        card_db = CreditCardHandler()
        statement_db = CreditStatementHandler()
        # Get the user's banks and credit cards from the database
        banks = bank_db.get_entries()
        bank_accounts = {}
        for bank in banks:
            accounts = account_db.get_entries((bank['id'],))
            # Only return banks which have bank accounts
            if accounts:
                bank_accounts[bank] = accounts
        cards = [dict(card) for card in card_db.get_entries(active=True)]
        for card in cards:
            statements = statement_db.get_entries((card['id'],))
            if statements:
                card['last_statement_id'] = statements[0]['id']
            else:
                card['last_statement_id'] = None
    else:
        bank_accounts, cards = None, None
    return render_template('index.html',
                           bank_accounts=bank_accounts,
                           cards=cards)


@core.route('/about')
def about():
    return render_template('about.html')

@core.route('/credits')
def credits():
    return render_template('credits.html')
