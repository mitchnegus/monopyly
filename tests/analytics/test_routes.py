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

    def test_show_tag_statistics(self, authorization):
        self.get_route("/tag_statistics")
        assert self.page_heading_includes_substring("Tag Statistics")
        # The page should include a chart
        assert self.div_exists(id="tag-statistics-chart")

    def test_update_tag_statistics_chart(self, authorization):
        self.post_route("/_update_tag_statistics_chart", json=3)
        # Returns chart data with a $1.00 tag subtotal in April 2020 and
        # a $253.99 subtotal in June 2020
        tag_statistics_data_json = (
            "TAG_STATISTICS_CHART_DATA = {"
            '"labels": [1585720800000, 1588312800000, 1590991200000], '
            '"series": [[1.0, 0, 253.99]]}'
        )
        assert tag_statistics_data_json in self.soup.find("script").string
