"""Tests for routes in the core blueprint."""
from unittest.mock import patch


def test_index(client, auth):
    # Test that index shows minimal information without login
    response = client.get("/")
    assert b"Don't go broke!" in response.data
    assert b"homepage-panels" not in response.data
    # Test index page after login
    auth.login()
    response = client.get("/")
    assert b"Don't go broke!" in response.data
    assert b"homepage-panels" in response.data


@patch("monopyly.core.routes.CreditStatementHandler")
def test_index_no_statements(mock_handler, client, auth):
    # Mock the statement handler to return no statements
    mock_statements = mock_handler.get_statements.return_value
    mock_statements.first.return_value = None
    mock_last_statement = mock_statements.first.return_value
    # Test that statement information is not shown if none exists
    auth.login()
    response = client.get("/")
    assert b"See most recent statement" not in response.data


def test_about(client):
    response = client.get("/about")
    assert b"<h1>Pass go and collect $200</h1>" in response.data


def test_credits(client):
    response = client.get("/credits")
    assert b"<h1>Credits</h1>" in response.data


def test_login_required(client, auth):
    response = client.get("/settings")
    assert b"Settings" not in response.data
    assert b"Redirecting..." in response.data
    auth.login()
    response = client.get("/settings")
    assert b"Settings" in response.data


def test_settings(client, authorization):
    response = client.get("/settings")
    assert b"Settings coming soon..." in response.data
