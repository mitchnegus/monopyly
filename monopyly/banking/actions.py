"""Module describing logical banking actions (to be used in routes)."""
from ..common.actions import get_groupings
from .banks import BankHandler
from .accounts import BankAccountHandler, BankAccountTypeHandler
from .transactions import BankTransactionHandler


def get_user_bank_account_groupings():
    """
    Get groupings (by bank) of a user's bank accounts.

    Returns
    -------
    bank_accounts : dict
        A mapping between the bank entries for the user and a list of
        all bank account entries for that bank.
    """
    bank_db = BankHandler()
    account_db = BankAccountHandler()
    # Get all user banks from the database
    banks = bank_db.get_entries()
    # Get groupings of bank accounts (grouped by bank)
    bank_accounts = get_groupings(banks, account_db)
    return bank_accounts


def get_bank_account_type_groupings(bank_id):
    """Get groupings (by account type) of bank accounts at the given bank."""
    account_type_db = BankAccountTypeHandler()
    account_db = BankAccountHandler()
    # Get all bank account types for the given bank
    bank_account_types = account_type_db.get_types_for_bank(bank_id)
    # Get all of the user's bank accounts from the database (grouped by type)
    type_accounts = {}
    for account_type in bank_account_types:
        accounts = account_db.get_entries((bank_id,), (account_type['id'],))
        type_accounts[account_type] = accounts
    return type_accounts


def get_bank_account_summaries(bank_id):
    """Get a summary of accounts for the given bank."""
    account_db = BankAccountHandler()
    # Get the total balance of all accounts at the bank
    bank_balance = account_db.get_bank_balance(bank_id)
    # Get a grouping (by account type) of accounts at the given bank
    type_accounts = get_bank_account_type_groupings(bank_id)
    return bank_balance, type_accounts


def get_bank_account_details(account_id):
    """Get default bank account details (e.g. the account and transactions)."""
    account_db = BankAccountHandler()
    transaction_db = BankTransactionHandler()
    # Get the user's bank account from the database
    account = account_db.get_entry(account_id)
    # Get all of the transactions for the account from the database
    transaction_fields = ('transaction_date', 'total', 'balance', 'notes',
                          'internal_transaction_id')
    transactions = transaction_db.get_entries(account_ids=(account['id'],),
                                              sort_order='DESC',
                                              fields=transaction_fields)
    return account, transactions

