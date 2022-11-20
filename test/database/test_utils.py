"""Tests for the database utilities."""
from contextlib import nullcontext as does_not_raise

import pytest

from monopyly.database.utils import validate_sort_order


@pytest.mark.parametrize(
    'sort_order, expectation',
    [['ASC', does_not_raise()],
     ['DESC', does_not_raise()],
     ['test', pytest.raises(ValueError)]]
)
def test_validate_sort_order(sort_order, expectation):
    with expectation:
        validate_sort_order(sort_order)

