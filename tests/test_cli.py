"""Tests for the Monopyly CLI interface."""

from unittest.mock import patch

import monopyly


@patch("monopyly.interact")
def test_entrypoint(mock_interact_method):
    monopyly.main()
    assert mock_interact_method.called_once_with("monopyly")
