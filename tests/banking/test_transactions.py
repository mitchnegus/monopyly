"""Tests for the banking module managing transactions/subtransactions."""
from datetime import date
from unittest.mock import Mock, patch

import pytest
from authanor.testing.helpers import TestHandler
from sqlalchemy.exc import IntegrityError
from werkzeug.exceptions import NotFound

from monopyly.banking.transactions import (
    BankTagHandler,
    BankTransactionHandler,
    record_new_transfer,
    save_transaction,
)
from monopyly.database.models import (
    BankSubtransaction,
    BankTransaction,
    BankTransactionView,
    TransactionTag,
)

from test_tag_helpers import TestTagHandler


@pytest.fixture
def transaction_handler(client_context):
    return BankTransactionHandler


def _mock_subtransaction_mappings():
    # Use a function to regenerate mappings (avoid persisting mutations)
    mock_tags = [Mock(name=f"Mock tag {i+1}") for i in range(3)]
    mappings = [
        {
            "subtotal": 1000.00,
            "note": "Mock subtransaction mapping 1",
            "tags": mock_tags[:2],
        },
        {
            "subtotal": 2000.00,
            "note": "Mock subtransaction mapping 2",
            "tags": mock_tags[:1],
        },
    ]
    return mappings


@pytest.fixture
def mock_subtransaction_mappings():
    return _mock_subtransaction_mappings()


@pytest.fixture
def mock_tags():
    mock_tags = [
        TransactionTag(id=100, user_id=1, parent_id=None, tag_name="Mock tag 1"),
        TransactionTag(id=101, user_id=1, parent_id=100, tag_name="Mock tag 2"),
        TransactionTag(id=102, user_id=1, parent_id=None, tag_name="Mock tag 3"),
    ]
    return mock_tags


class TestBankTransactionHandler(TestHandler):
    # References only include entries accessible to the authorized login
    #   - ordered by date (most recent first)
    db_reference = [
        BankTransactionView(
            id=7,
            internal_transaction_id=None,
            account_id=4,
            transaction_date=date(2020, 5, 6),
            merchant=None,
            total=200.00,
            notes="'Go' Corner ATM deposit",
            balance=200.00,
        ),
        BankTransactionView(
            id=4,
            internal_transaction_id=None,
            account_id=2,
            transaction_date=date(2020, 5, 6),
            merchant=None,
            total=58.90,
            notes="What else is there to do in Jail?",
            balance=85 + 300 + 58.90,
        ),
        BankTransactionView(
            id=6,
            internal_transaction_id=1,
            account_id=3,
            transaction_date=date(2020, 5, 5),
            merchant="Canteen",
            total=-300.00,
            notes="Transfer out",
            balance=(-300 - 109.21),
        ),
        BankTransactionView(
            id=3,
            internal_transaction_id=1,
            account_id=2,
            transaction_date=date(2020, 5, 5),
            merchant=None,
            total=300.00,
            notes="Transfer in",
            balance=(300 + 85.00),
        ),
        BankTransactionView(
            id=5,
            internal_transaction_id=2,
            account_id=3,
            transaction_date=date(2020, 5, 4),
            merchant="JP Morgan Chance",
            total=-109.21,
            notes="Credit card payment",
            balance=-109.21,
        ),
        BankTransactionView(
            id=2,
            internal_transaction_id=None,
            account_id=2,
            transaction_date=date(2020, 5, 4),
            merchant=None,
            total=85.00,
            notes="Jail subtransaction 1; Jail subtransaction 2",
            balance=85.00,
        ),
    ]

    @pytest.mark.parametrize(
        "account_ids, active, sort_order, reference_entries",
        [
            [None, None, "DESC", db_reference],  # defaults
            [(2, 3), None, "DESC", db_reference[1:]],
            [  # account 3 inactive
                None,
                True,
                "DESC",
                (row for row in db_reference if row.account_id != 3),
            ],
            [None, False, "DESC", (row for row in db_reference if row.account_id == 3)],
            [None, None, "ASC", db_reference[::-1]],
        ],
    )
    def test_get_transactions(
        self, transaction_handler, account_ids, active, sort_order, reference_entries
    ):
        transactions = transaction_handler.get_transactions(
            account_ids, active, sort_order
        )
        self.assert_entries_match(transactions, reference_entries, order=True)

    @pytest.mark.parametrize(
        "mapping",
        [
            {
                "internal_transaction_id": None,
                "account_id": 3,
                "transaction_date": date(2022, 5, 8),
                "subtransactions": _mock_subtransaction_mappings(),
            },
            {
                "internal_transaction_id": 2,
                "account_id": 3,
                "transaction_date": date(2022, 5, 8),
                "subtransactions": _mock_subtransaction_mappings(),
            },
        ],
    )
    @patch("monopyly.banking.transactions.BankTagHandler.get_tags")
    def test_add_entry(self, mock_method, transaction_handler, mock_tags, mapping):
        # Mock the tags found by the tag handler
        mock_method.return_value = mock_tags[:2]
        # Add the entry
        transaction = transaction_handler.add_entry(**mapping)
        # Check that the entry object was properly created
        assert transaction.transaction_date == date(2022, 5, 8)
        assert len(transaction.subtransactions) == 2
        assert isinstance(transaction.subtransactions[0], BankSubtransaction)
        assert transaction.subtransactions[0].subtotal == 1000.00
        # Check that the entry was added to the database
        self.assert_number_of_matches(
            1,
            BankTransaction.id,
            BankTransaction.transaction_date == date(2022, 5, 8),
        )

    @pytest.mark.parametrize(
        "mapping, exception",
        [
            [
                {
                    "internal_transaction_id": None,
                    "invalid_field": "Test",
                    "transaction_date": date(2022, 5, 8),
                    "subtransactions": _mock_subtransaction_mappings(),
                },
                TypeError,
            ],
            [
                {
                    "internal_transaction_id": 2,
                    "account_id": 3,
                    "subtransactions": _mock_subtransaction_mappings(),
                },
                IntegrityError,
            ],
            [
                {
                    "internal_transaction_id": 2,
                    "account_id": 3,
                    "transaction_date": date(2022, 5, 8),
                },
                KeyError,
            ],
        ],
    )
    def test_add_entry_invalid(self, transaction_handler, mapping, exception):
        with pytest.raises(exception):
            transaction_handler.add_entry(**mapping)

    @pytest.mark.parametrize(
        "mapping",
        [
            {
                "internal_transaction_id": None,
                "account_id": 3,
                "transaction_date": date(2022, 5, 8),
            },
            {
                "internal_transaction_id": None,
                "account_id": 3,
                "transaction_date": date(2022, 5, 8),
                "subtransactions": _mock_subtransaction_mappings(),
            },
            {"internal_transaction_id": None, "transaction_date": date(2022, 5, 8)},
        ],
    )
    @patch("monopyly.banking.transactions.BankTagHandler.get_tags")
    def test_update_entry(self, mock_method, transaction_handler, mock_tags, mapping):
        # Mock the tags found by the tag handler
        mock_method.return_value = mock_tags[:2]
        # Add the entry
        transaction = transaction_handler.update_entry(5, **mapping)
        # Check that the entry object was properly updated
        assert transaction.transaction_date == date(2022, 5, 8)
        if "subtransactions" in mapping:
            subtransaction_count = len(mapping["subtransactions"])
            first_subtotal = 1000.00
        else:
            # The subtransaction was not updated for the transaction (ID=5)
            subtransaction_count = 1
            first_subtotal = -109.21
        assert len(transaction.subtransactions) == subtransaction_count
        assert transaction.subtransactions[0].subtotal == first_subtotal
        # Check that the entry was updated in the database
        self.assert_number_of_matches(
            1, BankTransaction.id, BankTransaction.transaction_date == date(2022, 5, 8)
        )

    @pytest.mark.parametrize(
        "transaction_id, mapping, exception",
        [
            # Wrong transaction user
            [1, {"account_id": 1, "transaction_date": date(2022, 5, 8)}, NotFound],
            # Invalid field
            [5, {"account_id": 3, "invalid_field": "Test"}, ValueError],
            # Nonexistent ID
            [8, {"account_id": 3, "transaction_date": date(2022, 5, 8)}, NotFound],
        ],
    )
    def test_update_entry_invalid(
        self, transaction_handler, transaction_id, mapping, exception
    ):
        with pytest.raises(exception):
            transaction_handler.update_entry(transaction_id, **mapping)


@pytest.fixture
def tag_handler(client_context):
    return BankTagHandler


class TestBankTagHandler(TestTagHandler):
    # Redefine references here to allow them to be used by parametrization
    db_reference = TestTagHandler.db_reference
    db_reference_hierarchy = TestTagHandler.db_reference_hierarchy

    @pytest.mark.parametrize(
        "tag_names, transaction_ids, subtransaction_ids, ancestors, reference_entries",
        [
            [None, None, None, None, db_reference],  # defaults
            [("Credit payments",), None, None, None, db_reference[5:6]],
            [None, (4, 5, 6), None, None, db_reference[5:6]],
            [None, None, (2, 3, 4), None, []],
        ],
    )
    def test_get_tags(
        self,
        tag_handler,
        tag_names,
        transaction_ids,
        subtransaction_ids,
        ancestors,
        reference_entries,
    ):
        tags = tag_handler.get_tags(
            tag_names, transaction_ids, subtransaction_ids, ancestors
        )
        self.assert_entries_match(tags, reference_entries)


class TestSaveFormFunctions:
    @patch("monopyly.banking.transactions.BankTransactionHandler")
    @patch("monopyly.banking.forms.BankTransactionForm")
    def test_save_new_transaction(self, mock_form, mock_handler):
        # Mock the form and primary method
        mock_form.transaction_data = {"key": "test transaction data"}
        mock_form.transfer_data = None
        mock_method = mock_handler.add_entry
        # Call the function and check for proper call signatures
        transaction = save_transaction(mock_form)
        mock_method.assert_called_once_with(**mock_form.transaction_data)
        assert transaction == mock_method.return_value

    @patch("monopyly.banking.transactions.record_new_transfer")
    @patch("monopyly.banking.transactions.BankTransactionHandler")
    @patch("monopyly.banking.forms.BankTransactionForm")
    def test_save_new_transaction_with_transfer(
        self, mock_form, mock_handler, mock_function
    ):
        # Mock the form and primary method
        mock_form.transaction_data = {"key": "test transaction data"}
        mock_form.transfer_data = {"key": "test transfer data"}
        mock_method = mock_handler.add_entry
        mock_transfer = mock_function.return_value
        # Mock the expected final set of transaction data
        mock_transaction_data = {
            "internal_transaction_id": mock_transfer.internal_transaction_id,
            **mock_form.transaction_data,
        }
        # Call the function and check for proper call signatures
        transaction = save_transaction(mock_form)
        mock_function.assert_called_once_with(mock_form.transfer_data)
        mock_method.assert_called_once_with(**mock_transaction_data)
        assert transaction == mock_method.return_value

    @patch("monopyly.banking.transactions.BankTransactionHandler")
    @patch("monopyly.banking.forms.BankTransactionForm")
    def test_save_updated_transaction(self, mock_form, mock_handler):
        # Mock the form and primary method
        mock_form.transaction_data = {"key": "test transaction data"}
        mock_form.transfer_data = None
        mock_method = mock_handler.update_entry
        update_transaction = mock_handler.get_entry.return_value
        # Mock the expected final set of transaction data
        mock_transaction_data = {
            "internal_transaction_id": update_transaction.internal_transaction_id,
            **mock_form.transaction_data,
        }
        # Call the function and check for proper call signatures
        transaction_id = 2
        transaction = save_transaction(mock_form, transaction_id)
        mock_method.assert_called_once_with(
            transaction_id,
            **mock_transaction_data,
        )
        assert transaction == mock_method.return_value

    @patch("monopyly.banking.transactions.BankTransactionHandler")
    @patch("monopyly.banking.transactions.add_internal_transaction")
    def test_record_new_transfer(self, mock_function, mock_handler):
        # Mock the return values and data
        mock_transfer_data = {"key": "test data"}
        mock_method = mock_handler.add_entry
        # Call the function and check for proper call signatures
        transfer = record_new_transfer(mock_transfer_data)
        mock_method.assert_called_once_with(
            **mock_transfer_data,
        )
        assert transfer == mock_method.return_value
        new_internal_id = mock_transfer_data["internal_transaction_id"]
        assert new_internal_id == mock_function.return_value
