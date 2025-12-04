"""Tests for routes in the core blueprint."""

from unittest.mock import patch

from dry_foundation.testing.helpers import TestRoutes


class TestCoreRoutes(TestRoutes):
    def test_index(self, auth):
        # Test that index shows minimal information without login
        self.get_route("/")
        assert "Don't go broke!" in self.soup.find("div", id="homepage-block").text
        assert not self.div_exists(id="homepage-panels")
        # Test index page after login
        auth.login()
        self.get_route("/")
        assert self.div_exists(id="homepage-block")
        assert self.div_exists(id="homepage-panels")

    @patch("monopyly.core.routes.CreditStatementHandler")
    def test_index_no_statements(self, mock_handler, auth):
        # Mock the statement handler to return no statements
        mock_statements = mock_handler.get_statements.return_value
        mock_statements.first.return_value = None
        # Test that statement information is not shown if none exists
        auth.login()
        self.get_route("/")
        credit_panel = self.soup.find("div", id="credit", class_="panel")
        assert "See most recent statement" not in credit_panel.text

    def test_hide_homepage_block(self, auth):
        auth.login()
        self.get_route("/_hide_homepage_block")
        self.get_route("/")
        assert not self.div_exists(id="homepage-block")
        assert self.div_exists(id="homepage-panels")

    def test_hide_homepage_block_logout(self, auth):
        auth.login()
        self.get_route("/_hide_homepage_block")
        self.get_route("/")
        # Logout should reset the homepage block
        auth.logout()
        self.get_route("/")
        assert self.div_exists(id="homepage-block")
        # ...including for subsequent logins
        auth.login()
        self.get_route("/")
        assert self.div_exists(id="homepage-block")
        assert self.div_exists(id="homepage-panels")

    def test_about(self):
        self.get_route("/about")
        assert self.tag_exists("h4", id="tagline", string="The Money Game")

    def test_changelog(self):
        self.get_route("/changelog")
        assert self.tag_exists("h1", string="Changelog")
        assert self.anchor_exists(string="Latest")
        assert self.tag_exists("h2", string="1.0.0")

    def test_story(self, auth):
        auth.login()
        self.get_route("/story")
        assert self.page_heading_includes_substring("Pass go and collect $200")

    def test_credits(self):
        self.get_route("/credits")
        assert self.page_heading_includes_substring("Credits")

    def test_login_required(self, auth):
        self.get_route("/profile")
        assert not self.page_heading_includes_substring("Profile")
        assert not self.tag_exists("h2", string="Settings")
        assert self.page_heading_includes_substring("Redirecting...")
        auth.login()
        self.get_route("/profile")
        assert self.page_heading_includes_substring("Profile")
        assert self.tag_exists("h2", string="Settings")

    def test_settings(self, authorization):
        self.get_route("/profile")
        assert self.page_heading_includes_substring("Profile")
        assert self.tag_exists("h2", string="Settings")
