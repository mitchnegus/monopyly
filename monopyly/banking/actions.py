"""Module describing logical banking actions (e.g. to be used in routes)."""
from .banks import BankHandler
from .accounts import BankAccountHandler, BankAccountTypeHandler
from .transactions import BankTransactionHandler


def get_user_bank_account_groupings():
    """Get groupings (by bank) of a user's bank accounts."""
    bank_db = BankHandler()
    # Get all user banks from the database
    banks = bank_db.get_entries()
    # Get all of the user's bank accounts from the database (grouped by bank)
    bank_accounts = {}
    account_db = BankAccountHandler()
    for bank in banks:
        accounts = account_db.get_entries((bank['id'],))
        if accounts:
            bank_accounts[bank] = accounts
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

