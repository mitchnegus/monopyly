"""Module describing logical banking actions (to be used in routes)."""
from ..common.utils import convert_date_to_midnight_timestamp
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


def get_balance_chart_data(transactions):
    """
    Build a dataset to be passed to a `chartist.js` chart constructor.

    Parameters
    ----------
    transactions : list
        A list of transactions to be used for generating the chart data.

    Returns
    -------
    chart_data : list
        A list of sorted (x, y) pairs consisting of the Unix timestamp
        (in milliseconds) and the bank account balance.
    """
    chart_data = sorted(map(_make_transaction_balance_ordered_pair, transactions))
    return chart_data


def _make_transaction_balance_ordered_pair(transaction):
    # Create an ordered pair of date (timestamp) and account balance
    timestamp = convert_date_to_midnight_timestamp(
        transaction.transaction_date, milliseconds=True
    )
    return timestamp, transaction.balance
