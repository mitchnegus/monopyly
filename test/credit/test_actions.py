"""Tests for the actions performed by the credit blueprint."""
from datetime import date
from unittest.mock import Mock, patch, call

import pytest

from monopyly.credit.actions import (
    get_card_statement_grouping, get_potential_preceding_card,
    transfer_credit_card_statement, make_payment
)
from monopyly.banking.transactions import BankTransactionHandler
from monopyly.credit.cards import CreditCardHandler
from monopyly.credit.statements import CreditStatementHandler
from monopyly.credit.transactions import CreditTransactionHandler
from ..helpers import transaction_lifetime


@patch('monopyly.credit.actions.CreditStatementHandler.get_statements')
def test_get_card_statement_grouping(mock_statements_method):
    # Mock the inputs and external return values
    mock_cards = [Mock() for _ in range(3)]
    mock_statements = [Mock() for _ in range(3)]
    mock_statements_method.return_value = mock_statements
    # Check that the returned summary matches the expected format
    card_statements = get_card_statement_grouping(mock_cards)
    assert len(card_statements) == len(mock_statements)
    expected_calls = [
        call(card_ids=(mock_card.id,), sort_order="DESC")
        for mock_card in mock_cards
    ]
    assert mock_statements_method.mock_calls == expected_calls
    for key, mock_card in zip(card_statements, mock_cards):
        assert key == mock_card
        assert card_statements[mock_card] == mock_statements_method.return_value


def test_get_potential_preceding_card(client_context):
    # Mock the card to be tested for a preceding card
    card = Mock(id=5, active=1, account_id=2)
    preceding_card = get_potential_preceding_card(card)
    assert preceding_card.id == 3


def test_get_potential_preceding_card_inactive_card(client_context):
    # Mock the card to be tested for a preceding card
    card = Mock(id=5, active=0, account_id=2)
    preceding_card = get_potential_preceding_card(card)
    assert preceding_card is None


def test_get_potential_preceding_card_multiple_active_cards(client_context):
    # Add an active card to have multiple active cards
    other_active_card = CreditCardHandler.add_entry(
        account_id=3,
        last_four_digits="3337",
        active=1,
    )
    # Mock the card to be tested for a preceding card
    card = Mock(id=6, active=1, account_id=3)
    preceding_card = get_potential_preceding_card(card)
    assert preceding_card is None

def test_get_potential_preceding_card_no_statements(client_context):
    # Deactivate the original active card with statements
    CreditCardHandler.update_entry(4, active=0)
    # Add a card (without statements)
    other_active_card = CreditCardHandler.add_entry(
        account_id=3,
        last_four_digits="3337",
        active=1,
    )
    # Mock the card to be tested for a preceding card
    card = Mock(id=6, active=1, account_id=3)
    preceding_card = get_potential_preceding_card(card)
    assert preceding_card is None

def test_get_potential_preceding_card_no_balance(app, client_context):
    # Deactivate the original active card with statements
    CreditCardHandler.update_entry(4, active=0)
    # Add a card (without statements)
    other_active_card = CreditCardHandler.add_entry(
        account_id=3,
        last_four_digits="3337",
        active=1,
    )
    # Add a statement to the new card (and a transaction zeroing the balance)
    statement = CreditStatementHandler.add_statement(
        other_active_card, date(2020, 7, 10), due_date=date(2020, 8, 3)
    )
    CreditTransactionHandler.add_entry(
        internal_transaction_id=None,
        statement_id=statement.id,
        transaction_date=date(2020, 7, 9),
        vendor="Balance Beam Fitness",
        subtransactions=[
            {"subtotal": -636.33, "note": "Zeroing the balance", "tags": []},
        ]
    )
    app.db.session.refresh(statement)
    # Mock the card to be tested for a preceding card
    card = Mock(id=6, active=1, account_id=3)
    preceding_card = get_potential_preceding_card(card)
    assert preceding_card is None


@pytest.mark.parametrize("transfer", ["yes", "no"])
def test_transfer_credit_card_statement(client_context, transfer):
    mock_form = Mock()
    mock_form.transfer.data = transfer
    card = CreditCardHandler.add_entry(
        account_id=2, last_four_digits="3337", active=1
    )
    prior_card_id = 3
    transfer_credit_card_statement(mock_form, card.id, prior_card_id)
    # Check that the latest statement was transferred to the new card
    latest_statement = CreditStatementHandler.get_entry(5)
    expected_card_id = (card.id if transfer == "yes" else prior_card_id)
    assert latest_statement.card_id == expected_card_id
    # Check that the prior card was deactivated
    prior_card = CreditCardHandler.get_entry(prior_card_id)
    expected_prior_card_active = (0 if transfer == "yes" else 1)
    assert prior_card.active == expected_prior_card_active


@transaction_lifetime
def test_make_payment(client_context):
    transaction_date = date(2020, 7, 1)
    make_payment(4, 3, transaction_date, 100.00)
    payment_bank_transaction = BankTransactionHandler.get_entry(8)
    assert payment_bank_transaction.internal_transaction_id == 4
    assert payment_bank_transaction.account_id == 3
    assert payment_bank_transaction.transaction_date == transaction_date
    assert len(payment_bank_transaction.subtransactions) == 1
    assert payment_bank_transaction.subtransactions[0].subtotal == -100
    assert "TheBank" in payment_bank_transaction.subtransactions[0].note
    assert "3336" in payment_bank_transaction.subtransactions[0].note
    payment_credit_transaction = CreditTransactionHandler.get_entry(14)
    assert payment_credit_transaction.internal_transaction_id == 4
    assert payment_credit_transaction.statement_id == 8
    assert payment_credit_transaction.transaction_date == transaction_date
    assert payment_credit_transaction.vendor == "TheBank"
    assert len(payment_credit_transaction.subtransactions) == 1
    assert payment_credit_transaction.subtransactions[0].subtotal == -100
    assert payment_credit_transaction.subtransactions[0].note == "Card payment"


def test_make_payment_no_bank_account(client_context):
    make_payment(4, None, date(2020, 7, 1), 100.00)
    payment_credit_transaction = CreditTransactionHandler.get_entry(14)
    assert payment_credit_transaction.internal_transaction_id is None
    assert payment_credit_transaction.statement_id == 8
    assert payment_credit_transaction.transaction_date == date(2020, 7, 1)
    assert payment_credit_transaction.vendor == "TheBank"
    assert len(payment_credit_transaction.subtransactions) == 1
    assert payment_credit_transaction.subtransactions[0].subtotal == -100
    assert payment_credit_transaction.subtransactions[0].note == "Card payment"
