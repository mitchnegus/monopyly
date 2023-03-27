"""Tests for common aspects of transactions."""
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.exc import IntegrityError
from werkzeug.exceptions import NotFound

from monopyly.common.transactions import TransactionTagHandler, get_linked_transaction
from monopyly.database.models import TransactionTag

from ..common.helpers import TestTagHandler


@pytest.fixture
def tag_handler(client_context):
    return TransactionTagHandler


class TestTransactionTagHandler(TestTagHandler):
    # Redefine references here to allow them to be used by parametrization
    db_reference = TestTagHandler.db_reference
    db_reference_hierarchy = TestTagHandler.db_reference_hierarchy

    def test_initialization(self, tag_handler):
        assert tag_handler.model == TransactionTag
        assert tag_handler.table == "transaction_tags"
        assert tag_handler.user_id == 3

    @pytest.mark.parametrize(
        "tag_id, reference_entry", [[2, db_reference[0]], [3, db_reference[1]]]
    )
    def test_get_entry(self, tag_handler, tag_id, reference_entry):
        tag = tag_handler.get_entry(tag_id)
        self.assertEntryMatches(tag, reference_entry)

    @pytest.mark.parametrize(
        "tag_id, exception",
        [[1, NotFound], [9, NotFound]],  # Not the logged in user  # Not in the database
    )
    def test_get_entry_invalid(self, tag_handler, tag_id, exception):
        with pytest.raises(exception):
            tag_handler.get_entry(tag_id)

    @pytest.mark.parametrize(
        "tag, expected_subtags",
        [[db_reference[0], db_reference[1:3]], [db_reference[3], db_reference[4:5]]],
    )
    def test_get_subtags(self, tag_handler, tag, expected_subtags):
        subtags = tag_handler.get_subtags(tag)
        self.assertEntriesMatch(subtags, expected_subtags)

    @pytest.mark.parametrize(
        "tag, expected_supertag",
        [
            [db_reference[1], db_reference[0]],
            [db_reference[2], db_reference[0]],
            [db_reference[4], db_reference[3]],
        ],
    )
    def test_get_supertag(self, tag_handler, tag, expected_supertag):
        supertag = tag_handler.get_supertag(tag)
        self.assertEntryMatches(supertag, expected_supertag)

    @pytest.mark.parametrize(
        "root_tag, expected_hierarchy",
        [
            [None, db_reference_hierarchy],
            [db_reference[0], db_reference_hierarchy[db_reference[0]]],
        ],
    )
    def test_get_hierarchy(self, tag_handler, root_tag, expected_hierarchy):
        hierarchy = tag_handler.get_hierarchy(root_tag)
        self._compare_hierarchies(hierarchy, expected_hierarchy)

    @pytest.mark.parametrize(
        "tag, expected_ancestors",
        [
            [db_reference[1], (db_reference[0],)],
            [db_reference[2], (db_reference[0],)],
            [db_reference[0], ()],
            [db_reference[4], (db_reference[3],)],
        ],
    )
    def test_get_ancestors(self, tag_handler, tag, expected_ancestors):
        ancestors = tag_handler.get_ancestors(tag)
        self.assertEntriesMatch(ancestors, expected_ancestors)

    @pytest.mark.parametrize(
        "tag_name, reference_entry",
        [["Transportation", db_reference[0]], ["Electricity", db_reference[4]]],
    )
    def test_find_tag(self, tag_handler, tag_name, reference_entry):
        tag = tag_handler.find_tag(tag_name)
        self.assertEntryMatches(tag, reference_entry)

    @pytest.mark.parametrize("tag_name", ["Trains", None])
    def test_find_tag_none_exist(self, tag_handler, tag_name):
        tag = tag_handler.find_tag(tag_name)
        assert tag is None

    @pytest.mark.parametrize(
        "mapping",
        [
            {"user_id": 3, "parent_id": None, "tag_name": "Entertainment"},
            {"user_id": 3, "parent_id": 5, "tag_name": "Water"},
        ],
    )
    def test_add_entry(self, tag_handler, mapping):
        # Add the entry
        tag = tag_handler.add_entry(**mapping)
        # Check that the entry object was properly created
        assert tag.tag_name == mapping["tag_name"]
        # Check that the entry was added to the database
        self.assertNumberOfMatches(
            1, TransactionTag.id, TransactionTag.tag_name == mapping["tag_name"]
        )

    @pytest.mark.parametrize(
        "mapping, exception",
        [
            [
                {"user_id": 3, "invalid_field": None, "tag_name": "Entertainment"},
                TypeError,
            ],
            [{"user_id": 3, "parent_id": 5}, IntegrityError],
        ],
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
        [
            {"user_id": 3, "parent_id": None, "tag_name": "Trains"},
            {"user_id": 3, "tag_name": "Trains"},
        ],
    )
    def test_update_entry(self, tag_handler, mapping):
        # Add the entry
        tag = tag_handler.update_entry(4, **mapping)
        # Check that the entry object was properly updated
        assert tag.tag_name == "Trains"
        # Check that the entry was updated in the database
        self.assertNumberOfMatches(
            1, TransactionTag.id, TransactionTag.tag_name == "Trains"
        )

    @pytest.mark.parametrize(
        "tag_id, mapping, exception",
        [
            # Wrong tag user
            [1, {"user_id": 3, "tag_name": "Test"}, NotFound],
            # Invalid field
            [5, {"user_id": 3, "invalid_field": "Test"}, ValueError],
            # Nonexistent ID
            [9, {"user_id": 3, "tag_name": "Test"}, NotFound],
        ],
    )
    def test_update_entry_invalid(self, tag_handler, tag_id, mapping, exception):
        with pytest.raises(exception):
            tag_handler.update_entry(tag_id, **mapping)

    @pytest.mark.parametrize("entry_id, subtag_ids", [[4, ()], [5, (6,)]])
    def test_delete_entry(self, tag_handler, entry_id, subtag_ids):
        self.assert_entry_deletion_succeeds(tag_handler, entry_id)
        # Check that the cascading entries were deleted
        self.assertNumberOfMatches(
            0,
            TransactionTag.id,
            TransactionTag.id.in_(subtag_ids),
        )

    @pytest.mark.parametrize(
        "entry_id, exception",
        [
            [1, NotFound],  # should not be able to delete other user entries
            [9, NotFound],  # should not be able to delete nonexistent entries
        ],
    )
    def test_delete_entry_invalid(self, tag_handler, entry_id, exception):
        with pytest.raises(exception):
            tag_handler.delete_entry(entry_id)


@pytest.fixture
def mock_transaction():
    mock_transaction = MagicMock()
    return mock_transaction


class TestLinkedTransactionSearch:
    @pytest.mark.parametrize(
        "mock_transaction_id, mock_internal_transaction_id, expected_subtype, "
        "expected_transaction_id",
        [
            [3, 1, "bank", 6],  # --- bank-bank linked transaction
            [6, 1, "bank", 3],
            [5, 2, "credit", 7],  # - credit-bank linked transaction
            [7, 2, "bank", 5],
        ],
    )
    def test_get_linked_transaction(
        self,
        client_context,
        mock_transaction_id,
        mock_internal_transaction_id,
        expected_subtype,
        expected_transaction_id,
    ):
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
