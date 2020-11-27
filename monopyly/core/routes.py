"""
Routes for core functionality.
"""
from flask import render_template

from . import core
from ..banking.banks import BankHandler
from ..credit.cards import CreditCardHandler
from ..credit.statements import CreditStatementHandler


@core.route('/')
def index():
    bank_db = BankHandler()
    card_db = CreditCardHandler()
    statement_db = CreditStatementHandler()
    # Get the user's banks and credit cards from the database
    banks = bank_db.get_entries()
    cards = [dict(card) for card in card_db.get_entries(active=True)]
    for card in cards:
        last_statement = statement_db.get_entries(card_ids=(card['id'],))[0]
        card['last_statement_id'] = last_statement['id']
    return render_template('index.html', banks=banks, cards=cards)

@core.route('/about')
def about():
    return render_template('about.html')
