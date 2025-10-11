"""Tests for the actions performed by the analytics blueprint."""

from datetime import datetime
from unittest.mock import Mock

import pytest

from monopyly.analytics.actions import get_tag_statistics_chart_data
from monopyly.common.transactions import TransactionTagHandler


@pytest.fixture
def tags(client_context):
    """Get all top-level tags in the hierarchy from the test database."""
    return list(TransactionTagHandler.get_hierarchy().keys())


def test_get_tag_statistics_chart_data(tags):
    chart_data = get_tag_statistics_chart_data(tags)
    expected_labels = [
        datetime(y, m, d).timestamp() * 1000
        for y, m, d in [(2020, 4, 1), (2020, 5, 1), (2020, 6, 1)]
    ]
    expected_monthly_amounts = [
        # Utilities
        # - electric bill payment on 2020-04-25
        [99, 0, 0],
        # Transportation
        # - parking charge on 2020-04-13
        # - railroad ticket on 2020-06-05
        [1, 0, 253.99],
        # Credit payments
        # - bank and credit payments balance each other out
        [0, 0, 0],
        # Gifts
        [0, 0, 0],
    ]
    assert chart_data["labels"] == expected_labels
    assert chart_data["series"] == expected_monthly_amounts


@pytest.mark.parametrize(
    ("mock_tags", "limit", "exception"),
    [
        # Empty tag list
        ([], 5, ValueError),
        # Invalid tag limit value
        ([Mock()], -1, ValueError),
        # A tag with invalid subtransactions types
        ([Mock(subtransactions=[Mock(transaction_view=Mock())])], 5, TypeError),
    ],
)
def test_get_tag_statistics_chart_data_invalid(mock_tags, limit, exception):
    with pytest.raises(exception):
        get_tag_statistics_chart_data(mock_tags, limit=limit)
