"""Tests for tools used by the analytics blueprint."""

from unittest.mock import Mock, patch

import pytest

from monopyly.analytics.tools import FinancialPositionInventory
from monopyly.credit.cards import CreditCardRepository


class TestFinancialPositionInventory:
    """Isolated unit tests that mock out the underlying repositories."""

    @patch("monopyly.analytics.tools.CreditCardRepository.get_cards")
    @patch("monopyly.analytics.tools.BankAccountRepository.get_accounts")
    def test_init(self, mock_get_accounts, mock_get_cards):
        mock_accounts, mock_cards = Mock(), Mock()
        mock_get_accounts.return_value.all.return_value = mock_accounts
        mock_get_cards.return_value.all.return_value = mock_cards
        position_inventory = FinancialPositionInventory()
        # Check that the repositories were queried as expected
        mock_get_accounts.assert_called_once_with()
        mock_get_cards.assert_called_once_with(active=True)
        # Check that the returned collections were stored on the object
        assert position_inventory.bank_accounts == mock_accounts
        assert position_inventory.credit_cards == mock_cards

    @patch("monopyly.analytics.tools.CreditCardRepository.get_cards")
    @patch("monopyly.analytics.tools.BankAccountRepository.get_accounts")
    def test_bank_total(self, mock_get_accounts, mock_get_cards):
        mock_get_accounts.return_value.all.return_value = [
            Mock(balance=100.00),
            Mock(balance=-50.25),
            Mock(balance=200.00),
        ]
        mock_get_cards.return_value.all.return_value = []
        position_inventory = FinancialPositionInventory()
        assert position_inventory.bank_total == 249.75

    @patch("monopyly.analytics.tools.CreditCardRepository.get_cards")
    @patch("monopyly.analytics.tools.BankAccountRepository.get_accounts")
    def test_credit_total(self, mock_get_accounts, mock_get_cards):
        mock_get_accounts.return_value.all.return_value = []
        mock_get_cards.return_value.all.return_value = [
            Mock(balance=75.50),
            Mock(balance=24.50),
        ]
        position_inventory = FinancialPositionInventory()
        assert position_inventory.credit_total == 100.00

    @patch("monopyly.analytics.tools.CreditCardRepository.get_cards")
    @patch("monopyly.analytics.tools.BankAccountRepository.get_accounts")
    def test_inventory_total_no_accounts(self, mock_get_accounts, mock_get_cards):
        mock_get_accounts.return_value.all.return_value = []
        mock_get_cards.return_value.all.return_value = []
        position_inventory = FinancialPositionInventory()
        assert position_inventory.bank_total == 0

    @pytest.mark.parametrize(
        ("bank_balances", "credit_balances", "expected_net_worth"),
        [
            ([100.00, -50.25, 200.00], [75.50, 24.50], 149.75),
            ([100.00], [], 100.00),
            ([], [50.00], -50.00),
            ([], [], 0),
            ([-100.00], [50.00], -150.00),
        ],
    )
    @patch("monopyly.analytics.tools.CreditCardRepository.get_cards")
    @patch("monopyly.analytics.tools.BankAccountRepository.get_accounts")
    def test_net_worth(
        self,
        mock_get_accounts,
        mock_get_cards,
        bank_balances,
        credit_balances,
        expected_net_worth,
    ):
        mock_get_accounts.return_value.all.return_value = [
            Mock(balance=balance) for balance in bank_balances
        ]
        mock_get_cards.return_value.all.return_value = [
            Mock(balance=balance) for balance in credit_balances
        ]
        position_inventory = FinancialPositionInventory()
        assert position_inventory.net_worth == expected_net_worth


class TestFinancialPositionInventoryIntegration:
    """End-to-end tests against the real repositories and test database."""

    @pytest.fixture
    def position_inventory(self, client_context):
        return FinancialPositionInventory()

    def test_bank_accounts(self, position_inventory):
        # Bank accounts should include both active and inactive accounts
        # (unlike credit cards, which are filtered to only active cards)
        account_ids = {account.id for account in position_inventory.bank_accounts}
        assert account_ids == {2, 3, 4}

    def test_credit_cards(self, position_inventory):
        # Only active credit cards should be included
        card_ids = {card.id for card in position_inventory.credit_cards}
        assert card_ids == {3, 4}

    def test_bank_total(self, position_inventory):
        # 'Jail' savings (443.90)
        # + 'Jail' checking (-409.21)
        # + 'TheBank' CD (200.00)
        assert position_inventory.bank_total == 234.69

    def test_credit_total(self, client_context, position_inventory):
        # Cross-check against an independently computed sum over the same
        # (active-only) cards the class itself queries
        cards = CreditCardRepository.get_cards(active=True).all()
        expected_credit_total = sum(card.balance for card in cards)
        assert position_inventory.credit_total == expected_credit_total

    def test_net_worth(self, position_inventory):
        expected_net_worth = (
            position_inventory.bank_total - position_inventory.credit_total
        )
        assert position_inventory.net_worth == expected_net_worth
