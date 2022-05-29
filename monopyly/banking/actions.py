"""Module describing logical actions (e.g. to be used in routes)."""
from .banks import BankHandler
from .accounts import BankAccountHandler, BankAccountTypeHandler


def get_user_bank_account_groupings():
    bank_db = BankHandler()
    account_db = BankAccountHandler()
    # Get all user banks from the database
    banks = bank_db.get_entries()
    # Get all of the user's bank accounts from the database (by bank)
    bank_accounts = {}
    for bank in banks:
        accounts = account_db.get_entries((bank['id'],))
        if accounts:
            bank_accounts[bank] = accounts
    return bank_accounts


def get_user_bank_account_types():
    account_type_db = BankAccountTypeHandler()
    # Get all user bank account types from the database
    return account_type_db.get_entries()

