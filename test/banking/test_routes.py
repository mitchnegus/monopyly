"""Tests for routes in the banking blueprint."""
import json

import pytest

from ..helpers import transaction_lifetime, TestRoutes


class TestBankingRoutes(TestRoutes):

    blueprint_prefix = "banking"

    def test_load_accounts(self, authorization):
        self.get_route("/accounts")
        assert "Bank Accounts" in self.html
        # 2 banks for the user, with 3 total accounts
        assert self.html.count("bank-block") == 2
        assert self.html.count('class="account-block"') == 3

    def test_add_account_get(self, authorization):
        self.get_route("/add_account")
        assert "New Bank Account" in self.html
        assert '<form id="bank-account"' in self.html

    def test_add_bank_account_get(self, authorization):
        self.get_route("/add_account/2")
        assert "New Bank Account" in self.html
        assert '<form id="bank-account"' in self.html
        # Form should be prepopulated with the bank info
        assert 'value="Jail"' in self.html

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
        assert "Bank Accounts" in self.html
        assert self.html.count("bank-block") == 2
        assert self.html.count('class="account-block"') == 4
        assert "8888" in self.html

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
        assert "Bank Accounts" in self.html
        assert self.html.count("bank-block") == 3
        assert self.html.count('class="account-block"') == 4
        assert "8888" in self.html

    @transaction_lifetime
    def test_delete_account(self, authorization):
        self.get_route("/delete_account/3", follow_redirects=True)
        assert "Bank Accounts" in self.html
        # 2 banks for the user, with 2 total accounts
        assert self.html.count("bank-block") == 2
        assert self.html.count('class="account-block"') == 2

    def test_load_account_summaries(self, authorization):
        self.get_route("/account_summaries/2")
        assert "Bank Account Summaries" in self.html
        # 2 accounts (1 checking, 1 savings)
        total_balance = (42.00 + 43.00 + 300 + 58.90 - 109.21 - 300)
        assert f'<h2 class="bank">Jail (${total_balance:.2f})</h2' in self.html
        assert self.html.count("account-type-block") == 2
        assert self.html.count('<span class="digits">5556</span>') == 2
        assert self.html.count("<b>Savings</b>") == 1
        assert self.html.count("<b>Checking</b>") == 1

    def test_load_account_details(self, authorization):
        self.get_route("/account/2")
        assert "Account Details" in self.html
        assert "account-summary" in self.html
        # 3 transactions in the table for the account
        assert "transactions-table" in self.html
        assert self.html.count('class="transaction ') == 3
        for id_ in (2, 3, 4):
            assert f"transaction-{id_}" in self.html

    def test_expand_transaction(self, authorization):
        self.post_route("/_expand_transaction", json="transaction-5")
        # 1 subtransaction in this transaction
        assert self.html.count("subtransaction-details") == 1
        assert "Credit card payment" in self.html
        assert "$-109.21" in self.html

    def test_show_linked_bank_transaction(self, authorization):
        self.post_route(
            "/_show_linked_transaction", json={"transaction_id": 6}
        )
        # Show the overlay
        assert "overlay" in self.html
        assert "linked-transaction-display" in self.html
        # The current transaction is a bank transaction
        assert "Jail (5556)" in self.html
        assert "Checking" in self.html
        # The linked transaction is also a bank transaction
        assert "Jail (5556)" in self.html
        assert "Savings" in self.html

    def test_show_linked_credit_transaction(self, authorization):
        self.post_route(
            "/_show_linked_transaction", json={"transaction_id": 5}
        )
        # Show the overlay
        assert "overlay" in self.html
        assert "linked-transaction-display" in self.html
        # The current transaction is a bank transaction
        assert "Jail (5556)" in self.html
        assert "Checking" in self.html
        # The linked transaction is a credit transaction
        assert "JP Morgan Chance" in self.html
        assert "Credit Card" in self.html

    def test_add_transaction_get(self, authorization):
        self.get_route("/add_transaction")
        assert "New Bank Transaction" in self.html
        assert '<form id="bank-transaction"' in self.html

    def test_add_bank_transaction_get(self, authorization):
        self.get_route("/add_transaction/2")
        assert "New Bank Transaction" in self.html
        assert '<form id="bank-transaction"' in self.html
        # Form should be prepopulated with the bank info
        assert 'value="Jail"' in self.html
        assert 'value="5556"' not in self.html

    def test_add_account_transaction_get(self, authorization):
        self.get_route("/add_transaction/2/3")
        assert "New Bank Transaction" in self.html
        assert '<form id="bank-transaction"' in self.html
        # Form should be prepopulated with the account info
        assert 'value="Jail"' in self.html
        assert 'value="5556"' in self.html

    @transaction_lifetime
    def test_add_transaction_post(self, authorization):
        self.post_route(
            "/add_transaction",
            data={
                "transaction_date": "2022-01-19",
                "account_info-last_four_digits": "5556",
                "account_info-type_name": "Savings",
                "subtransactions-1-subtotal": "505.00",
                "subtransactions-1-note": "7 hour flight, 45 minute drive",
            },
            follow_redirects=True,
        )
        # Returns to the "Account Details" page with the new transaction added
        assert "Account Details" in self.html
        assert "account-summary" in self.html
        # 4 transactions in the table for the account
        assert "transactions-table" in self.html
        assert self.html.count('class="transaction ') == 4
        for id_ in (2, 3, 4, 8):
            assert f"transaction-{id_}" in self.html

    @transaction_lifetime
    def test_add_transaction_multiple_subtransactions_post(
        self, authorization
    ):
        self.post_route(
            "/add_transaction",
            data={
                "transaction_date": "2022-01-19",
                "account_info-last_four_digits": "5556",
                "account_info-type_name": "Savings",
                "subtransactions-1-subtotal": "505.00",
                "subtransactions-1-note": "7 hour flight, 45 minute drive",
                "subtransactions-2-subtotal": "0.80",
                "subtransactions-2-note": "Rave reviews",
                "subtransactions-3-subtotal": "70.70",
                "subtransactions-3-note": "Easy money",
            },
            follow_redirects=True,
        )
        # Returns to the "Account Details" page with the new transaction added
        assert "Account Details" in self.html
        assert "account-summary" in self.html
        # 4 transactions in the table for the account
        assert "transactions-table" in self.html
        assert self.html.count('class="transaction ') == 4
        for id_ in (2, 3, 4, 8):
            assert f"transaction-{id_}" in self.html

    def test_update_transaction_get(self, authorization):
        self.get_route("/update_transaction/4")
        assert "Update Bank Transaction" in self.html
        assert '<form id="bank-transaction"' in self.html
        # Form should be prepopulated with the transaction info
        assert 'value="Jail"' in self.html
        assert 'value="5556"' in self.html
        assert 'value="2020-05-06"' in self.html
        assert 'value="What else is there to do in Jail?"' in self.html

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
            },
            follow_redirects=True,
        )
        # Returns to the "Account Details" page with the new transaction added
        assert "Account Details" in self.html
        assert "account-summary" in self.html
        # 4 transactions in the table for the account
        assert "transactions-table" in self.html
        assert self.html.count('class="transaction ') == 1
        for id_ in (7,):
            assert f"transaction-{id_}" in self.html
        assert "Do not pass GO, do not collect $200" in self.html

    def test_add_subtransaction_fields(self, authorization):
        self.post_route(
            "/_add_subtransaction_fields",
            json={"subtransaction_count": 1}
        )
        assert 'id="subtransactions-2"' in self.html
        assert "subtransactions-2-subtotal" in self.html
        assert "subtransactions-2-note" in self.html

    def test_add_transfer_field(self, authorization):
        self.post_route("/_add_transfer_field")
        assert 'id="transfer_accounts_info-0"' in self.html
        assert "transfer_accounts_info-0-bank_name" in self.html
        assert "transfer_accounts_info-0-type_name" in self.html
        assert "transfer_accounts_info-0-last_four_digits" in self.html

    @transaction_lifetime
    def test_delete_transaction(self, authorization):
        self.get_route("/delete_transaction/4", follow_redirects=True)
        assert "Account Details" in self.html
        # 2 transactions in the table for the user
        assert "transactions-table" in self.html
        assert self.html.count('class="transaction ') == 2
        # Ensure that the transaction was deleted
        assert 'value="What else is there to do in Jail?"' not in self.html

    @pytest.mark.parametrize(
        "field, suggestions",
        [["bank_name", ["TheBank", "Jail"]],
         ["last_four_digits", ["5556", "5557"]]]
    )
    def test_suggest_transaction_autocomplete(self, authorization, field,
                                              suggestions):
        self.post_route(
            "/_suggest_transaction_autocomplete", json={"field": field}
        )
        # Returned suggestions are not required to be in any particular order
        # (for this test)
        assert sorted(json.loads(self.response.data)) == sorted(suggestions)

