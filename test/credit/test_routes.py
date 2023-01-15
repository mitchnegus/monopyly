"""Tests for routes in the credit blueprint."""
from ..helpers import TestRoutes


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

    def test_load_account(self, authorization):
        self.get_route("/account/2")
        assert "Credit Account Details" in self.html
        # 4 rows with information
        assert self.html.count("info-row") == 4
        # 2 credit cards for the account
        assert self.html.count("credit-card-block") == 2

    @TestRoutes.transaction_client_lifetime
    def test_delete_card(self, transaction_authorization):
        self.get_route("/delete_card/3", follow_redirects=True)
        assert "Credit Account Details" in self.html
        # 4 rows with information
        assert self.html.count("info-row") == 4
        # 1 credit card for the account
        assert self.html.count("credit-card-block") == 1
        # Ensure that the card (ending in "3335") was deleted
        assert "3335" not in self.html

    @TestRoutes.transaction_client_lifetime
    def test_delete_account(self, transaction_authorization):
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

    def test_load_statement_details(self, authorization):
        self.get_route("/statement/4")
        assert "Statement Details" in self.html
        assert "statement-summary" in self.html
        # 3 transactions in the table on the statement
        assert "transactions-table" in self.html
        assert self.html.count('class="transaction ') == 3
        for id_ in (5, 6, 7):
            assert f"transaction-{id_}" in self.html

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
        assert 'value="2020-06-11"' not in self.html

    def test_add_statement_transaction_get(self, authorization):
        self.get_route("/add_transaction/3/5")
        assert "New Credit Transaction" in self.html
        assert '<form id="credit-transaction"' in self.html
        # Form should be prepopulated with the statement info
        assert 'value="Jail"' in self.html
        assert 'value="3335"' in self.html
        assert 'value="2020-06-11"' in self.html

    def test_update_transaction_get(self, authorization):
        self.get_route("/update_transaction/8")
        assert "Update Credit Transaction" in self.html
        assert '<form id="credit-transaction"' in self.html
        # Form should be prepopulated with the transaction info
        assert 'value="Jail"' in self.html
        assert 'value="3335"' in self.html
        assert 'value="2020-05-30"' in self.html
        assert 'value="Water Works"' in self.html
        assert 'value="2020-06-11"' in self.html

    @TestRoutes.transaction_client_lifetime
    def test_delete_transaction(self, transaction_authorization):
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

