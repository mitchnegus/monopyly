from unittest.mock import Mock

import pytest

from monopyly.banking.filters import check_transfer_is_within_bank


# Allows indirect parameters to identify mock transactions by name
@pytest.fixture
def mock_transaction(request):
    transaction = request.getfixturevalue(request.param)
    return transaction


@pytest.fixture
def non_internal_transaction():
    transaction = Mock()
    transaction.internal_transaction = None
    return transaction


@pytest.fixture
def bank_credit_internal_transaction():
    transaction = Mock()
    linked_transaction = Mock()
    transaction.internal_transaction.bank_transactions = [transaction]
    transaction.internal_transaction.credit_transactions = [linked_transaction]
    return transaction


@pytest.fixture
def multi_bank_internal_transaction():
    transaction = Mock()
    linked_transaction = Mock()
    transaction.internal_transaction.bank_transactions = [
        transaction,
        linked_transaction,
    ]
    return transaction


@pytest.fixture
def single_bank_internal_transaction():
    transaction = Mock()
    transaction.account.bank_id = 123
    linked_transaction = Mock()
    linked_transaction.account.bank_id = 123
    transaction.internal_transaction.bank_transactions = [
        transaction,
        linked_transaction,
    ]
    return transaction


@pytest.mark.parametrize(
    ("mock_transaction", "expected_within_bank"),
    [
        ("non_internal_transaction", False),
        ("bank_credit_internal_transaction", False),
        ("multi_bank_internal_transaction", False),
        ("single_bank_internal_transaction", True),
    ],
    indirect=["mock_transaction"],
)
def test_check_transfer_is_within_bank(mock_transaction, expected_within_bank):
    assert check_transfer_is_within_bank(mock_transaction) is expected_within_bank
