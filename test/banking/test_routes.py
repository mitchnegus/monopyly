"""Tests for routes in the banking blueprint."""
from ..helpers import TestRoutes


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

    @TestRoutes.transaction_client_lifetime
    def test_delete_account(self, transaction_authorization):
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

    def test_update_transaction_get(self, authorization):
        self.get_route("/update_transaction/4")
        assert "Update Bank Transaction" in self.html
        assert '<form id="bank-transaction"' in self.html
        # Form should be prepopulated with the transaction info
        assert 'value="Jail"' in self.html
        assert 'value="5556"' in self.html
        assert 'value="2020-05-06"' in self.html
        assert 'value="What else is there to do in Jail?"' in self.html

    @TestRoutes.transaction_client_lifetime
    def test_delete_transaction(self, transaction_authorization):
        self.get_route("/delete_transaction/4", follow_redirects=True)
        assert "Account Details" in self.html
        # 2 transactions in the table for the user
        assert "transactions-table" in self.html
        assert self.html.count('class="transaction ') == 2
        # Ensure that the transaction was deleted
        assert 'value="What else is there to do in Jail?"' not in self.html

