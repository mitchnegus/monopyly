"""Tests for common aspects of transactions."""
from unittest.mock import MagicMock, patch

import pytest

from monopyly.common.transactions import get_linked_transaction


@pytest.fixture
def mock_transaction():
    mock_transaction = MagicMock()
    return mock_transaction


class TestLinkedTransactionSearch:

    def test_get_linked_transaction_none(self, client_context):
        mock_transaction = MagicMock()
        mock_transaction.internal_transaction_id = None
        linked_transaction = get_linked_transaction(mock_transaction)
        assert linked_transaction is None

