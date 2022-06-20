"""Tests for the actions performed by the banking blueprint."""
from unittest.mock import Mock, patch

import pytest

from monopyly.banking.actions import *
from test.helpers import TestGrouper


class TestGroupingActions(TestGrouper):

    def test_get_user_bank_account_groupings(self, client_context):
        account_id_groupings = {2: [2, 3], 3: [4]}
        groupings = get_user_bank_account_groupings()
        self.compare_groupings(groupings, account_id_groupings)

    @pytest.mark.parametrize(
        'bank_id, account_id_groupings',
        [[2, {1: [2], 2: [3]}],
         [3, {3: [4]}]]
    )
    def test_get_bank_account_type_groupings(self, client_context, bank_id,
                                             account_id_groupings):
        groupings = get_bank_account_type_groupings(bank_id)
        self.compare_groupings(groupings, account_id_groupings)


@patch('monopyly.banking.actions.get_bank_account_type_groupings')
@patch('monopyly.banking.actions.BankAccountHandler')
def test_get_bank_account_summaries(mock_handler_type, mock_function):
    mock_db = mock_handler_type()
    mock_db.get_bank_balance.return_value = 'test balance'
    mock_function.return_value = 'test groupings'
    bank_id = Mock()
    assert get_bank_account_summaries(bank_id) == ('test balance',
                                                   'test groupings')


@patch('monopyly.banking.actions.BankTransactionHandler')
@patch('monopyly.banking.actions.BankAccountHandler')
def test_get_bank_account_details(mock_account_handler_type,
                                  mock_transaction_handler_type):
    mock_account = {'id': 'test id'}
    mock_account_db = mock_account_handler_type()
    mock_account_db.get_entry.return_value = mock_account
    mock_transaction_db = mock_transaction_handler_type()
    mock_transaction_db.get_entries.return_value = ['test entries']
    default_args = {
        'account_ids': ('test id',),
        'sort_order': 'DESC',
        'fields': (
            'transaction_date',
            'total',
            'balance',
            'notes',
            'internal_transaction_id',
        )
    }
    details = get_bank_account_details(mock_account['id'])
    assert details == (mock_account, ['test entries'])
    mock_transaction_db.get_entries.assert_called_once_with(**default_args)

