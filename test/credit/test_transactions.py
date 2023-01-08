"""Tests for the credit module managing transactions/subtransactions."""
from datetime import date
from unittest.mock import patch, Mock

import pytest
from werkzeug.exceptions import NotFound
from sqlalchemy.exc import IntegrityError

from monopyly.database.models import (
    CreditTransaction, CreditTransactionView, CreditSubtransaction, CreditTag
)
from monopyly.credit.transactions import (
    CreditTransactionHandler, CreditTagHandler, save_transaction
)
from ..helpers import TestHandler


@pytest.fixture
def transaction_handler(client_context):
    return CreditTransactionHandler


def _mock_subtransaction_mappings():
    # Use a function to regenerate mappings (avoid persisting mutations)
    mock_tags = [Mock(name=f"Mock tag {_+1}") for _ in range(3)]
    mappings = [
        {"subtotal": 100.00, "note": "Mock subtransaction mapping 1",
         "tags": mock_tags[:2]},
        {"subtotal": 200.00, "note": "Mock subtransaction mapping 2",
         "tags": mock_tags[:1]},
    ]
    return mappings


@pytest.fixture
def mock_subtransaction_mappings():
    return _mock_subtransaction_mappings()


@pytest.fixture
def mock_tags():
    mock_tags = [
        CreditTag(id=100, user_id=1, parent_id=None, tag_name="Mock tag 1"),
        CreditTag(id=101, user_id=1, parent_id=100, tag_name="Mock tag 2"),
        CreditTag(id=102, user_id=1, parent_id=None, tag_name="Mock tag 3"),
    ]
    return mock_tags


class TestCreditTransactionHandler(TestHandler):

    # References only include entries accessible to the authorized login
    #   - ordered by date (most recent first)
    db_reference = [
        CreditTransactionView(id=12, internal_transaction_id=None,
                              statement_id=7,
                              transaction_date=date(2020, 6, 5),
                              vendor="Boardwalk", total=12.34,
                              notes="Back for more..."),
        CreditTransactionView(id=11, internal_transaction_id=None,
                              statement_id=7,
                              transaction_date=date(2020, 6, 5),
                              vendor="Reading Railroad", total=253.99,
                              notes="Conducting business"),
        CreditTransactionView(id=8, internal_transaction_id=None,
                              statement_id=5,
                              transaction_date=date(2020, 5, 30),
                              vendor="Water Works", total=26.87,
                              notes="Tough loss"),
        CreditTransactionView(id=10, internal_transaction_id=None,
                              statement_id=6,
                              transaction_date=date(2020, 5, 10),
                              vendor="Income Tax Board", total=-1230.00,
                              notes="Refund"),
        CreditTransactionView(id=7, internal_transaction_id=2,
                              statement_id=4,
                              transaction_date=date(2020, 5, 4),
                              vendor="JP Morgan Chance", total=-109.21,
                              notes="Credit card payment"),
        CreditTransactionView(id=6, internal_transaction_id=None,
                              statement_id=4,
                              transaction_date=date(2020, 5, 1),
                              vendor="Marvin Gardens", total=6500.00,
                              notes="Expensive real estate"),
        CreditTransactionView(id=5, internal_transaction_id=None,
                              statement_id=4,
                              transaction_date=date(2020, 4, 25),
                              vendor="Electric Company", total=99.00,
                              notes="Electric bill"),
        CreditTransactionView(id=9, internal_transaction_id=None,
                              statement_id=6,
                              transaction_date=date(2020, 4, 20),
                              vendor="Pennsylvania Avenue", total=1600.00,
                              notes="Big house tour"),
        CreditTransactionView(id=2, internal_transaction_id=None,
                              statement_id=2,
                              transaction_date=date(2020, 4, 13),
                              vendor="Top Left Corner", total=1.00,
                              notes="Parking (thought it was free)"),
        CreditTransactionView(id=4, internal_transaction_id=None,
                              statement_id=3,
                              transaction_date=date(2020, 4, 5),
                              vendor="Park Place", total=65.00,
                              notes="One for the park; One for the place"),
        CreditTransactionView(id=3, internal_transaction_id=None,
                              statement_id=3,
                              transaction_date=date(2020, 3, 20),
                              vendor="Boardwalk", total=43.21,
                              notes="Merry-go-round"),
        CreditTransactionView(id=13, internal_transaction_id=None,
                              statement_id=2,
                              transaction_date=date(2020, 3, 10),
                              vendor="Community Chest", total=None,
                              notes=None),  # transaction without subtransactions
    ]

    def test_initialization(self, transaction_handler):
        assert transaction_handler.model == CreditTransaction
        assert transaction_handler.table == "credit_transactions"
        assert transaction_handler.table_view == "credit_transactions_view"
        assert transaction_handler.user_id == 3

    def test_model_view_access(self, transaction_handler):
        assert transaction_handler.model == CreditTransaction
        transaction_handler._view_context = True
        assert transaction_handler.model == CreditTransactionView
        transaction_handler._view_context = False

    @pytest.mark.parametrize(
        "statement_ids, card_ids, active, sort_order, reference_entries",
        [[None, None, None, "DESC",             # defaults
          db_reference],
         [(3, ), None, None, "DESC",
          [row for row in db_reference if row.statement_id == 3]],
         [None, (2, 3), None, "DESC",
          [row for row in db_reference if row.statement_id in (2, 3, 4, 5)]],
         [None, None, True, "DESC",             # card 2 (statement 2) inactive
          [row for row in db_reference if row.statement_id != 2]],
         [None, None, False, "DESC",
          [row for row in db_reference if row.statement_id == 2]],
         [None, None, None, "ASC",
          db_reference[::-1]]]
    )
    def test_get_transactions(self, transaction_handler, statement_ids,
                              card_ids, active, sort_order, reference_entries):
        transactions = transaction_handler.get_transactions(
            statement_ids, card_ids, active, sort_order
        )
        self.assertEntriesMatch(
            transactions, reference_entries, order=True
        )

    @pytest.mark.parametrize(
        "transaction_id, reference_entry",
        [[2, db_reference[8]],
         [3, db_reference[10]]]
    )
    def test_get_entry(self, transaction_handler, transaction_id,
                       reference_entry):
        transaction = transaction_handler.get_entry(transaction_id)
        self.assertEntryMatches(transaction, reference_entry)

    @pytest.mark.parametrize(
        "transaction_id, exception",
        [[1, NotFound],   # Not the logged in user
         [14, NotFound]]  # Not in the database
    )
    def test_get_entry_invalid(self, transaction_handler, transaction_id,
                               exception):
        with pytest.raises(exception):
            transaction_handler.get_entry(transaction_id)

    @pytest.mark.parametrize(
        "mapping",
        [{"internal_transaction_id": None, "statement_id": 4,
          "transaction_date": date(2020, 5, 3), "vendor": "Baltic Avenue",
          "subtransactions": _mock_subtransaction_mappings()},
         {"internal_transaction_id": 2, "statement_id": 6,
          "transaction_date": date(2020, 5, 3),
          "vendor": "Mediterranean Avenue",
          "subtransactions": _mock_subtransaction_mappings()}]
    )
    @patch("monopyly.credit.transactions.CreditTagHandler.get_tags")
    def test_add_entry(self, mock_method, transaction_handler, mock_tags,
                       mapping):
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
        self.assertNumberOfMatches(
            1,
            CreditTransaction.id,
            CreditTransaction.transaction_date == date(2020, 5, 3)
        )

    @pytest.mark.parametrize(
        "mapping, exception",
        [[{"internal_transaction_id": None, "invalid_field": "Test",
           "transaction_date": date(2022, 5, 3), "vendor": "Baltic Avenue",
           "subtransactions": _mock_subtransaction_mappings()},
          TypeError],
         [{"internal_transaction_id": 2, "statement_id": 4,
           "transaction_date": date(2022, 5, 3),
           "subtransactions": _mock_subtransaction_mappings()},
          IntegrityError],
         [{"internal_transaction_id": 2, "statement_id": 4,
           "transaction_date": date(2022, 5, 3), "vendor": "Baltic Avenue"},
          KeyError]]
    )
    def test_add_entry_invalid(self, transaction_handler, mapping, exception):
        with pytest.raises(exception):
            transaction_handler.add_entry(**mapping)

    def test_add_entry_invalid_user(self, transaction_handler,
                                    mock_subtransaction_mappings):
        mapping = {
            "internal_transaction_id": 2,
            "statement_id": 1,
            "transaction_date": date(2022, 5, 3),
            "vendor": "Baltic Avenue",
            "subtransactions": mock_subtransaction_mappings,
        }
        # Ensure that 'mr.monopyly' cannot add an entry for the test user
        self.assert_invalid_user_entry_add_fails(
            transaction_handler, mapping, invalid_user_id=1, invalid_matches=1
        )

    @pytest.mark.parametrize(
        "mapping",
        [{"internal_transaction_id": None, "statement_id": 4,
          "transaction_date": date(2022, 5, 3),
          "subtransactions": _mock_subtransaction_mappings()},
         {"transaction_date": date(2022, 5, 3)}]
    )
    @patch("monopyly.credit.transactions.CreditTagHandler.get_tags")
    def test_update_entry(self, mock_method, transaction_handler, mock_tags,
                          mapping):
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
        self.assertNumberOfMatches(
            1,
            CreditTransaction.id,
            CreditTransaction.transaction_date == date(2022, 5, 3)
        )

    @pytest.mark.parametrize(
        "transaction_id, mapping, exception",
        [[1, {"statement_id": 1, "transaction_date": date(2022, 5, 3)},
          NotFound],                                        # wrong user
         [5, {"statement_id": 4, "invalid_field": "Test"},
          ValueError],                                      # invalid field
         [14, {"statement_id": 4, "transaction_date": date(2022, 5, 3)},
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
            CreditSubtransaction.id,
            CreditSubtransaction.transaction_id == entry_id,
        )

    @pytest.mark.parametrize(
        "entry_id, exception",
        [[1, NotFound],    # should not be able to delete other user entries
         [14, NotFound]]   # should not be able to delete nonexistent entries
    )
    def test_delete_entry_invalid(self, transaction_handler, entry_id,
                                    exception):
        with pytest.raises(exception):
            transaction_handler.delete_entry(entry_id)


@pytest.fixture
def tag_handler(client_context):
    return CreditTagHandler


class TestCreditTagHandler(TestHandler):

    # References only include entries accessible to the authorized login
    db_reference = [
        CreditTag(id=2, user_id=3, parent_id=None, tag_name="Transportation"),
        CreditTag(id=3, user_id=3, parent_id=2, tag_name="Parking"),
        CreditTag(id=4, user_id=3, parent_id=2, tag_name="Railroad"),
        CreditTag(id=5, user_id=3, parent_id=None, tag_name="Utilities"),
        CreditTag(id=6, user_id=3, parent_id=5, tag_name="Electricity"),
    ]

    db_reference_hierarchy = {
        db_reference[0]: {
            db_reference[1]: {},
            db_reference[2]: {},
        },
        db_reference[3]: {
            db_reference[4]: {},
        },
    }

    def _compare_hierarchies(self, hierarchy, reference_hierarchy):
        self.assertEntriesMatch(hierarchy.keys(), reference_hierarchy.keys())
        # Double loop over heirarchies to test equivalence regardless of order
        for key, subhierarchy in hierarchy.items():
            for ref_key, ref_subhierarchy in reference_hierarchy.items():
                if key.id == ref_key.id:
                    self._compare_hierarchies(subhierarchy, ref_subhierarchy)

    def test_initialization(self, tag_handler):
        assert tag_handler.model == CreditTag
        assert tag_handler.table == "credit_tags"
        assert tag_handler.user_id == 3

    @pytest.mark.parametrize(
        "tag_names, transaction_ids, subtransaction_ids, ancestors, reference_entries",
        [[None, None, None, None,             # defaults
          db_reference],
         [("Railroad", "Utilities"), None, None, None,
          db_reference[2:4]],
         [None, (10, 11, 12), None, None,
          [db_reference[0], db_reference[2]]],
         [None, None, (5, 6, 7), None,
          db_reference[3:]],
         [("Parking",), None, None, True,
          db_reference[0:2]],
         [("Parking", "Transportation"), None, None, False,
          [db_reference[1]]]]
    )
    def test_get_tags(self, tag_handler, tag_names, transaction_ids,
                      subtransaction_ids, ancestors, reference_entries):
        tags = tag_handler.get_tags(
            tag_names, transaction_ids, subtransaction_ids, ancestors
        )
        self.assertEntriesMatch(tags, reference_entries)

    @pytest.mark.parametrize(
        "tag_id, reference_entry",
        [[2, db_reference[0]],
         [3, db_reference[1]]]
    )
    def test_get_entry(self, tag_handler, tag_id, reference_entry):
        tag = tag_handler.get_entry(tag_id)
        self.assertEntryMatches(tag, reference_entry)

    @pytest.mark.parametrize(
        "tag_id, exception",
        [[1, NotFound],   # Not the logged in user
         [7, NotFound]]   # Not in the database
    )
    def test_get_entry_invalid(self, tag_handler, tag_id, exception):
        with pytest.raises(exception):
            tag_handler.get_entry(tag_id)

    @pytest.mark.parametrize(
        'tag, expected_subtags',
        [[db_reference[0], db_reference[1:3]],
         [db_reference[3], db_reference[4:]]]
    )
    def test_get_subtags(self, tag_handler, tag, expected_subtags):
        subtags = tag_handler.get_subtags(tag)
        self.assertEntriesMatch(subtags, expected_subtags)

    @pytest.mark.parametrize(
        'tag, expected_supertag',
        [[db_reference[1], db_reference[0]],
         [db_reference[2], db_reference[0]],
         [db_reference[4], db_reference[3]]]
    )
    def test_get_supertag(self, tag_handler, tag, expected_supertag):
        supertag = tag_handler.get_supertag(tag)
        self.assertEntryMatches(supertag, expected_supertag)

    @pytest.mark.parametrize(
        "root_tag, expected_hierarchy",
        [[None, db_reference_hierarchy],
         [db_reference[0], db_reference_hierarchy[db_reference[0]]]]
    )
    def test_get_hierarchy(self, tag_handler, root_tag, expected_hierarchy):
        hierarchy = tag_handler.get_hierarchy(root_tag)
        self._compare_hierarchies(hierarchy, expected_hierarchy)

    @pytest.mark.parametrize(
        "tag, expected_ancestors",
        [[db_reference[1], [db_reference[0]]],
         [db_reference[2], [db_reference[0]]],
         [db_reference[0], []],
         [db_reference[4], [db_reference[3]]]]
    )
    def test_get_ancestors(self, tag_handler, tag, expected_ancestors):
        ancestors = tag_handler.get_ancestors(tag)
        self.assertEntriesMatch(ancestors, expected_ancestors)

    @pytest.mark.parametrize(
        "tag_name, reference_entry",
        [["Transportation", db_reference[0]],
         ["Electricity", db_reference[4]]]
    )
    def test_find_tag(self, tag_handler, tag_name, reference_entry):
        tag = tag_handler.find_tag(tag_name)
        self.assertEntryMatches(tag, reference_entry)

    @pytest.mark.parametrize(
        "tag_name", ["Trains", None]
    )
    def test_find_tag_none_exist(self, tag_handler, tag_name):
        tag = tag_handler.find_tag(tag_name)
        assert tag is None

    @pytest.mark.parametrize(
        "mapping",
        [{"user_id": 3, "parent_id": None, "tag_name": "Entertainment"},
         {"user_id": 3, "parent_id": 5, "tag_name": "Water"}]
    )
    def test_add_entry(self, tag_handler, mapping):
        # Add the entry
        tag = tag_handler.add_entry(**mapping)
        # Check that the entry object was properly created
        assert tag.tag_name == mapping["tag_name"]
        # Check that the entry was added to the database
        self.assertNumberOfMatches(
            1, CreditTag.id, CreditTag.tag_name == mapping["tag_name"]
        )

    @pytest.mark.parametrize(
        "mapping, exception",
        [[{"user_id": 3, "invalid_field": None, "tag_name": "Entertainment"},
          TypeError],
         [{"user_id": 3, "parent_id": 5}, IntegrityError]]
    )
    def test_add_entry_invalid(self, tag_handler, mapping, exception):
        with pytest.raises(exception):
            tag_handler.add_entry(**mapping)

    def test_add_entry_invalid_user(self, tag_handler):
        mapping = {
            "user_id": 1,
            "parent_id": None,
            "tag_name": "Entertainment",
        }
        # Ensure that 'mr.monopyly' cannot add an entry for the test user
        self.assert_invalid_user_entry_add_fails(
            tag_handler, mapping, invalid_user_id=1, invalid_matches=1
        )

    @pytest.mark.parametrize(
        "mapping",
        [{"user_id": 3, "parent_id": None, "tag_name": "Trains"},
         {"user_id": 3, "tag_name": "Trains"}]
    )
    def test_update_entry(self, tag_handler, mapping):
        # Add the entry
        tag = tag_handler.update_entry(4, **mapping)
        # Check that the entry object was properly updated
        assert tag.tag_name == "Trains"
        # Check that the entry was updated in the database
        self.assertNumberOfMatches(
            1, CreditTag.id, CreditTag.tag_name == "Trains"
        )

    @pytest.mark.parametrize(
        "tag_id, mapping, exception",
        [[1, {"user_id": 3, "tag_name": "Test"},
          NotFound],                                        # wrong user
         [5, {"user_id": 3, "invalid_field": "Test"},
          ValueError],                                      # invalid field
         [7, {"user_id": 3, "tag_name": "Test"},
          NotFound]]                                        # nonexistent ID
    )
    def test_update_entry_invalid(self, tag_handler, tag_id, mapping,
                                  exception):
        with pytest.raises(exception):
            tag_handler.update_entry(tag_id, **mapping)

    @pytest.mark.parametrize(
        "entry_id, subtag_ids",
        [[4, ()],
         [5, (6,)]]
    )
    def test_delete_entry(self, tag_handler, entry_id, subtag_ids):
        self.assert_entry_deletion_succeeds(tag_handler, entry_id)
        # Check that the cascading entries were deleted
        self.assertNumberOfMatches(
            0,
            CreditTag.id,
            CreditTag.id.in_(subtag_ids),
        )

    @pytest.mark.parametrize(
        "entry_id, exception",
        [[1, NotFound],    # should not be able to delete other user entries
         [7, NotFound]]    # should not be able to delete nonexistent entries
    )
    def test_delete_entry_invalid(self, tag_handler, entry_id, exception):
        with pytest.raises(exception):
            tag_handler.delete_entry(entry_id)


class TestSaveFormFunctions:

    @patch("monopyly.credit.transactions.CreditTransactionHandler")
    @patch("monopyly.credit.forms.CreditTransactionForm")
    def test_save_new_transaction(self, mock_form, mock_handler):
        # Mock the form and primary method
        mock_form.transaction_data = {"key": "test transaction data"}
        mock_method = mock_handler.add_entry
        # Call the function and check for proper call signatures
        transaction = save_transaction(mock_form)
        mock_method.assert_called_once_with(**mock_form.transaction_data)
        assert transaction == mock_method.return_value

    @patch("monopyly.credit.transactions.CreditTransactionHandler")
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

