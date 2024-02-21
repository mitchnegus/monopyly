"""Tests for common aspects of transactions."""

from unittest.mock import MagicMock

import pytest

from monopyly.common.transactions import TransactionTagHandler, get_linked_transaction
from monopyly.database.models import TransactionTag

from test_tag_helpers import TestTagHandler


@pytest.fixture
def tag_handler(client_context):
    return TransactionTagHandler


class TestTransactionTagHandler(TestTagHandler):
    # Redefine references here to allow them to be used by parametrization
    db_reference = TestTagHandler.db_reference
    db_reference_hierarchy = TestTagHandler.db_reference_hierarchy

    @pytest.mark.parametrize(
        "tag, expected_subtags",
        [[db_reference[0], db_reference[1:3]], [db_reference[3], db_reference[4:5]]],
    )
    def test_get_subtags(self, tag_handler, tag, expected_subtags):
        subtags = tag_handler.get_subtags(tag)
        self.assert_entries_match(subtags, expected_subtags)

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
        self.assert_entry_matches(supertag, expected_supertag)

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
        self.assert_entries_match(ancestors, expected_ancestors)

    @pytest.mark.parametrize(
        "tag_name, reference_entry",
        [["Transportation", db_reference[0]], ["Electricity", db_reference[4]]],
    )
    def test_find_tag(self, tag_handler, tag_name, reference_entry):
        tag = tag_handler.find_tag(tag_name)
        self.assert_entry_matches(tag, reference_entry)

    @pytest.mark.parametrize("tag_name", ["Trains", None])
    def test_find_tag_none_exist(self, tag_handler, tag_name):
        tag = tag_handler.find_tag(tag_name)
        assert tag is None


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
