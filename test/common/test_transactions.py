"""Tests for common aspects of transactions."""
from unittest.mock import MagicMock, patch

import pytest

from monopyly.common.transactions import get_linked_transaction


@pytest.fixture
def mock_transaction():
    mock_transaction = MagicMock()
    return mock_transaction


class TestLinkedTransactionSearch:

    @patch('monopyly.banking.transactions.BankTransactionHandler')
    def test_get_linked_bank_transaction(self, mock_bank_handler,
                                         mock_transaction):
        mock_bank_method = mock_bank_handler.return_value.query_entries
        mock_bank_method.return_value = ['linked_bank_transaction']
        linked_transaction = get_linked_transaction(mock_transaction)
        assert linked_transaction == 'linked_bank_transaction'

    @patch('monopyly.credit.transactions.CreditTransactionHandler')
    @patch('monopyly.banking.transactions.BankTransactionHandler')
    def test_get_linked_credit_transaction(self, mock_bank_handler,
                                           mock_credit_handler,
                                           mock_transaction):
        mock_bank_method = mock_bank_handler.return_value.query_entries
        mock_bank_method.return_value = None
        mock_credit_method = mock_credit_handler.return_value.query_entries
        mock_credit_method.return_value = ['linked_credit_transaction']
        linked_transaction = get_linked_transaction(mock_transaction)
        assert linked_transaction == 'linked_credit_transaction'

    def test_get_no_linked_transaction(self, mock_transaction):
        mock_method = mock_transaction.db.get_entry
        mock_method.return_value = {'internal_transaction_id': None}
        linked_transaction = get_linked_transaction(mock_transaction)
        assert linked_transaction is None

