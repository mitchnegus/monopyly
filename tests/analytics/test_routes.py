"""Tests for routes in the analytics blueprint."""

from datetime import date, datetime
from unittest.mock import patch

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
        with patch("monopyly.analytics.tools.date") as mock_date:
            mock_date.today.return_value = date(2020, 6, 30)
            mock_date.side_effect = lambda *args, **kwargs: date(*args, **kwargs)
            self.post_route("/_update_tag_statistics_chart", json=3)
        # Returns chart data with a $1.00 tag subtotal in April 2020 and
        # a $253.99 subtotal in June 2020
        timestamp_labels = [
            str(int(datetime(2020, month, 1, 0, 0, 0).timestamp() * 1000))
            for month in (4, 5, 6)
        ]
        tag_statistics_data_json = (
            "TAG_STATISTICS_CHART_DATA = {"
            f'"labels": [{", ".join(timestamp_labels)}], '
            '"series": [[1.0, 0, 253.99]]}'
        )
        assert tag_statistics_data_json in self.soup.find("script").string

    def test_show_net_worth(self, authorization):
        # Get expected values for the user (i.e., count bank accounts and active cards)
        expected_net_worth_value = 234.69 + (-7262.20)
        expected_bank_account_count = 3
        expected_credit_card_count = 2
        # Load the net worth page and extract values
        self.get_route("/net_worth")
        net_worth_text = self.soup.find("div", id="net-worth-total").get_text()
        bank_account_subtotals = self.soup.find("div", id="bank-account-subtotal-stack")
        bank_account_count = len(
            bank_account_subtotals.find_all("a", class_="account-subtotal-block")
        )
        credit_card_subtotals = self.soup.find("div", id="credit-card-subtotal-stack")
        credit_card_count = len(
            credit_card_subtotals.find_all("a", class_="account-subtotal-block")
        )
        # Ensure expectation matches reality
        assert "$" in net_worth_text
        assert str(expected_net_worth_value) in net_worth_text.replace(",", "")
        assert bank_account_count == expected_bank_account_count
        assert credit_card_count == expected_credit_card_count
