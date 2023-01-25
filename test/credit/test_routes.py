"""Tests for routes in the credit blueprint."""
import json
from unittest.mock import patch, Mock

import pytest
from flask import url_for
from werkzeug.exceptions import NotFound

from ..helpers import transaction_lifetime, TestRoutes


class TestCreditRoutes(TestRoutes):

    blueprint_prefix = "credit"

    def test_load_cards(self, authorization):
        self.get_route("/cards")
        assert "Credit Cards" in self.html
        # 3 credit cards for the user; 1 for the 'Add card' button
        assert self.html.count("credit-card-block") == (3 + 1)

    def test_add_card_get(self, authorization):
        self.get_route("/add_card")
        assert "New Card" in self.html
        assert '<form id="card"' in self.html

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
        assert "overlay" in self.html
        assert "Your card has been saved successfully." in self.html
        assert "this new card may be a replacement" in self.html
        assert "(ending in 3336)" in self.html
        assert "_transfer_card_statement" in self.html

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
        assert "Credit Account Details" in self.html
        # 4 rows with information
        assert self.html.count("info-row") == 4
        # 1 credit card for the account (only the new card)
        assert self.html.count("credit-card-block") == 1
        assert "3337" in self.html

    @patch("monopyly.credit.routes.CardStatementTransferForm")
    @patch("monopyly.credit.routes.transfer_credit_card_statement")
    def test_transfer_statement(self, mock_function, mock_form_class,
                                authorization, client_context):
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
            'credit.load_account', account_id=mock_account_id
        )

    def test_load_account(self, authorization):
        self.get_route("/account/2")
        assert "Credit Account Details" in self.html
        # 4 rows with information
        assert self.html.count("info-row") == 4
        # 2 credit cards for the account
        assert self.html.count("credit-card-block") == 2

    @transaction_lifetime
    def test_update_card_status(self, authorization):
        self.post_route(
            "/_update_card_status",
            json={
                "input_id": "card-3-status",
                "active": False,
            },
        )
        # The formerly active card should now be displayed as inactive
        assert "INACTIVE" in self.html

    @transaction_lifetime
    def test_delete_card(self, authorization):
        self.get_route("/delete_card/3", follow_redirects=True)
        assert "Credit Account Details" in self.html
        # 4 rows with information
        assert self.html.count("info-row") == 4
        # 1 credit card for the account
        assert self.html.count("credit-card-block") == 1
        # Ensure that the card (ending in "3335") was deleted
        assert "3335" not in self.html

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
        assert "Credit Cards" in self.html
        # 1 credit card for the user; 1 for the 'Add card' button
        assert self.html.count("credit-card-block") == (1 + 1)
        # Ensure that the cards associated with the credit account were deleted
        assert "3334" not in self.html
        assert "3335" not in self.html

    def test_load_statements(self, authorization):
        self.get_route("/statements")
        assert "Credit Card Statements" in self.html
        # 2 active cards with statements for the user
        assert self.html.count("card-column") == 2
        # 5 statements on those active cards
        assert self.html.count("statement-block ") == 5

    def test_update_statements_display(self, authorization):
        self.post_route(
            "/_update_statements_display",
            json={"filter_ids": ["Jail-3335"]},
        )
        # 1 card shown with the filter applied
        assert self.html.count("card-column") == 1
        # 3 statements on that card
        assert self.html.count("statement-block ") == 3

    def test_load_statement_details(self, authorization):
        self.get_route("/statement/4")
        assert "Statement Details" in self.html
        assert "statement-summary" in self.html
        # 3 transactions in the table on the statement
        assert "transactions-table" in self.html
        assert self.html.count('class="transaction ') == 3
        for id_ in (5, 6, 7):
            assert f"transaction-{id_}" in self.html

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
        assert "statement-summary" in self.html
        assert "PAID" in self.html

    def test_load_user_transactions(self, authorization):
        self.get_route("/transactions")
        assert "Credit Transactions" in self.html
        # 10 transactions in the table for the user on active cards
        assert "transactions-table" in self.html
        assert self.html.count('class="transaction ') == 10

    def test_load_card_transactions(self, authorization):
        self.get_route("/transactions/3")
        assert "Credit Transactions" in self.html
        # 6 transactions in the table for the associated card
        assert "transactions-table" in self.html
        assert self.html.count('class="transaction ') == 6

    def test_expand_transaction(self, authorization):
        self.post_route("/_expand_transaction", json="transaction-4")
        # 2 subtransactions in this transaction
        assert self.html.count("subtransaction-details") == 2
        assert "One for the park" in self.html
        assert "$30.00" in self.html
        assert "One for the place" in self.html
        assert "$35.00" in self.html

    def test_show_linked_bank_transaction(self, authorization):
        self.post_route(
            "/_show_linked_transaction", json={"transaction_id": 7}
        )
        # Show the overlay
        assert "overlay" in self.html
        assert "linked-transaction-display" in self.html
        # The current transaction is a credit transaction
        assert "JP Morgan Chance" in self.html
        assert "Credit Card" in self.html
        # The linked transaction is a bank transaction
        assert "Jail (5556)" in self.html
        assert "Checking" in self.html

    def test_update_transactions_display_card(self, authorization):
        self.post_route(
            "/_update_transactions_display",
            json={
                "filter_ids": ["Jail-3335"],
                "sort_order": "asc"},
        )
        # 1 card shown with the filter applied
        assert all(_ not in self.html for _ in ["3333", "3334", "3336"])
        assert all(_ in self.html for _ in ["3335"])
        # 6 transactions on that card
        assert self.html.count('id="transaction-') == 6
        # Most recent transactions at the top
        dates = [_.text for _ in self.soup.find_all("span", "numeric-date")]
        assert sorted(dates) == dates

    def test_update_transactions_display_order(self, authorization):
        self.post_route(
            "/_update_transactions_display",
            json={
                "filter_ids": ["Jail-3335", "TheBank-3336"],
                "sort_order": "desc"},
        )
        # 2 cards shown with the filter applied
        assert all(_ not in self.html for _ in ["3333", "3334"])
        assert all(_ in self.html for _ in ["3335", "3336"])
        # 10 transactions for those cards
        assert self.html.count('id="transaction-') == 10
        # Most recent transactions at the bottom
        dates = [_.text for _ in self.soup.find_all("span", "numeric-date")]
        assert sorted(dates, reverse=True) == dates

    def test_add_transaction_get(self, authorization):
        self.get_route("/add_transaction")
        assert "New Credit Transaction" in self.html
        assert '<form id="credit-transaction"' in self.html

    def test_add_card_transaction_get(self, authorization):
        self.get_route("/add_transaction/3")
        assert "New Credit Transaction" in self.html
        assert '<form id="credit-transaction"' in self.html
        # Form should be prepopulated with the card info
        assert 'value="Jail"' in self.html
        assert 'value="3335"' in self.html
        assert 'value="2020-06-10"' not in self.html

    def test_add_statement_transaction_get(self, authorization):
        self.get_route("/add_transaction/3/5")
        assert "New Credit Transaction" in self.html
        assert '<form id="credit-transaction"' in self.html
        # Form should be prepopulated with the statement info
        assert 'value="Jail"' in self.html
        assert 'value="3335"' in self.html
        assert 'value="2020-06-10"' in self.html

    @transaction_lifetime
    def test_add_transaction_post(self, authorization):
        self.post_route(
            "/add_transaction",
            data={
                "transaction_date": "2020-06-10",
                "statement_info-card_info-bank_name": "TheBank",
                "statement_info-card_info-last_four_digits": "3336",
                "statement_info-issue_date": "2022-06-11",
                "vendor": "body shop",
                "subtransactions-1-subtotal": "250.00",
                "subtransactions-1-note": "New Token",
                "subtransactions-1-tags": "",
            },
        )
        # Move to the transaction submission page
        assert "Transaction Submitted" in self.html
        assert "The transaction was saved successfully." in self.html
        assert "2020-06-10" in self.html
        assert "$250.00" in self.html
        assert "New Token" in self.html

    @transaction_lifetime
    def test_add_transaction_multiple_subtransactions_post(
        self, authorization
    ):
        self.post_route(
            "/add_transaction",
            data={
                "transaction_date": "2020-06-10",
                "statement_info-card_info-bank_name": "TheBank",
                "statement_info-card_info-last_four_digits": "3336",
                "statement_info-issue_date": "2022-06-11",
                "vendor": "Body shop",
                "subtransactions-1-subtotal": "250.00",
                "subtransactions-1-note": "New token",
                "subtransactions-1-tags": "",
                "subtransactions-2-subtotal": "1250.00",
                "subtransactions-2-note": "Race car, forever and always",
                "subtransactions-2-tags": "",
            },
        )
        # Move to the transaction submission page
        assert "Transaction Submitted" in self.html
        assert "The transaction was saved successfully." in self.html
        assert "2020-06-10" in self.html
        assert "$1,500.00" in self.html
        assert "New token" in self.html
        assert "Race car, forever and always" in self.html

    def test_update_transaction_get(self, authorization):
        self.get_route("/update_transaction/8")
        assert "Update Credit Transaction" in self.html
        assert '<form id="credit-transaction"' in self.html
        # Form should be prepopulated with the transaction info
        assert 'value="Jail"' in self.html
        assert 'value="3335"' in self.html
        assert 'value="2020-05-30"' in self.html
        assert 'value="Water Works"' in self.html
        assert 'value="2020-06-10"' in self.html

    @transaction_lifetime
    def test_update_transaction_post(self, authorization):
        self.post_route(
            "/update_transaction/10",
            data={
                "transaction_date": "2020-05-10",
                "statement_info-card_info-last_four_digits": "3336",
                "statement_info-card_info-bank_name": "TheBank",
                "statement_info-issue_date": "2022-06-11",
                "vendor": "Body shop",
                "subtransactions-1-subtotal": "-2345.00",
                "subtransactions-1-note": "Bigger refund",
                "subtransactions-1-tags": "",
            },
        )
        # Move to the transaction submission page
        assert "Transaction Updated" in self.html
        assert "The transaction was saved successfully." in self.html
        assert "2020-05-10" in self.html
        assert "$-2,345.00" in self.html
        assert "Bigger refund" in self.html

    def test_add_subtransaction_fields(self, authorization):
        self.post_route(
            "/_add_subtransaction_fields",
            json={"subtransaction_count": 1}
        )
        assert 'id="subtransactions-2"' in self.html
        assert "subtransactions-2-subtotal" in self.html
        assert "subtransactions-2-note" in self.html
        assert "subtransactions-2-tags" in self.html

    @transaction_lifetime
    def test_delete_transaction(self, authorization):
        self.get_route("/delete_transaction/8", follow_redirects=True)
        assert "Credit Transactions" in self.html
        # 9 transactions in the table for the user
        assert "transactions-table" in self.html
        assert self.html.count('class="transaction ') == 9
        # Ensure that the transaction was deleted
        assert "Water Works" not in self.html

    def test_load_tags(self, authorization):
        self.get_route("/tags")
        assert "Transaction Tags" in self.html
        # 5 tags for the user
        assert self.html.count('class="tag"') == 5

    @transaction_lifetime
    def test_add_tag(self, authorization):
        self.post_route(
            "/_add_tag", json={"tag_name": "Games", "parent": None},
        )
        # Returns the subtag tree with the new tag added
        tags = self.soup.find_all("div", "tag")
        assert len(tags) == 1
        assert tags[0].text == "Games"

    @transaction_lifetime
    def test_add_tag_with_parent(self, authorization):
        self.post_route(
            "/_add_tag", json={"tag_name": "Gas", "parent": "Transportation"},
        )
        # Returns the subtag tree with the new tag added
        tags = self.soup.find_all("div", "tag")
        assert len(tags) == 1
        assert tags[0].text == "Gas"

    @transaction_lifetime
    def test_add_conflicting_tag(self, authorization):
        with pytest.raises(ValueError):
            self.post_route(
                "/_add_tag", json={"tag_name": "Railroad", "parent": None},
            )

    @transaction_lifetime
    def test_delete_tag(self, authorization):
        self.post_route("/_delete_tag", json={"tag_name": "Railroad"})
        # Returns an empty string
        assert self.response.data == b""

    @pytest.mark.parametrize(
        "field, suggestions",
        [["bank_name", ["TheBank", "Jail"]],
         ["last_four_digits", ["3334", "3335", "3336"]],
         ["vendor",
          ["Top Left Corner", "Boardwalk", "Park Place", "Electric Company",
           "Marvin Gardens", "JP Morgan Chance", "Water Works",
           "Pennsylvania Avenue", "Income Tax Board", "Reading Railroad",
           "Community Chest"]]]
    )
    def test_suggest_transaction_autocomplete(self, authorization, field,
                                              suggestions):
        self.post_route(
            "/_suggest_transaction_autocomplete", json={"field": field}
        )
        # Returned suggestions are not required to be in any particular order
        # (for this test)
        assert sorted(json.loads(self.response.data)) == sorted(suggestions)

    def test_suggest_transaction_note_autocomplete(self, authorization):
        self.post_route(
            "/_suggest_transaction_autocomplete",
            json={"field": "note", "vendor": "Boardwalk"}
        )
        # Returned suggestions should prioritize notes related to the vendor
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
        response_top_suggestions = response_suggestions[:len(top_suggestions)]
        response_other_suggestions = response_suggestions[len(top_suggestions):]
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
        self.post_route(
            "/_infer_card", json={"bank_name": "TheBank", "digits": "3336"}
        )
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
        assert "404 Not Found" in self.html

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

