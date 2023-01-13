"""Tests for routes in the core blueprint."""
from unittest.mock import patch

from ..helpers import TestRoutes


class TestCoreRoutes(TestRoutes):

    def test_index(self, auth):
        # Test that index shows minimal information without login
        self.get_route("/")
        assert "Don't go broke!" in self.html
        assert "homepage-panels" not in self.html
        # Test index page after login
        auth.login()
        self.get_route("/")
        assert "Don't go broke!" in self.html
        assert "homepage-panels" in self.html

    @patch("monopyly.core.routes.CreditStatementHandler")
    def test_index_no_statements(self, mock_handler, auth):
        # Mock the statement handler to return no statements
        mock_statements = mock_handler.get_statements.return_value
        mock_statements.first.return_value = None
        mock_last_statement = mock_statements.first.return_value
        # Test that statement information is not shown if none exists
        auth.login()
        self.get_route("/")
        assert "See most recent statement" not in self.html

    def test_about(self):
        self.get_route("/about")
        assert "<h1>Pass go and collect $200</h1>" in self.html

    def test_credits(self):
        self.get_route("/credits")
        assert "<h1>Credits</h1>" in self.html

    def test_login_required(self, auth):
        self.get_route("/settings")
        assert "Settings" not in self.html
        assert "Redirecting..." in self.html
        auth.login()
        self.get_route("/settings")
        assert "Settings" in self.html

    def test_settings(self, authorization):
        self.get_route("/settings")
        assert "Settings coming soon..." in self.html

