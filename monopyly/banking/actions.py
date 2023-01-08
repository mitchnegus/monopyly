"""Module describing logical banking actions (to be used in routes)."""
from .accounts import BankAccountHandler, BankAccountTypeHandler


def get_bank_account_type_grouping(bank):
    """Get a summary of accounts for the given bank, grouped by type."""
    # Get a grouping (by account type) of accounts at the given bank
    type_accounts = {}
    for account_type in BankAccountTypeHandler.get_types_for_bank(bank.id):
        # Get only accounts for the logged in user and the given bank
        type_accounts[account_type] = BankAccountHandler.get_accounts(
            bank_ids=(bank.id,),
            account_type_ids=(account_type.id,),
        )
    return type_accounts

