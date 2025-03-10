"""Tests for the credit module managing transactions/subtransactions."""

from datetime import date
from unittest.mock import Mock, patch

import pytest
from dry_foundation.testing.helpers import TestHandler
from sqlalchemy.exc import IntegrityError
from werkzeug.exceptions import NotFound

from monopyly.credit.transactions import (
    CreditTagHandler,
    CreditTransactionHandler,
    save_transaction,
)
from monopyly.database.models import (
    CreditSubtransaction,
    CreditTransaction,
    CreditTransactionView,
    TransactionTag,
)

from test_tag_helpers import TestTagHandler


@pytest.fixture
def transaction_handler(client_context):
    return CreditTransactionHandler


def _mock_subtransaction_mappings():
    # Use a function to regenerate mappings (avoid persisting mutations)
    mock_tags = [Mock(name=f"Mock tag {i+1}") for i in range(3)]
    mappings = [
        {
            "subtotal": 100.00,
            "note": "Mock subtransaction mapping 1",
            "tags": mock_tags[:2],
        },
        {
            "subtotal": 200.00,
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


class TestCreditTransactionHandler(TestHandler):
    # References only include entries accessible to the authorized login
    #   - ordered by date (most recent first)
    db_reference = [
        CreditTransactionView(
            id=12,
            internal_transaction_id=None,
            statement_id=7,
            transaction_date=date(2020, 6, 5),
            merchant="Boardwalk",
            total=12.34,
            notes="Back for more...",
        ),
        CreditTransactionView(
            id=11,
            internal_transaction_id=None,
            statement_id=7,
            transaction_date=date(2020, 6, 5),
            merchant="Reading Railroad",
            total=253.99,
            notes="Conducting business",
        ),
        CreditTransactionView(
            id=8,
            internal_transaction_id=None,
            statement_id=5,
            transaction_date=date(2020, 5, 30),
            merchant="Water Works",
            total=26.87,
            notes="Tough loss",
        ),
        CreditTransactionView(
            id=10,
            internal_transaction_id=None,
            statement_id=6,
            transaction_date=date(2020, 5, 10),
            merchant="Income Tax Board",
            total=-1230.00,
            notes="Refund",
        ),
        CreditTransactionView(
            id=7,
            internal_transaction_id=2,
            statement_id=4,
            transaction_date=date(2020, 5, 4),
            merchant="JP Morgan Chance",
            total=-109.21,
            notes="Credit card payment",
        ),
        CreditTransactionView(
            id=6,
            internal_transaction_id=None,
            statement_id=4,
            transaction_date=date(2020, 5, 1),
            merchant="Marvin Gardens",
            total=6500.00,
            notes="Expensive real estate",
        ),
        CreditTransactionView(
            id=5,
            internal_transaction_id=None,
            statement_id=4,
            transaction_date=date(2020, 4, 25),
            merchant="Electric Company",
            total=99.00,
            notes="Electric bill",
        ),
        CreditTransactionView(
            id=9,
            internal_transaction_id=None,
            statement_id=6,
            transaction_date=date(2020, 4, 20),
            merchant="Pennsylvania Avenue",
            total=1600.00,
            notes="Big house tour",
        ),
        CreditTransactionView(
            id=2,
            internal_transaction_id=None,
            statement_id=2,
            transaction_date=date(2020, 4, 13),
            merchant="Top Left Corner",
            total=1.00,
            notes="Parking (thought it was free)",
        ),
        CreditTransactionView(
            id=4,
            internal_transaction_id=None,
            statement_id=3,
            transaction_date=date(2020, 4, 5),
            merchant="Park Place",
            total=65.00,
            notes="One for the park; One for the place",
        ),
        CreditTransactionView(
            id=3,
            internal_transaction_id=None,
            statement_id=3,
            transaction_date=date(2020, 3, 20),
            merchant="Boardwalk",
            total=43.21,
            notes="Merry-go-round",
        ),
        # Transaction without subtransactions
        CreditTransactionView(
            id=13,
            internal_transaction_id=None,
            statement_id=2,
            transaction_date=date(2020, 3, 10),
            merchant="Community Chest",
            total=None,
            notes=None,
        ),
    ]

    @pytest.mark.parametrize(
        "statement_ids, card_ids, active, sort_order, reference_entries",
        [
            [None, None, None, "DESC", db_reference],  # defaults
            [
                (3,),
                None,
                None,
                "DESC",
                (row for row in db_reference if row.statement_id == 3),
            ],
            [
                None,
                (2, 3),
                None,
                "DESC",
                (row for row in db_reference if row.statement_id in (2, 3, 4, 5)),
            ],
            [  # card 2 (statement 2) inactive
                None,
                None,
                True,
                "DESC",
                (row for row in db_reference if row.statement_id != 2),
            ],
            [
                None,
                None,
                False,
                "DESC",
                (row for row in db_reference if row.statement_id == 2),
            ],
            [None, None, None, "ASC", db_reference[::-1]],
        ],
    )
    def test_get_transactions(
        self,
        transaction_handler,
        statement_ids,
        card_ids,
        active,
        sort_order,
        reference_entries,
    ):
        transactions = transaction_handler.get_transactions(
            statement_ids, card_ids, active, sort_order
        )
        self.assert_entries_match(transactions, reference_entries, order=True)

    def test_get_merchants(self, transaction_handler):
        merchants = transaction_handler.get_merchants()
        assert sorted(merchants) == sorted(set(_.merchant for _ in self.db_reference))

    @pytest.mark.parametrize(
        "mapping",
        [
            {
                "internal_transaction_id": None,
                "statement_id": 4,
                "transaction_date": date(2020, 5, 3),
                "merchant": "Baltic Avenue",
                "subtransactions": _mock_subtransaction_mappings(),
            },
            {
                "internal_transaction_id": 2,
                "statement_id": 6,
                "transaction_date": date(2020, 5, 3),
                "merchant": "Mediterranean Avenue",
                "subtransactions": _mock_subtransaction_mappings(),
            },
        ],
    )
    @patch("monopyly.credit.transactions.CreditTagHandler.get_tags")
    def test_add_entry(self, mock_method, transaction_handler, mock_tags, mapping):
        # Mock the tags found by the tag handler
        mock_method.return_value = mock_tags[:2]
        # Add the entry
        transaction = transaction_handler.add_entry(**mapping)
        # Check that the entry object was properly created
        assert transaction.transaction_date == date(2020, 5, 3)
        assert len(transaction.subtransactions) == 2
        assert isinstance(transaction.subtransactions[0], CreditSubtransaction)
        assert transaction.subtransactions[0].subtotal == 100.00
        # Check that the entry was added to the database
        self.assert_number_of_matches(
            1,
            CreditTransaction.id,
            CreditTransaction.transaction_date == date(2020, 5, 3),
        )

    @pytest.mark.parametrize(
        "mapping, exception",
        [
            [
                {
                    "internal_transaction_id": None,
                    "invalid_field": "Test",
                    "transaction_date": date(2022, 5, 3),
                    "merchant": "Baltic Avenue",
                    "subtransactions": _mock_subtransaction_mappings(),
                },
                TypeError,
            ],
            [
                {
                    "internal_transaction_id": 2,
                    "statement_id": 4,
                    "transaction_date": date(2022, 5, 3),
                    "subtransactions": _mock_subtransaction_mappings(),
                },
                IntegrityError,
            ],
            [
                {
                    "internal_transaction_id": 2,
                    "statement_id": 4,
                    "transaction_date": date(2022, 5, 3),
                    "merchant": "Baltic Avenue",
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
                "statement_id": 4,
                "transaction_date": date(2022, 5, 3),
                "subtransactions": _mock_subtransaction_mappings(),
            },
            {"transaction_date": date(2022, 5, 3)},
        ],
    )
    @patch("monopyly.credit.transactions.CreditTagHandler.get_tags")
    def test_update_entry(self, mock_method, transaction_handler, mock_tags, mapping):
        # Mock the tags found by the tag handler
        mock_method.return_value = mock_tags[:2]
        # Add the entry
        transaction = transaction_handler.update_entry(5, **mapping)
        # Check that the entry object was properly updated
        assert transaction.transaction_date == date(2022, 5, 3)
        if "subtransactions" in mapping:
            subtransaction_count = len(mapping["subtransactions"])
            first_subtotal = 100.00
        else:
            subtransaction_count = 1
            first_subtotal = 99.00
        assert len(transaction.subtransactions) == subtransaction_count
        assert transaction.subtransactions[0].subtotal == first_subtotal
        # Check that the entry was updated in the database
        self.assert_number_of_matches(
            1,
            CreditTransaction.id,
            CreditTransaction.transaction_date == date(2022, 5, 3),
        )

    @pytest.mark.parametrize(
        "transaction_id, mapping, exception",
        [
            # Wrong transaction user
            [1, {"statement_id": 1, "transaction_date": date(2022, 5, 3)}, NotFound],
            # Invalid field
            [5, {"statement_id": 4, "invalid_field": "Test"}, ValueError],
            # Nonexistent ID
            [14, {"statement_id": 4, "transaction_date": date(2022, 5, 3)}, NotFound],
        ],
    )
    def test_update_entry_invalid(
        self, transaction_handler, transaction_id, mapping, exception
    ):
        with pytest.raises(exception):
            transaction_handler.update_entry(transaction_id, **mapping)


@pytest.fixture
def tag_handler(client_context):
    return CreditTagHandler


class TestCreditTagHandler(TestTagHandler):
    # Redefine references here to allow them to be used by parametrization
    db_reference = TestTagHandler.db_reference
    db_reference_hierarchy = TestTagHandler.db_reference_hierarchy

    @pytest.mark.parametrize(
        "tag_names, transaction_ids, subtransaction_ids, ancestors, reference_entries",
        [
            [None, None, None, None, db_reference],  # defaults
            [("Railroad", "Utilities"), None, None, None, db_reference[2:4]],
            [None, (10, 11, 12), None, None, [db_reference[0], db_reference[2]]],
            [None, None, (5, 6, 7), None, db_reference[3:5]],
            [("Parking",), None, None, True, db_reference[0:2]],
            [("Parking", "Transportation"), None, None, False, [db_reference[1]]],
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
    @patch("monopyly.credit.transactions._transactions.CreditTransactionHandler")
    @patch("monopyly.credit.forms.CreditTransactionForm")
    def test_save_new_transaction(self, mock_form, mock_handler):
        # Mock the form and primary method
        mock_form.transaction_data = {"key": "test transaction data"}
        mock_method = mock_handler.add_entry
        # Call the function and check for proper call signatures
        transaction = save_transaction(mock_form)
        mock_method.assert_called_once_with(**mock_form.transaction_data)
        assert transaction == mock_method.return_value

    @patch("monopyly.credit.transactions._transactions.CreditTransactionHandler")
    @patch("monopyly.credit.forms.CreditTransactionForm")
    def test_save_updated_transaction(self, mock_form, mock_handler):
        # Mock the form and primary method
        mock_form.transaction_data = {"key": "test transaction data"}
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
