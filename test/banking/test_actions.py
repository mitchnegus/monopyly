"""Tests for the actions performed by the banking blueprint."""
from unittest.mock import Mock, patch, call

from monopyly.banking.actions import get_bank_account_type_grouping


@patch('monopyly.banking.actions.BankAccountHandler.get_accounts')
@patch('monopyly.banking.actions.BankAccountTypeHandler.get_types_for_bank')
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
    for key, mock_account_type in zip(type_accounts, mock_account_types):
        assert key == mock_account_type
        assert type_accounts[mock_account_type] == mock_accounts_method.return_value

