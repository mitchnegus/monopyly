"""Tests for the banking module managing transactions/subtransactions."""
from datetime import date
from unittest.mock import patch, Mock

import pytest
from werkzeug.exceptions import NotFound
from sqlalchemy.exc import IntegrityError

from monopyly.database.models import (
    BankTransaction, BankTransactionView, BankSubtransaction
)
from monopyly.banking.transactions import (
    BankTransactionHandler, save_transaction, record_new_transfer
)
from ..helpers import TestHandler


@pytest.fixture
def transaction_handler(client_context):
    return BankTransactionHandler


def _mock_subtransaction_mappings():
    # Use a function to regenerate mappings (avoid persisting mutations)
    mock_tags = [Mock(name=f"Mock tag {_+1}") for _ in range(3)]
    mappings = [
        {"subtotal": 1000.00, "note": "Mock subtransaction mapping 1"},
        {"subtotal": 2000.00, "note": "Mock subtransaction mapping 2"},
    ]
    return mappings


@pytest.fixture
def mock_subtransaction_mappings():
    return _mock_subtransaction_mappings()


class TestBankTransactionHandler(TestHandler):

    # References only include entries accessible to the authorized login
    #   - ordered by date (most recent first)
    db_reference = [
        BankTransactionView(id=7, internal_transaction_id=None, account_id=4,
                            transaction_date=date(2020, 5, 6), total=200.00,
                            notes="'Go' Corner ATM deposit", balance=200.00),
        BankTransactionView(id=4, internal_transaction_id=None, account_id=2,
                            transaction_date=date(2020, 5, 6), total=58.90,
                            notes="What else is there to do in Jail?",
                            balance=85+300+58.90),
        BankTransactionView(id=6, internal_transaction_id=1, account_id=3,
                            transaction_date=date(2020, 5, 5), total=-300.00,
                            notes="Transfer out", balance=(-300-109.21)),
        BankTransactionView(id=3, internal_transaction_id=1, account_id=2,
                            transaction_date=date(2020, 5, 5), total=300.00,
                            notes="Transfer in", balance=(300+85.00)),
        BankTransactionView(id=5, internal_transaction_id=2, account_id=3,
                            transaction_date=date(2020, 5, 4), total=-109.21,
                            notes="Credit card payment", balance=-109.21),
        BankTransactionView(id=2, internal_transaction_id=None, account_id=2,
                            transaction_date=date(2020, 5, 4), total=85.00,
                            notes="Jail subtransaction 1; Jail subtransaction 2",
                            balance=85.00),
    ]

    def test_initialization(self, transaction_handler):
        assert transaction_handler.model == BankTransaction
        assert transaction_handler.table == "bank_transactions"
        assert transaction_handler.table_view == "bank_transactions_view"
        assert transaction_handler.user_id == 3

    def test_model_view_access(self, transaction_handler):
        assert transaction_handler.model == BankTransaction
        transaction_handler._view_context = True
        assert transaction_handler.model == BankTransactionView
        transaction_handler._view_context = False

    @pytest.mark.parametrize(
        "account_ids, active, sort_order, reference_entries",
        [[None, None, "DESC",                           # defaults
          db_reference],
         [(2, 3), None, "DESC",
          db_reference[1:]],
         [None, True, "DESC",                           # account 3 inactive
         [row for row in db_reference if row.account_id != 3]],
         [None, False, "DESC",
         [row for row in db_reference if row.account_id == 3]],
         [None, None, "ASC",
          db_reference[::-1]]]
    )
    def test_get_transactions(self, transaction_handler, account_ids, active,
                              sort_order, reference_entries):
        transactions = transaction_handler.get_transactions(
            account_ids, active, sort_order
        )
        self.assertEntriesMatch(transactions, reference_entries, order=True)

    @pytest.mark.parametrize(
        "transaction_id, reference_entry",
        [[2, db_reference[5]],
         [3, db_reference[3]]]
    )
    def test_get_entry(self, transaction_handler, transaction_id,
                       reference_entry):
        transaction = transaction_handler.get_entry(transaction_id)
        self.assertEntryMatches(transaction, reference_entry)

    @pytest.mark.parametrize(
        "transaction_id, exception",
        [[1, NotFound],   # Not the logged in user
         [8, NotFound]]   # Not in the database
    )
    def test_get_entry_invalid(self, transaction_handler, transaction_id,
                               exception):
        with pytest.raises(exception):
            transaction_handler.get_entry(transaction_id)

    @pytest.mark.parametrize(
        "mapping",
        [{"internal_transaction_id": None, "account_id": 3,
          "transaction_date": date(2022, 5, 8),
          "subtransactions": _mock_subtransaction_mappings()},
         {"internal_transaction_id": 2, "account_id": 3,
          "transaction_date": date(2022, 5, 8),
          "subtransactions": _mock_subtransaction_mappings()}]
    )
    def test_add_entry(self, transaction_handler, mapping):
        transaction = transaction_handler.add_entry(**mapping)
        # Check that the entry object was properly created
        assert transaction.transaction_date == date(2022, 5, 8)
        assert len(transaction.subtransactions) == 2
        assert isinstance(transaction.subtransactions[0], BankSubtransaction)
        assert transaction.subtransactions[0].subtotal == 1000.00
        # Check that the entry was added to the database
        self.assertNumberOfMatches(
            1,
            BankTransaction.id,
            BankTransaction.transaction_date == date(2022, 5, 8),
        )

    @pytest.mark.parametrize(
        "mapping, exception",
        [[{"internal_transaction_id": None, "invalid_field": "Test",
          "transaction_date": date(2022, 5, 8),
          "subtransactions": _mock_subtransaction_mappings()},
          TypeError],
         [{"internal_transaction_id": 2, "account_id": 3,
          "subtransactions": _mock_subtransaction_mappings()},
          IntegrityError],
         [{"internal_transaction_id": 2, "account_id": 3,
           "transaction_date": date(2022, 5, 8)},
          KeyError]]
    )
    def test_add_entry_invalid(self, transaction_handler, mapping, exception):
        with pytest.raises(exception):
            transaction_handler.add_entry(**mapping)

    def test_add_entry_invalid_user(self, transaction_handler,
                                    mock_subtransaction_mappings):
        mapping = {
            "internal_transaction_id": 2,
            "account_id": 1,
            "transaction_date": date(2022, 5, 8),
            "subtransactions": mock_subtransaction_mappings,
        }
        # Ensure that 'mr.monopyly' cannot add an entry for the test user
        self.assert_invalid_user_entry_add_fails(
            transaction_handler, mapping, invalid_user_id=1, invalid_matches=1
        )

    @pytest.mark.parametrize(
        "mapping",
        [{"internal_transaction_id": None, "account_id": 3,
          "transaction_date": date(2022, 5, 8)},
         {"internal_transaction_id": None, "account_id": 3,
          "transaction_date": date(2022, 5, 8),
          "subtransactions": _mock_subtransaction_mappings()},
         {"internal_transaction_id": None,
          "transaction_date": date(2022, 5, 8)}]
    )
    def test_update_entry(self, transaction_handler, mapping):
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
        self.assertNumberOfMatches(
            1,
            BankTransaction.id,
            BankTransaction.transaction_date == date(2022, 5, 8)
        )

    @pytest.mark.parametrize(
        "transaction_id, mapping, exception",
        [[1, {"account_id": 1, "transaction_date": date(2022, 5, 8)},
          NotFound],                                        # wrong user
         [5, {"account_id": 3, "invalid_field": "Test"},
          ValueError],                                      # invalid field
         [8, {"account_id": 3, "transaction_date": date(2022, 5, 8)},
          NotFound]]                                        # nonexistent ID
    )
    def test_update_entry_invalid(self, transaction_handler, transaction_id,
                                  mapping, exception):
        with pytest.raises(exception):
            transaction_handler.update_entry(transaction_id, **mapping)

    @pytest.mark.parametrize("entry_id", [4, 7])
    def test_delete_entry(self, transaction_handler, entry_id):
        self.assert_entry_deletion_succeeds(transaction_handler, entry_id)
        # Check that the cascading entries were deleted
        self.assertNumberOfMatches(
            0,
            BankSubtransaction.id,
            BankSubtransaction.transaction_id == entry_id,
        )

    @pytest.mark.parametrize(
        "entry_id, exception",
        [[1, NotFound],   # should not be able to delete other user entries
         [8, NotFound]]   # should not be able to delete nonexistent entries
    )
    def test_delete_entry_invalid(self, transaction_handler, entry_id,
                                    exception):
        with pytest.raises(exception):
            transaction_handler.delete_entry(entry_id)


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
    def test_save_new_transaction_with_transfer(self, mock_form, mock_handler,
                                                mock_function):
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

