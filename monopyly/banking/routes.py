"""
Routes for banking financials.
"""
from ..auth.tools import login_required
from . import banking
from .accounts import BankAccountHandler


@banking.route('/accounts')
@login_required
def load_accounts():
    account_db = BankAccountHandler()
    # Get all of the user's bank accounts from the database
    accounts = account_db.get_entries()
    return 'Accounts found'
