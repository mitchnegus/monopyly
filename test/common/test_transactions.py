"""Tests for common aspects of transactions."""
from unittest.mock import MagicMock, patch

import pytest

from monopyly.common.transactions import get_linked_transaction


@pytest.fixture
def mock_transaction():
    mock_transaction = MagicMock()
    return mock_transaction


class TestLinkedTransactionSearch:

    @pytest.mark.parametrize(
        "mock_transaction_id, mock_internal_transaction_id, expected_subtype, "
        "expected_transaction_id",
        [[3, 1, "bank", 6],
         [6, 1, "bank", 3],
         [5, 2, "credit", 7],
         [7, 2, "bank", 5]]
    )
    def test_get_linked_transaction(self, client_context, mock_transaction_id,
                                    mock_internal_transaction_id,
                                    expected_subtype, expected_transaction_id):
        mock_transaction = MagicMock()
        mock_transaction.id = mock_transaction_id
        mock_transaction.internal_transaction_id = mock_internal_transaction_id
        linked_transaction = get_linked_transaction(mock_transaction)
        assert linked_transaction.subtype == expected_subtype
        assert linked_transaction.id == expected_transaction_id

    def test_get_linked_transaction_none(self, client_context):
        mock_transaction = MagicMock()
        mock_transaction.internal_transaction_id = None
        linked_transaction = get_linked_transaction(mock_transaction)
        assert linked_transaction is None

