"""Tests for the actions commonly shared among blueprints."""
from unittest.mock import Mock, MagicMock

import pytest

from monopyly.common.actions import *


def test_get_user_database_entries():
    mock_handler_type = Mock()
    mock_db = mock_handler_type.return_value
    mock_db.get_entries.return_value = 'test entries'
    entries = get_user_database_entries(mock_handler_type)
    mock_db.get_entries.assert_called_once()
    assert entries == 'test entries'


@pytest.mark.parametrize('fields', [None, ('test_field_1', 'test_field_2')])
def test_get_groupings(fields):
    mock_entries = [MagicMock(), MagicMock()]
    mock_grouped_entries = [MagicMock(), MagicMock()]
    mock_handler_type = Mock()
    mock_db = mock_handler_type.return_value
    mock_db.get_entries.return_value = mock_grouped_entries
    groupings = get_groupings(mock_entries, mock_db, fields=fields)
    assert groupings == {entry: mock_grouped_entries for entry in mock_entries}


@pytest.mark.parametrize(
    'return_field, expected_value',
    [[None, None],
     ['test_field', 'test_value']]
)
def test_delete_database_entry(return_field, expected_value):
    mock_handler_type, entry_id = MagicMock(), Mock()
    mock_db = mock_handler_type.return_value
    if return_field:
        mock_db.get_entry.return_value = {return_field: expected_value}
    value = delete_database_entry(mock_handler_type, entry_id, return_field)
    mock_db.delete_entries.assert_called_once_with((entry_id,))
    assert value == expected_value

