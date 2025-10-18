"""Tests for common aspects of transactions."""

from unittest.mock import MagicMock, Mock

import pytest

from monopyly.common.transactions import (
    CategoryTree,
    RootCategoryTree,
    TransactionTagHandler,
    get_linked_transaction,
    get_subtransactions,
    highlight_unmatched_transactions,
)
from monopyly.database.models import CreditSubtransaction

from test_tag_helpers import TestTagHandler


@pytest.fixture
def mock_transaction():
    mock_transaction = MagicMock()
    return mock_transaction


class TestLinkedTransactionSearch:
    @pytest.mark.parametrize(
        (
            "mock_transaction_id",
            "mock_internal_transaction_id",
            "expected_subtype",
            "expected_transaction_id",
        ),
        [
            (3, 1, "bank", 6),  # --- bank-bank linked transaction
            (6, 1, "bank", 3),
            (5, 2, "credit", 7),  # - credit-bank linked transaction
            (7, 2, "bank", 5),
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


def test_unmatched_transaction_highlighter():
    transactions = [Mock(id=_) for _ in range(1, 5)]
    unmatched_transactions = [Mock(id=_) for _ in range(2, 5)]
    highlighted_transactions = list(
        highlight_unmatched_transactions(transactions, unmatched_transactions)
    )
    assert all(transaction.highlighted for transaction in highlighted_transactions[1:])


@pytest.fixture
def tag_handler(client_context):
    return TransactionTagHandler


class TestTransactionTagHandler(TestTagHandler):
    """Tests for the tag handler."""

    # Redefine references here to allow them to be used by parametrization
    db_reference = TestTagHandler.db_reference
    db_reference_hierarchy = TestTagHandler.db_reference_hierarchy

    def test_tag_depth(self, tag_handler):
        # Top level tags should have a depth of 0
        top_level_tags = tag_handler.get_subtags(None).all()
        assert all(tag.depth == 0 for tag in top_level_tags)
        # Subtags should have appropriate additional depth
        for parent_tag in top_level_tags:
            self._check_subtag_depths(parent_tag)

    def _check_subtag_depths(self, parent_tag):
        for child_tag in parent_tag.children:
            assert child_tag.depth == parent_tag.depth + 1
            self._check_subtag_depths(child_tag)

    @pytest.mark.parametrize(
        ("tag", "expected_subtags"),
        [(db_reference[1], db_reference[2:4]), (db_reference[4], db_reference[5:6])],
    )
    def test_get_subtags(self, tag_handler, tag, expected_subtags):
        subtags = tag_handler.get_subtags(tag)
        self.assert_entries_match(subtags, expected_subtags)

    @pytest.mark.parametrize(
        ("tag", "expected_supertag"),
        [
            (db_reference[2], db_reference[1]),
            (db_reference[3], db_reference[1]),
            (db_reference[5], db_reference[4]),
        ],
    )
    def test_get_supertag(self, tag_handler, tag, expected_supertag):
        supertag = tag_handler.get_supertag(tag)
        self.assert_entry_matches(supertag, expected_supertag)

    @pytest.mark.parametrize(
        ("root_tag", "expected_hierarchy"),
        [
            (None, db_reference_hierarchy),
            (db_reference[0], db_reference_hierarchy[db_reference[0]]),
        ],
    )
    def test_get_hierarchy(self, tag_handler, root_tag, expected_hierarchy):
        hierarchy = tag_handler.get_hierarchy(root_tag)
        self._compare_hierarchies(hierarchy, expected_hierarchy)

    @pytest.mark.parametrize(
        ("tag", "expected_ancestors"),
        [
            (db_reference[2], (db_reference[1],)),
            (db_reference[3], (db_reference[1],)),
            (db_reference[1], ()),
            (db_reference[5], (db_reference[4],)),
        ],
    )
    def test_get_ancestors(self, tag_handler, tag, expected_ancestors):
        ancestors = tag_handler.get_ancestors(tag)
        self.assert_entries_match(ancestors, expected_ancestors)

    @pytest.mark.parametrize(
        ("tag_name", "reference_entry"),
        [("Transportation", db_reference[1]), ("Electricity", db_reference[5])],
    )
    def test_find_tag(self, tag_handler, tag_name, reference_entry):
        tag = tag_handler.find_tag(tag_name)
        self.assert_entry_matches(tag, reference_entry)

    @pytest.mark.parametrize("tag_name", ["Trains", None])
    def test_find_tag_none_exist(self, tag_handler, tag_name):
        tag = tag_handler.find_tag(tag_name)
        assert tag is None


def test_get_subtransactions():
    multiplicity = 3
    transactions = [Mock(subtransactions=[1, 2, 3]) for _ in range(multiplicity)]
    assert get_subtransactions(transactions) == [1, 2, 3] * multiplicity


class TestCategoryTree:
    """Tests for the ``CategoryTree`` object."""

    def test_initialization(self):
        mock_tag = Mock()
        tree = CategoryTree(mock_tag)
        assert tree.category is mock_tag
        assert tree.subtransactions == []
        assert tree.subcategories == {}
        assert tree.subtotal == 0

    def test_add_subcategory(self):
        mock_tag, mock_subtag = Mock(tag_name="tag"), Mock(tag_name="subtag")
        tree = CategoryTree(mock_tag)
        subtree = tree.add_subcategory(mock_subtag)
        assert tree.category is mock_tag
        assert subtree.category is mock_subtag
        assert tree.subcategories["subtag"] is subtree

    def test_subtotal(self):
        mock_tag, mock_subtag = Mock(tag_name="tag"), Mock(tag_name="subtag")
        tree = CategoryTree(mock_tag)
        subtree = tree.add_subcategory(mock_subtag)
        subtotals = {"tree": [10, 20], "subtree": [5, 25]}
        tree.subtransactions = [Mock(subtotal=_) for _ in subtotals["tree"]]
        subtree.subtransactions = [Mock(subtotal=_) for _ in subtotals["subtree"]]
        assert tree.subtotal == sum(subtotals["tree"] + subtotals["subtree"])
        assert subtree.subtotal == sum(subtotals["subtree"])


@pytest.fixture
def root_category_tree():
    # Define the tags
    tag = TestTagHandler.db_reference[1]
    child_tag = TestTagHandler.db_reference[2]
    # Build the testable category tree by hand
    tree = RootCategoryTree()
    tree.subtransactions = [
        CreditSubtransaction(subtotal=10),
        CreditSubtransaction(subtotal=20),
    ]
    tree.subcategories = {tag.tag_name: CategoryTree(tag.tag_name)}
    subtree = tree.subcategories[tag.tag_name]
    subtree.subtransactions = [
        CreditSubtransaction(subtotal=50, tags=[tag]),
        CreditSubtransaction(subtotal=150, tags=[tag]),
    ]
    subtree.subcategories = {child_tag.tag_name: CategoryTree(child_tag.tag_name)}
    subsubtree = subtree.subcategories[child_tag.tag_name]
    subsubtree.subtransactions = [
        CreditSubtransaction(subtotal=3, tags=[tag, child_tag]),
    ]
    return tree


@pytest.fixture
def root_category_tree_chart_data():
    return {
        "labels": ["Transportation", ""],
        "subtotals": [(50 + 150 + 3), (10 + 20)],
    }


class TestRootCategoryTree:
    """Tests for the ``RootCategoryTree`` object."""

    def test_initialization(self):
        tree = RootCategoryTree()
        assert tree.category == "root"
        assert tree.subtransactions == []
        assert tree.subcategories == {}
        assert tree.subtotal == 0

    @pytest.mark.parametrize(
        "mock_tags",
        [
            [Mock(tag_name=f"tag{_}", depth=_) for _ in [0, 1, 2]],
            [Mock(tag_name=f"tag{_}", depth=_) for _ in [1, 0, 2]],
            [Mock(tag_name=f"tag{_}", depth=_) for _ in [2, 1, 0]],
        ],
    )
    def test_categorize_subtransaction(self, mock_tags):
        # Assume that the subtransaction is categorizable based on the given tags
        mock_subtransaction = Mock(subtotal=10, tags=mock_tags, categorizable=True)
        tree = RootCategoryTree()
        tree.categorize_subtransaction(mock_subtransaction)
        assert tree.subtransactions == []
        assert "tag0" in tree.subcategories
        assert "tag1" in tree.subcategories["tag0"].subcategories
        assert "tag2" in tree.subcategories["tag0"].subcategories["tag1"].subcategories

    def test_uncategorizable_subtransaction(self):
        # The set of tags 'Transportation', 'Transportation/Railroad', and 'Gifts'
        # is not categorizable
        uncategorizable_tags = [TestTagHandler.db_reference[_] for _ in [1, 3, 6]]
        subtransaction = CreditSubtransaction(subtotal=10, tags=uncategorizable_tags)
        tree = RootCategoryTree()
        tree.categorize_subtransaction(subtransaction)
        assert tree.subtransactions == [subtransaction]
        assert tree.subcategories == {}

    @pytest.mark.parametrize(
        "extra_subtree",
        [
            None,
            CategoryTree(
                "Exclusion",
                subtransactions=[CreditSubtransaction(subtotal=1_000)],
            ),
            CategoryTree(
                "Zeros",
                subtransactions=[
                    CreditSubtransaction(subtotal=100, note="purchase"),
                    CreditSubtransaction(subtotal=-100, note="return"),
                ],
            ),
        ],
    )
    def test_assemble_chart_data(
        self, root_category_tree, root_category_tree_chart_data, extra_subtree
    ):
        if extra_subtree:
            root_category_tree.subcategories[extra_subtree.category] = extra_subtree
        chart_data = root_category_tree.assemble_chart_data(exclude=["Exclusion"])
        assert chart_data == root_category_tree_chart_data
