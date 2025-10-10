"""Tests for routes in the banking blueprint."""

import json
from datetime import date
from unittest.mock import patch

import pytest
from dry_foundation.testing import transaction_lifetime

from test_helpers import TestRoutes


class TestBankingRoutes(TestRoutes):
    blueprint_prefix = "banking"

    def test_load_accounts(self, authorization):
        self.get_route("/accounts")
        assert self.page_header_includes_substring("Bank Accounts")
        # 2 banks for the user, with 3 total accounts
        assert self.tag_count_is_equal(2, "div", class_="bank-stack")
        assert self.tag_count_is_equal(3, "div", class_="account-block")

    def test_add_account_get(self, authorization):
        self.get_route("/add_account")
        assert self.page_header_includes_substring("New Bank Account")
        assert self.form_exists(id="bank-account")

    def test_add_bank_account_get(self, authorization):
        self.get_route("/add_account/2")
        assert self.page_header_includes_substring("New Bank Account")
        assert self.form_exists(id="bank-account")
        # Form should be prepopulated with the bank info
        assert self.input_has_value("Jail", id="bank_info-bank_name")

    @transaction_lifetime
    def test_add_account_post(self, authorization):
        self.post_route(
            "/add_account",
            data={
                "bank_info-bank_id": 2,
                "account_type_info-account_type_id": 3,
                "last_four_digits": "8888",
            },
            follow_redirects=True,
        )
        # Returns the "Bank Accounts" page with the new account added
        assert self.page_header_includes_substring("Bank Accounts")
        assert self.tag_count_is_equal(2, "div", class_="bank-stack")
        assert self.tag_count_is_equal(4, "div", class_="account-block")
        digit_tags = self.soup.find_all("span", class_="digits")
        assert any(tag.text == "8888" for tag in digit_tags)

    @transaction_lifetime
    def test_add_new_bank_account_post(self, authorization):
        self.post_route(
            "/add_account",
            data={
                "bank_info-bank_id": 0,
                "bank_info-bank_name": "Up My Sleeve, Inc",
                "account_type_info-account_type_id": 3,
                "last_four_digits": "8888",
            },
            follow_redirects=True,
        )
        # Returns the "Bank Accounts" page with the new account added
        assert self.page_header_includes_substring("Bank Accounts")
        assert self.tag_count_is_equal(3, "div", class_="bank-stack")
        assert self.tag_count_is_equal(4, "div", class_="account-block")
        digit_tags = self.soup.find_all("span", class_="digits")
        assert any(tag.text == "8888" for tag in digit_tags)

    @transaction_lifetime
    def test_delete_account(self, authorization):
        self.get_route("/delete_account/3", follow_redirects=True)
        assert self.page_header_includes_substring("Bank Accounts")
        # 2 banks for the user, with 2 total accounts
        assert self.tag_count_is_equal(2, "div", class_="bank-stack")
        assert self.tag_count_is_equal(2, "div", class_="account-block")

    def test_load_account_summaries(self, authorization):
        self.get_route("/account_summaries/2")
        assert self.page_header_includes_substring("Bank Account Summaries")
        # 2 accounts (1 checking, 1 savings)
        total_balance = 42.00 + 43.00 + 300 + 58.90 - 109.21 - 300
        assert self.tag_exists("h2", class_="bank", string="Jail")
        assert self.tag_exists("h3", class_="balance", string=f"${total_balance:,.2f}")
        self.tag_count_is_equal(2, "div", class_="account-type-stack")
        self.tag_count_is_equal(2, "span", class_="stack-title-info", string="5556")
        self.tag_count_is_equal(1, "b", string="Savings")
        self.tag_count_is_equal(1, "b", string="Checking")

    def test_load_account_details(self, authorization):
        self.get_route("/account/2")
        assert self.page_header_includes_substring("Account Details")
        assert self.div_exists(id="account-summary")
        # 3 transactions in the table for the account
        assert self.div_exists(class_="transactions-table")
        assert self.tag_count_is_equal(3, "div", class_="transaction")
        for id_ in (2, 3, 4):
            assert self.div_exists(id=f"transaction-{id_}")
        assert self.div_exists(id="balance-chart")

    def test_load_more_card_transactions(self, authorization):
        transaction_limit = 2
        with patch("monopyly.banking.routes.TRANSACTION_LIMIT", new=transaction_limit):
            self.post_route(
                "/_extra_transactions",
                json={"account_id": 2, "block_count": 2},
            )
        transaction_notes = [_.text for _ in self.soup.find_all("div", class_="notes")]
        expected_notes = ["Jail subtransaction 1", "Jail subtransaction 2"]
        for expected_note in expected_notes:
            assert any(expected_note in note for note in transaction_notes)
        assert len(transaction_notes) == 1  # only 1 extra transaction left

    def test_expand_transaction(self, authorization):
        self.post_route("/_expand_transaction", json="5")
        # 1 subtransaction in this transaction
        assert self.tag_count_is_equal(1, "div", class_="subtransaction-details")
        assert self.span_exists(string="Credit card payment")
        assert "$-109.21" in self.soup.find("div", class_="subtotal").text

    def test_show_linked_bank_transaction(self, authorization):
        self.post_route("/_show_linked_transaction", json={"transaction_id": 6})
        # Show the overlay
        assert self.div_exists(class_="overlay")
        assert self.div_exists(id="linked-transaction-display")
        # The current transaction is a bank transaction
        selected_transaction_tag = self.soup.find(
            "div", class_="linked-transaction selected modal-box"
        )
        assert "Jail (5556)" in selected_transaction_tag.text
        assert "Checking" in selected_transaction_tag.text
        # The linked transaction is also a bank transaction
        linked_transaction_tag = self.soup.find(
            "div", class_="linked-transaction modal-box"
        )
        assert "Jail (5556)" in linked_transaction_tag.text
        assert "Savings" in linked_transaction_tag.text

    def test_show_linked_credit_transaction(self, authorization):
        self.post_route("/_show_linked_transaction", json={"transaction_id": 5})
        # Show the overlay
        assert self.div_exists(class_="overlay")
        assert self.div_exists(id="linked-transaction-display")
        # The current transaction is a bank transaction
        selected_transaction_tag = self.soup.find(
            "div", class_="linked-transaction selected modal-box"
        )
        assert "Jail (5556)" in selected_transaction_tag.text
        assert "Checking" in selected_transaction_tag.text
        # The linked transaction is a credit transaction
        linked_transaction_tag = self.soup.find(
            "div", class_="linked-transaction modal-box"
        )
        assert "JP Morgan Chance" in linked_transaction_tag.text
        assert "Credit Card" in linked_transaction_tag.text

    def test_add_transaction_get(self, authorization):
        self.get_route("/add_transaction")
        assert self.page_header_includes_substring("New Bank Transaction")
        assert self.form_exists(id="bank-transaction")
        assert self.input_exists(value=f"{date.today()}")

    def test_add_bank_transaction_get(self, authorization):
        self.get_route("/add_transaction/2")
        assert self.page_header_includes_substring("New Bank Transaction")
        assert self.form_exists(id="bank-transaction")
        # Form should be prepopulated with the bank info
        assert self.input_has_value("Jail", id="account_info-bank_name")
        assert not self.input_has_value("5556", id="account_info-last_four_digits")

    def test_add_account_transaction_get(self, authorization):
        self.get_route("/add_transaction/2/3")
        assert self.page_header_includes_substring("New Bank Transaction")
        assert self.form_exists(id="bank-transaction")
        # Form should be prepopulated with the account info
        assert self.input_has_value("Jail", id="account_info-bank_name")
        assert self.input_has_value("5556", id="account_info-last_four_digits")

    @transaction_lifetime
    def test_add_transaction_post(self, authorization):
        self.post_route(
            "/add_transaction",
            data={
                "transaction_date": "2022-01-19",
                "account_info-last_four_digits": "5556",
                "account_info-type_name": "Savings",
                "subtransactions-1-subtotal": "-505.00",
                "subtransactions-1-note": "7 hour flight, 45 minute drive",
                "subtransactions-1-tags": "Transportation",
            },
            follow_redirects=True,
        )
        # Returns to the "Account Details" page with the new transaction added
        assert self.page_header_includes_substring("Account Details")
        assert self.div_exists(id="account-summary")
        # 4 transactions in the table for the account
        assert self.div_exists(class_="transactions-table")
        assert self.tag_count_is_equal(4, "div", class_="transaction")
        for id_ in (2, 3, 4, 8):
            assert self.div_exists(id=f"transaction-{id_}")

    @transaction_lifetime
    def test_add_transaction_multiple_subtransactions_post(self, authorization):
        self.post_route(
            "/add_transaction",
            data={
                "transaction_date": "2022-01-19",
                "account_info-last_four_digits": "5556",
                "account_info-type_name": "Savings",
                "subtransactions-1-subtotal": "-505.00",
                "subtransactions-1-note": "7 hour flight, 45 minute drive",
                "subtransactions-1-tags": "Transportation",
                "subtransactions-2-subtotal": "0.80",
                "subtransactions-2-note": "Rave reviews",
                "subtransactions-2-tags": "",
                "subtransactions-3-subtotal": "70.70",
                "subtransactions-3-note": "Easy money",
                "subtransactions-3-tags": "",
            },
            follow_redirects=True,
        )
        # Returns to the "Account Details" page with the new transaction added
        assert self.page_header_includes_substring("Account Details")
        assert self.div_exists(id="account-summary")
        # 4 transactions in the table for the account
        assert self.div_exists(class_="transactions-table")
        assert self.tag_count_is_equal(4, "div", class_="transaction")
        for id_ in (2, 3, 4, 8):
            assert self.div_exists(id=f"transaction-{id_}")

    def test_update_transaction_get(self, authorization):
        self.get_route("/update_transaction/4")
        assert self.page_header_includes_substring("Update Bank Transaction")
        assert self.form_exists(id="bank-transaction")
        # Form should be prepopulated with the transaction info
        input_id_values = {
            "account_info-bank_name": "Jail",
            "account_info-last_four_digits": "5556",
            "transaction_date": "2020-05-06",
            "subtransactions-0-note": "What else is there to do in Jail?",
        }
        for id_, value in input_id_values.items():
            assert self.input_has_value(value, id=id_)

    @transaction_lifetime
    def test_update_transaction_post(self, authorization):
        self.post_route(
            "/update_transaction/7",
            data={
                "transaction_date": "2020-05-06",
                "account_info-last_four_digits": "5557",
                "account_info-type_name": "Certificate of Deposit",
                "subtransactions-1-subtotal": "0.01",
                "subtransactions-1-note": "Do not pass GO, do not collect $200",
                "subtransactions-1-tags": "",
            },
            follow_redirects=True,
        )
        # Returns to the "Account Details" page with the new transaction added
        assert self.page_header_includes_substring("Account Details")
        assert self.div_exists(id="account-summary")
        # 1 transaction in the table for the account
        assert self.div_exists(class_="transactions-table")
        assert self.tag_count_is_equal(1, "div", class_="transaction")
        for id_ in (7,):
            assert self.div_exists(id=f"transaction-{id_}")
        notes_tag = self.soup.find("div", class_="notes text column")
        assert "Do not pass GO, do not collect $200" in notes_tag.text

    def test_add_subtransaction_fields(self, authorization):
        self.post_route("/_add_subtransaction_fields", json={"subtransaction_count": 1})
        # Created a second transaction with index 1
        assert self.div_exists(id="subtransactions-1")
        assert self.input_exists(id="subtransactions-1-subtotal")
        assert self.input_exists(id="subtransactions-1-note")
        assert self.input_exists(id="subtransactions-1-tags")

    def test_add_transfer_field(self, authorization):
        self.post_route("/_add_transfer_field")
        assert self.div_exists(id="transfer_accounts_info-0")
        assert self.input_exists(id="transfer_accounts_info-0-bank_name")
        assert self.input_exists(id="transfer_accounts_info-0-type_name")
        assert self.input_exists(id="transfer_accounts_info-0-last_four_digits")

    @transaction_lifetime
    def test_delete_transaction(self, authorization):
        self.get_route("/delete_transaction/4", follow_redirects=True)
        assert self.page_header_includes_substring("Account Details")
        # 2 transactions in the table for the user
        assert self.div_exists(class_="transactions-table")
        assert self.tag_count_is_equal(2, "div", class_="transaction")
        # Ensure that the transaction was deleted
        assert not self.input_has_value("What else is there to do in Jail?")

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
        with pytest.raises(ValueError, match="The given tag name already exists."):
            self.post_route(
                "/_add_tag",
                json={"tag_name": "Railroad", "parent": None},
            )

    @transaction_lifetime
    def test_delete_tag(self, authorization):
        self.post_route("/_delete_tag", json={"tag_name": "Railroad"})
        # Returns an empty string
        assert self.response.data == b""

    @transaction_lifetime
    def test_delete_tag_invalid(self, authorization):
        self.post_route("/_delete_tag", json={"tag_name": "Credit payments"})
        assert all(_ in self.soup.text for _ in ("No dice!", "403", "Forbidden"))

    @pytest.mark.parametrize(
        ("field", "suggestions"),
        [
            ("bank_name", ("TheBank", "Jail")),
            ("last_four_digits", ("5556", "5557")),
            (
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
            ),
        ],
    )
    def test_suggest_transaction_autocomplete(self, authorization, field, suggestions):
        self.post_route("/_suggest_transaction_autocomplete", json={"field": field})
        # Returned suggestions are not required to be in any particular order
        # (for this test)
        assert sorted(json.loads(self.response.data)) == sorted(suggestions)

    @transaction_lifetime
    def test_update_bank_name(self, authorization):
        self.post_route("/_update_bank_name/2", json="Prison")  # less fun than jail...
        assert self.response.data == b"Prison"

    @transaction_lifetime
    def test_delete_bank(self, authorization):
        self.get_route("/delete_bank/2", follow_redirects=True)
        assert self.page_header_includes_substring("Profile")
        # 1 remaining bank for the user
        assert self.tag_count_is_equal(1, "div", class_="bank-block")
