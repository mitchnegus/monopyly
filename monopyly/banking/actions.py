"""Module describing logical banking actions (to be used in routes)."""

from collections import UserList, namedtuple

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
        A list containing (x, y) pairs, each consisting of the Unix
        timestamp (in milliseconds) and the bank account balance.
    """
    return list(_BalanceChartData(transactions))


class _BalanceChartData(UserList):
    """
    A list of balances to be passed to a `chartist.js` chart constructor.

    A special list-like object containing transaction data formatted for
    use in a balance chart created by the `chartist.js` library. This
    converts each transaction into an (x, y) pair consisting of a Unix
    timestamp (in milleseconds) and a corresponding bank account
    balance. For transactions occurring on the same day (the finest
    granularity recorded by the Monopyly app), a slight offset is
    added to each timestamp to guarantee a smooth representation in the
    rendered chart.

    Parameters
    ----------
    transactions : list
        A list of transactions to be used for generating the chart data.
    """

    _DAILY_MILLISECONDS = 86_400_000
    offset = 1
    point = namedtuple("DataPoint", ["timestamp", "balance"])

    def __init__(self, transactions):
        super().__init__()
        transaction_groups = self._group_transactions_by_date(transactions)
        self._prepare_chart_data(transaction_groups)

    @staticmethod
    def _group_transactions_by_date(transactions):
        date_groups = {}
        for transaction in transactions:
            group = date_groups.setdefault(transaction.transaction_date, [])
            group.append(transaction)
        return date_groups

    def _prepare_chart_data(self, transaction_groups):
        # Assign chart data to the list as tuples, adding offsets for duplicated dates
        for transaction_date, transaction_group in transaction_groups.items():
            base_timestamp = convert_date_to_midnight_timestamp(
                transaction_date, milliseconds=True
            )
            offset = self._DAILY_MILLISECONDS / len(transaction_group)
            for i, transaction in enumerate(transaction_group):
                adjusted_timestamp = base_timestamp + (i * offset)
                self.data.append((adjusted_timestamp, transaction.balance))
