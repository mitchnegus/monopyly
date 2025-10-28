"""Tests for routes in the analytics blueprint."""

import pytest
from dry_foundation.testing import transaction_lifetime
from dry_foundation.testing.helpers import TestRoutes


class TestAnalyticsRoutes(TestRoutes):
    blueprint_prefix = "analytics"

    def test_load_tags(self, authorization):
        self.get_route("/tags")
        assert self.page_heading_includes_substring("Transaction Tags")
        # 7 tags for the user
        assert self.tag_count_is_equal(7, "div", class_="tag")

    @transaction_lifetime
    def test_add_tag(self, authorization):
        self.post_route(
            "/_add_tag",
            json={"tag_name": "Games", "parent": None},
        )
        # Returns the subtag tree with the new tag added
        tags = self.soup.find_all("div", "tag")
        assert len(tags) == 1
        assert tags[0].text == "Games"

    @transaction_lifetime
    def test_add_tag_with_parent(self, authorization):
        self.post_route(
            "/_add_tag",
            json={"tag_name": "Gas", "parent": "Transportation"},
        )
        # Returns the subtag tree with the new tag added
        tags = self.soup.find_all("div", "tag")
        assert len(tags) == 1
        assert tags[0].text == "Gas"

    @transaction_lifetime
    def test_add_conflicting_tag(self, authorization):
        with pytest.raises(ValueError, match="The given tag name already exists."):
            self.post_route(
                "/_add_tag",
                json={"tag_name": "Railroad", "parent": None},
            )

    @transaction_lifetime
    def test_delete_tag(self, authorization):
        response = self.post_route("/_delete_tag", json={"tag_name": "Railroad"})
        # Returns an empty string
        assert response.data == b""

    @transaction_lifetime
    def test_delete_tag_invalid(self, authorization):
        self.post_route("/_delete_tag", json={"tag_name": "Credit payments"})
        assert all(_ in self.soup.text for _ in ("No dice!", "403", "Forbidden"))
