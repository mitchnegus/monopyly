"""Tests for routes in the credit blueprint."""

import json
import re
from datetime import date
from unittest.mock import Mock, patch

import pytest
from flask import url_for
from fuisce.testing import transaction_lifetime
from werkzeug.exceptions import NotFound

from monopyly.credit.transactions.activity.data import TransactionActivities

from test_helpers import TestRoutes


class TestCreditRoutes(TestRoutes):
    blueprint_prefix = "credit"

    def test_load_cards(self, authorization):
        self.get_route("/cards")
        assert self.page_header_includes_substring("Credit Cards")
        # 3 credit cards for the user; 1 for the 'Add card' button
        assert self.tag_count_is_equal(3 + 1, "a", class_="credit-card-block")

    def test_add_card_get(self, authorization):
        self.get_route("/add_card")
        assert self.page_header_includes_substring("New Card")
        assert self.form_exists(id="card")

    @transaction_lifetime
    def test_add_card_post(self, authorization):
        self.post_route(
            "/add_card",
            data={
                "account_info-account_id": 3,
                "account_info-bank_info-bank_id": -1,
                "last_four_digits": "3337",
                "active": True,
            },
        )
        # Returns the form page again with a prompt asking about card transfers
        assert self.div_exists(class_="overlay")
        assert "Your card has been saved successfully." in self.soup.text
        assert "this new card may be a replacement" in self.soup.text
        assert "(ending in 3336)" in self.soup.text
        assert self.form_exists(action=self.match_substring("_transfer_card_statement"))

    @transaction_lifetime
    def test_add_new_account_card_post(self, authorization):
        self.post_route(
            "/add_card",
            data={
                "account_info-account_id": 0,
                "account_info-bank_info-bank_id": 0,
                "account_info-bank_info-bank_name": "Up My Sleeve, Inc.",
                "account_info-statement_issue_day": 15,
                "account_info-statement_due_day": 10,
                "last_four_digits": "3337",
            },
            follow_redirects=True,
        )
        # Returns the "Credit Account" page for the new account with the card
        assert self.page_header_includes_substring("Credit Account Details")
        # 4 rows with information
        assert self.tag_count_is_equal(4, "div", class_="info-row")
        # 1 credit card for the account (only the new card)
        assert self.tag_count_is_equal(1, "div", class_="credit-card-block")
        digit_tags = self.soup.find_all("div", class_="digits")
        assert any(tag.text == "3337" for tag in digit_tags)

    @patch("monopyly.credit.routes.CardStatementTransferForm")
    @patch("monopyly.credit.routes.transfer_credit_card_statement")
    def test_transfer_statement(
        self, mock_function, mock_form_class, authorization, client_context
    ):
        mock_form = mock_form_class.return_value
        mock_account_id = 100
        mock_card_id = 201
        mock_prior_card_id = 200
        self.post_route(
            "/_transfer_card_statement"
            f"/{mock_account_id}/{mock_card_id}/{mock_prior_card_id}",
            follow_redirects=True,
        )
        mock_function.assert_called_once_with(
            mock_form, mock_card_id, mock_prior_card_id
        )
        assert self.response.request.path == url_for(
            "credit.load_account", account_id=mock_account_id
        )

    def test_load_account(self, authorization):
        self.get_route("/account/2")
        assert self.page_header_includes_substring("Credit Account Details")
        # 4 rows with information
        assert self.tag_count_is_equal(4, "div", class_="info-row")
        # 2 credit cards for the account
        assert self.tag_count_is_equal(2, "div", class_="credit-card-block")

    @transaction_lifetime
    def test_update_card_status(self, authorization):
        self.post_route(
            "/_update_card_status",
            json={
                "card_id": "3",
                "active": False,
            },
        )
        # The formerly active card should now be displayed as inactive
        assert self.div_exists(class_="notice", string="INACTIVE")

    @transaction_lifetime
    def test_delete_card(self, authorization):
        self.get_route("/delete_card/3", follow_redirects=True)
        assert self.page_header_includes_substring("Credit Account Details")
        # 4 rows with information
        assert self.tag_count_is_equal(4, "div", class_="info-row")
        # 1 credit card for the account
        assert self.tag_count_is_equal(1, "div", class_="credit-card-block")
        # Ensure that the card (ending in "3335") was deleted
        digit_tags = self.soup.find_all("div", class_="digits")
        assert not any(tag.text == "3337" for tag in digit_tags)

    @transaction_lifetime
    def test_update_account_statement_issue_day(self, authorization):
        self.post_route("/_update_account_statement_issue_day/3", json="19")
        assert self.response.data == b"19"

    @transaction_lifetime
    def test_update_account_statement_due_day(self, authorization):
        self.post_route("/_update_account_statement_due_day/3", json="11")
        assert self.response.data == b"11"

    @transaction_lifetime
    def test_delete_account(self, authorization):
        self.get_route("/delete_account/2", follow_redirects=True)
        assert self.page_header_includes_substring("Credit Cards")
        # 1 credit card for the user; 1 for the 'Add card' button
        assert self.tag_count_is_equal(1 + 1, "a", class_="credit-card-block")
        # Ensure that the cards associated with the credit account were deleted
        digit_tags = self.soup.find_all("div", class_="digits")
        assert not any(tag.text in ("3334", "3335") for tag in digit_tags)

    def test_load_statements(self, authorization):
        self.get_route("/statements")
        assert self.page_header_includes_substring("Credit Card Statements")
        # 2 active cards with statements for the user
        assert self.tag_count_is_equal(2, "div", class_="card-stack")
        # 5 statements on those active cards
        assert self.tag_count_is_equal(5, "a", class_="statement-block")

    def test_update_statements_display(self, authorization):
        self.post_route(
            "/_update_statements_display",
            json={"card_ids": ["3"]},
        )
        # 1 card shown with the filter applied
        assert self.tag_count_is_equal(1, "div", class_="card-stack")
        # 3 statements on that card
        assert self.tag_count_is_equal(3, "a", class_="statement-block")

    def test_load_statement_details(self, authorization):
        self.get_route("/statement/4")
        assert self.page_header_includes_substring("Statement Details")
        assert self.div_exists(id="statement-summary")
        # 3 transactions in the table on the statement
        assert self.div_exists(class_="transactions-table")
        assert self.tag_count_is_equal(3, "div", class_="transaction")
        for id_ in (5, 6, 7):
            assert self.div_exists(id=f"transaction-{id_}")

    @transaction_lifetime
    def test_update_statement_due_date(self, authorization):
        self.post_route("/_update_statement_due_date/5", json="07/06/2020")
        assert self.response.data == b"2020-07-06"

    @transaction_lifetime
    def test_pay_credit_card(self, authorization):
        self.post_route(
            "/_pay_credit_card/4/7",
            json={
                "payment_amount": "636.33",
                "payment_date": "7/1/2020",
                "payment_bank_account": "2",
            },
        )
        # Returns the template for the summary section of the statement page
        statement_summary, transactions_table = self.soup
        assert statement_summary.find_all("div", id="statement-summary")
        assert statement_summary.find_all("div", string="Paid")
        assert transactions_table.find_all("div", class_="transactions-table")

    def test_reconcile_activity_get(self, authorization):
        self.get_route("/_reconcile_activity/3")
        # Check the result of the GET request
        assert self.div_exists(class_="overlay")
        assert self.div_exists(id="statement-reconciliation")
        assert self.form_exists(action="/credit/reconciliation/3")

    @patch("monopyly.credit.routes.ActivityMatchmaker")
    def test_load_statement_reconciliation_details_get(
        self, mock_matchmaker_cls, client, client_context
    ):
        test_data = [
            ["2020-05-30", 27.00, "The Water Works"],
            ["2020-05-25", 12.34, "Test Merchant 1"],
            ["2020-05-27", 50.00, "Test Merchant 2"],
        ]
        with client.session_transaction() as session:
            session["reconciliation_info"] = (5, test_data)
        activities = TransactionActivities(test_data)
        discrepancies = activities[:1]
        nonmatches = activities[1:]
        mock_matchmaker = mock_matchmaker_cls.return_value
        mock_matchmaker.match_discrepancies = {
            Mock(id=100): activity for activity in discrepancies
        }
        mock_matchmaker.unmatched_activities = nonmatches
        discrepant_amount = activities.total - 26.87
        self.get_route("/reconciliation/5", follow_redirects=True)
        # Check the result of the GET request
        assert self.page_header_includes_substring("Statement Reconciliation")
        assert str(discrepant_amount) in self.soup.find(class_="balance").text
        self._compare_reconciled_activities("discrepant-activity", discrepancies)
        self._compare_reconciled_activities("unrecorded-activity", nonmatches)

    def test_load_statement_reconciliation_details_get_no_data(self, client_context):
        # Get the route without any reconciliation info being set
        self.get_route("/reconciliation/5", follow_redirects=True)
        # Check the result of the GET request
        assert self.page_header_includes_substring("Statement Details")
        assert self.div_exists(id="statement-summary")
        assert self.div_exists(class_="flash", string="ERROR")

    def _compare_reconciled_activities(
        self, discrepancy_category_class, expected_activities
    ):
        activity_tags = self.soup.select(f"div.{discrepancy_category_class}")
        for activity, tag in zip(expected_activities, activity_tags, strict=True):
            assert str(activity.transaction_date) == tag.find(class_="date").text
            assert activity.description == tag.find(class_="text").text
            assert str(activity.total) in tag.find(class_="amount").text

    @patch("monopyly.credit.routes.ActivityMatchmaker")
    @patch("monopyly.credit.routes.parse_transaction_activity_file")
    @patch("flask.Request.files")
    def test_load_statement_reconciliation_details_post(
        self,
        mock_request_files,
        mock_activity_parse_function,
        mock_matchmaker_cls,
        client_context,
    ):
        test_data = [
            ["2020-05-30", 27.00, "The Water Works"],
            ["2020-05-25", 12.34, "Test Merchant 1"],
            ["2020-05-27", 50.00, "Test Merchant 2"],
        ]
        activities = TransactionActivities(test_data)
        discrepancies = activities[:1]
        nonmatches = activities[1:]
        mock_matchmaker = mock_matchmaker_cls.return_value
        mock_matchmaker.match_discrepancies = {
            Mock(id=100): activity for activity in discrepancies
        }
        mock_matchmaker.unmatched_activities = nonmatches
        mock_activity_parse_function.return_value = activities
        discrepant_amount = activities.total - 26.87
        self.post_route("/reconciliation/5", follow_redirects=True)
        # Check the result of the POST request
        mock_request_files.get.assert_called_once()
        assert self.page_header_includes_substring("Statement Reconciliation")
        assert str(discrepant_amount) in self.soup.find(class_="balance").text
        self._compare_reconciled_activities("discrepant-activity", discrepancies)
        self._compare_reconciled_activities("unrecorded-activity", nonmatches)

    @patch("monopyly.credit.routes.parse_transaction_activity_file")
    @patch("flask.Request.files")
    def test_load_statement_reconciliation_details_post_no_data(
        self, mock_request_files, mock_activity_parse_function, client_context
    ):
        mock_activity_parse_function.return_value = None
        self.post_route("/reconciliation/5", follow_redirects=True)
        # Check the result of the POST request
        mock_request_files.get.assert_called_once()
        assert self.page_header_includes_substring("Statement Details")
        assert self.div_exists(id="statement-summary")
        assert self.div_exists(class_="flash", string="ERROR")

    def test_load_user_transactions(self, authorization):
        self.get_route("/transactions")
        assert self.page_header_includes_substring("Credit Transactions")
        # 10 transactions in the table for the user on active cards
        assert self.div_exists(class_="transactions-table")
        assert self.tag_count_is_equal(10, "div", class_="transaction")

    def test_load_card_transactions(self, authorization):
        self.get_route("/transactions/3")
        assert self.page_header_includes_substring("Credit Transactions")
        # 6 transactions in the table for the associated card
        assert self.div_exists(class_="transactions-table")
        assert self.tag_count_is_equal(6, "div", class_="transaction")

    def test_expand_transaction(self, authorization):
        self.post_route("/_expand_transaction", json="4")
        # 2 subtransactions in this transaction
        assert self.tag_count_is_equal(2, "div", class_="subtransaction-details")
        for tag, (note, amount) in zip(
            self.soup.find_all("div", class_="subtransaction-details"),
            [("One for the park", "$30.00"), ("One for the place", "$35.00")],
            strict=True,
        ):
            assert note in tag.find("div", class_="notes").find("span").text
            assert amount in tag.find("div", class_="subtotal").text

    def test_show_linked_bank_transaction(self, authorization):
        self.post_route("/_show_linked_transaction", json={"transaction_id": 7})
        # Show the overlay
        assert self.div_exists(class_="overlay")
        assert self.div_exists(id="linked-transaction-display")
        # The current transaction is a credit transaction
        selected_transaction_tag = self.soup.find(
            "div", class_="linked-transaction selected modal-box"
        )
        assert "JP Morgan Chance" in selected_transaction_tag.text
        assert "Credit Card" in selected_transaction_tag.text
        # The linked transaction is a bank transaction
        linked_transaction_tag = self.soup.find(
            "div", class_="linked-transaction modal-box"
        )
        assert "Jail (5556)" in linked_transaction_tag.text
        assert "Checking" in linked_transaction_tag.text

    def _get_displayed_card_digits(self):
        return [_.text for _ in self.soup.find_all("span", class_="digits")]

    def test_update_transactions_display_card(self, authorization):
        self.post_route(
            "/_update_transactions_display",
            json={"card_ids": ["3"], "sort_order": "asc"},
        )
        # 1 card shown with the filter applied
        displayed_digits = self._get_displayed_card_digits()
        assert all(
            digits not in displayed_digits for digits in ["3333", "3334", "3336"]
        )
        assert all(digits in displayed_digits for digits in ["3335"])
        # 6 transactions on that card
        assert self.tag_count_is_equal(6, "div", class_="transaction")
        # Most recent transactions at the top
        dates = [_.text for _ in self.soup.find_all("span", "numeric-date")]
        assert sorted(dates) == dates

    def test_update_transactions_display_order(self, authorization):
        self.post_route(
            "/_update_transactions_display",
            json={"card_ids": ["3", "4"], "sort_order": "desc"},
        )
        # 2 cards shown with the filter applied
        displayed_digits = self._get_displayed_card_digits()
        assert all(digits not in displayed_digits for digits in ["3333", "3334"])
        assert all(digits in displayed_digits for digits in ["3335", "3336"])
        # 10 transactions for those cards
        assert self.tag_count_is_equal(10, "div", class_="transaction")
        # Most recent transactions at the bottom
        dates = [_.text for _ in self.soup.find_all("span", "numeric-date")]
        assert sorted(dates, reverse=True) == dates

    def test_add_transaction_get(self, authorization):
        self.get_route("/add_transaction")
        assert self.page_header_includes_substring("New Credit Transaction")
        assert self.form_exists(id="credit-transaction")
        assert self.input_exists(value=f"{date.today()}")

    def test_add_transaction_with_merchant_suggestion_get(self, authorization):
        self.get_route("/add_transaction?description=The%20Gardens")
        assert self.page_header_includes_substring("New Credit Transaction")
        assert self.form_exists(id="credit-transaction")
        assert self.div_exists(class_="merchant-suggestion")

    def test_add_card_transaction_get(self, authorization):
        self.get_route("/add_transaction/3")
        assert self.page_header_includes_substring("New Credit Transaction")
        assert self.form_exists(id="credit-transaction")
        # Form should be prepopulated with the card info
        input_id_values = {
            "statement_info-card_info-bank_name": "Jail",
            "statement_info-card_info-last_four_digits": "3335",
        }
        for id_, value in input_id_values.items():
            assert self.input_has_value(value, id=id_)
        assert not self.input_has_value("2020-06-10", id="statement_info-issue_date")

    def test_add_statement_transaction_get(self, authorization):
        self.get_route("/add_transaction/3/5")
        assert self.page_header_includes_substring("New Credit Transaction")
        assert self.form_exists(id="credit-transaction")
        # Form should be prepopulated with the statement info
        input_id_values = {
            "statement_info-card_info-bank_name": "Jail",
            "statement_info-card_info-last_four_digits": "3335",
            "statement_info-issue_date": "2020-06-10",
        }
        for id_, value in input_id_values.items():
            assert self.input_has_value(value, id=id_)

    @transaction_lifetime
    def test_add_transaction_post(self, authorization):
        self.post_route(
            "/add_transaction",
            data={
                "transaction_date": "2020-06-10",
                "statement_info-card_info-bank_name": "TheBank",
                "statement_info-card_info-last_four_digits": "3336",
                "statement_info-issue_date": "2022-06-11",
                "merchant": "body shop",
                "subtransactions-1-subtotal": "250.00",
                "subtransactions-1-note": "New Token",
                "subtransactions-1-tags": "",
            },
        )
        # Move to the transaction submission page
        assert self.page_header_includes_substring("Transaction Submitted")
        assert "The transaction was saved successfully." in self.soup.text
        assert "2020-06-10" in self.soup.text
        assert "$250.00" in self.soup.text
        assert "New Token" in self.soup.text

    @transaction_lifetime
    def test_add_transaction_multiple_subtransactions_post(self, authorization):
        self.post_route(
            "/add_transaction",
            data={
                "transaction_date": "2020-06-10",
                "statement_info-card_info-bank_name": "TheBank",
                "statement_info-card_info-last_four_digits": "3336",
                "statement_info-issue_date": "2022-06-11",
                "merchant": "Body shop",
                "subtransactions-1-subtotal": "250.00",
                "subtransactions-1-note": "New token",
                "subtransactions-1-tags": "",
                "subtransactions-2-subtotal": "1250.00",
                "subtransactions-2-note": "Race car, forever and always",
                "subtransactions-2-tags": "",
            },
        )
        # Move to the transaction submission page
        assert self.page_header_includes_substring("Transaction Submitted")
        assert "The transaction was saved successfully." in self.soup.text
        assert "2020-06-10" in self.soup.text
        assert "$1,500.00" in self.soup.text
        assert "New token" in self.soup.text
        assert "Race car, forever and always" in self.soup.text

    def test_update_transaction_get(self, authorization):
        self.get_route("/update_transaction/8")
        assert self.page_header_includes_substring("Update Credit Transaction")
        assert self.form_exists(id="credit-transaction")
        # Form should be prepopulated with the transaction info
        input_id_values = {
            "statement_info-card_info-bank_name": "Jail",
            "statement_info-card_info-last_four_digits": "3335",
            "transaction_date": "2020-05-30",
            "merchant": "Water Works",
            "statement_info-issue_date": "2020-06-10",
        }
        for id_, value in input_id_values.items():
            assert self.input_has_value(value, id=id_)

    @patch(
        "monopyly.credit.routes.parse_request_transaction_data",
        return_value={
            "transaction_date": date(2020, 5, 31),
            "subtransactions": [{"subtotal": 123}],
            "merchant": "The Water Works",
        },
    )
    def test_update_transaction_suggested_amount_get(self, _, authorization):
        self.get_route("/update_transaction/8")
        assert self.page_header_includes_substring("Update Credit Transaction")
        assert self.form_exists(id="credit-transaction")
        # Form should be prepopulated with the transaction info
        assert self.input_exists(value="Jail")
        assert self.input_exists(value="3335")
        assert self.input_exists(value="2020-05-31")
        assert self.input_exists(value="The Water Works")
        assert self.input_exists(value="2020-06-10")
        assert self.span_exists(class_="suggested-value", string="$123.00")

    @transaction_lifetime
    def test_update_transaction_post(self, authorization):
        self.post_route(
            "/update_transaction/10",
            data={
                "transaction_date": "2020-05-10",
                "statement_info-card_info-last_four_digits": "3336",
                "statement_info-card_info-bank_name": "TheBank",
                "statement_info-issue_date": "2022-06-11",
                "merchant": "Body shop",
                "subtransactions-1-subtotal": "-2345.00",
                "subtransactions-1-note": "Bigger refund",
                "subtransactions-1-tags": "",
            },
        )
        # Move to the transaction submission page
        assert self.page_header_includes_substring("Transaction Updated")
        assert "The transaction was saved successfully." in self.soup.text
        assert "2020-05-10" in self.soup.text
        assert "$-2,345.00" in self.soup.text
        assert "Bigger refund" in self.soup.text

    def test_add_subtransaction_fields(self, authorization):
        self.post_route("/_add_subtransaction_fields", json={"subtransaction_count": 1})
        # Created a second transaction with index 1
        assert self.div_exists(id="subtransactions-1")
        assert self.input_exists(id="subtransactions-1-subtotal")
        assert self.input_exists(id="subtransactions-1-note")
        assert self.input_exists(id="subtransactions-1-tags")

    @transaction_lifetime
    def test_delete_transaction(self, authorization):
        self.get_route("/delete_transaction/9", follow_redirects=True)
        assert self.page_header_includes_substring("Credit Transactions")
        # 9 transactions in the table for the user
        assert self.div_exists(class_="transactions-table")
        assert self.tag_count_is_equal(9, "div", class_="transaction")
        # Ensure that the transaction was deleted
        assert self.div_exists(class_="merchant", string=re.compile(".*Water Works.*"))

    def test_load_tags(self, authorization):
        self.get_route("/tags")
        assert self.page_header_includes_substring("Transaction Tags")
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
        with pytest.raises(ValueError):
            self.post_route(
                "/_add_tag",
                json={"tag_name": "Railroad", "parent": None},
            )

    @transaction_lifetime
    def test_delete_tag(self, authorization):
        self.post_route("/_delete_tag", json={"tag_name": "Railroad"})
        # Returns an empty string
        assert self.response.data == b""

    @pytest.mark.parametrize(
        "field, suggestions",
        [
            ["bank_name", ["TheBank", "Jail"]],
            ["last_four_digits", ["3334", "3335", "3336"]],
            [
                "merchant",
                [
                    "Top Left Corner",
                    "Boardwalk",
                    "Park Place",
                    "Electric Company",
                    "Marvin Gardens",
                    "JP Morgan Chance",
                    "Water Works",
                    "Pennsylvania Avenue",
                    "Income Tax Board",
                    "Reading Railroad",
                    "Community Chest",
                ],
            ],
            [
                "tags",
                [
                    "Transportation",
                    "Utilities",
                    "Electricity",
                    "Parking",
                    "Railroad",
                    "Credit payments",
                    "Gifts",
                ],
            ],
        ],
    )
    def test_suggest_transaction_autocomplete(self, authorization, field, suggestions):
        self.post_route("/_suggest_transaction_autocomplete", json={"field": field})
        # Returned suggestions are not required to be in any particular order
        # (for this test)
        assert sorted(json.loads(self.response.data)) == sorted(suggestions)

    def test_suggest_transaction_note_autocomplete(self, authorization):
        self.post_route(
            "/_suggest_transaction_autocomplete",
            json={"field": "note", "merchant": "Boardwalk"},
        )
        # Returned suggestions should prioritize notes related to the merchant
        top_suggestions = ["Merry-go-round", "Back for more..."]
        other_suggestions = [
            "Parking (thought it was free)",
            "One for the park",
            "One for the place",
            "Electric bill",
            "Expensive real estate",
            "Credit card payment",
            "Tough loss",
            "Big house tour",
            "Refund",
            "Conducting business",
        ]
        response_suggestions = json.loads(self.response.data)
        response_top_suggestions = response_suggestions[: len(top_suggestions)]
        response_other_suggestions = response_suggestions[len(top_suggestions) :]
        assert sorted(response_top_suggestions) == sorted(top_suggestions)
        assert sorted(response_other_suggestions) == sorted(other_suggestions)

    def test_invalid_infer_card_no_info(self, authorization):
        self.post_route("/_infer_card", json={"bank_name": None})
        assert self.response.data == b""

    def test_infer_card_from_bank(self, authorization):
        self.post_route("/_infer_card", json={"bank_name": "Jail"})
        inferred_card_map = {"bank_name": "Jail", "digits": "3335"}
        assert json.loads(self.response.data) == inferred_card_map

    def test_infer_card_from_digits(self, authorization):
        self.post_route("/_infer_card", json={"bank_name": "TheBank", "digits": "3336"})
        inferred_card_map = {"bank_name": "TheBank", "digits": "3336"}
        assert json.loads(self.response.data) == inferred_card_map

    def test_infer_statement_invalid_no_info(self, authorization):
        self.post_route("/_infer_statement", json={"bank_name": None})
        assert self.response.data == b""

    def test_infer_statement_invalid_no_date(self, authorization):
        self.post_route(
            "/_infer_statement", json={"bank_name": "Jail", "digits": "3335"}
        )
        assert self.response.data == b""

    def test_infer_statement_invalid_no_statement(self, authorization):
        self.post_route(
            "/_infer_statement",
            json={
                "bank_name": "Jail",
                "digits": "3335",
                "transaction_date": "2020-06-15",
            },
        )
        assert "No dice!" in self.soup.text

    def test_infer_statement(self, authorization):
        self.post_route(
            "/_infer_statement",
            json={
                "bank_name": "Jail",
                "digits": "3335",
                "transaction_date": "2020-06-05",
            },
        )
        assert self.response.data == b"2020-06-10"
