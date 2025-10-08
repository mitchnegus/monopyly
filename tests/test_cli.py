"""Tests for the Monopyly CLI interface."""

from unittest.mock import patch

import monopyly


@patch("monopyly.interact")
def test_entrypoint(mock_interact_method):
    monopyly.main()
    mock_interact_method.assert_called_once_with("monopyly")
