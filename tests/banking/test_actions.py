"""Tests for the actions performed by the banking blueprint."""

from datetime import date
from unittest.mock import Mock, call, patch

import pytest

from monopyly.banking.actions import (
    get_balance_chart_data,
    get_bank_account_type_grouping,
)


@patch("monopyly.banking.actions.BankAccountHandler.get_accounts")
@patch("monopyly.banking.actions.BankAccountTypeHandler.get_types_for_bank")
def test_get_bank_account_type_grouping(mock_types_method, mock_accounts_method):
    # Mock the inputs and external return values
    mock_bank = Mock()
    mock_account_types = [Mock() for _ in range(3)]
    mock_types_method.return_value = mock_account_types
    # Check that the returned summary matches the expected format
    type_accounts = get_bank_account_type_grouping(mock_bank)
    assert len(type_accounts) == len(mock_account_types)
    expected_calls = [
        call(bank_ids=(mock_bank.id,), account_type_ids=(mock_account_type.id,))
        for mock_account_type in mock_account_types
    ]
    assert mock_accounts_method.mock_calls == expected_calls
    for key, mock_account_type in zip(type_accounts, mock_account_types, strict=True):
        assert key == mock_account_type
        assert type_accounts[mock_account_type] == mock_accounts_method.return_value


@patch("monopyly.banking.actions.convert_date_to_midnight_timestamp")
def test_get_balance_chart_data(mock_timestamp_converter):
    mock_timestamps = [1577862000, 1577948400, 1578034800]
    mock_timestamp_converter.side_effect = mock_timestamps
    mock_transactions = [Mock(balance=balance) for balance in [100, 200, 400]]
    data = get_balance_chart_data(mock_transactions)
    for i, point in enumerate(data["series"][0]["data"]):
        assert point["x"] == mock_timestamps[i]
        assert point["y"] == mock_transactions[i].balance


@pytest.mark.parametrize(
    ("mock_timestamps", "mock_transaction_dates", "offsets"),
    [
        (
            [1577862000, 1577948400, 1577948400, 1578034800],
            [date(2020, 1, 1)] + 2 * [date(2020, 1, 2)] + [date(2020, 1, 3)],
            {2: (86_400_000 / 2)},
        ),
        (
            [1577862000, 1577948400, 1577948400, 1577948400, 1578034800],
            [date(2020, 1, 1)] + 3 * [date(2020, 1, 2)] + [date(2020, 1, 3)],
            {2: (86_400_000 / 3), 3: 2 * (86_400_000 / 3)},
        ),
        (
            [1577862000, 1577948400, 1577948400, 1577948400, 1578034800, 1578034800],
            [date(2020, 1, 1)] + 3 * [date(2020, 1, 2)] + 2 * [date(2020, 1, 3)],
            {
                2: 1 * (86_400_000 / 3),
                3: 2 * (86_400_000 / 3),
                5: 1 * (86_400_000 / 2),
            },
        ),
    ],
)
@patch("monopyly.banking.actions.convert_date_to_midnight_timestamp")
def test_get_balance_chart_data_duplicate_dates(
    mock_timestamp_converter, mock_timestamps, mock_transaction_dates, offsets
):
    mock_timestamp_converter.side_effect = sorted(set(mock_timestamps))
    mock_transactions = [
        Mock(transaction_date=date_, balance=100 * i)
        for i, date_ in enumerate(mock_transaction_dates, start=1)
    ]
    data = get_balance_chart_data(mock_transactions)
    for i, point in enumerate(data["series"][0]["data"]):
        assert point["x"] == mock_timestamps[i] + offsets.get(i, 0)
        assert point["y"] == mock_transactions[i].balance
