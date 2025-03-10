"""Tests for the credit module managing credit cards."""

from unittest.mock import patch

import pytest
from dry_foundation.testing.helpers import TestHandler
from werkzeug.exceptions import NotFound

from monopyly.credit.cards import CreditCardHandler, save_card
from monopyly.database.models import CreditCard, CreditStatement


@pytest.fixture
def card_handler(client_context):
    return CreditCardHandler


class TestCreditCardHandler(TestHandler):
    # References only include entries accessible to the authorized login
    #   - ordered by active status (active first)
    db_reference = [
        CreditCard(id=3, account_id=2, last_four_digits="3335", active=1),
        CreditCard(id=4, account_id=3, last_four_digits="3336", active=1),
        CreditCard(id=2, account_id=2, last_four_digits="3334", active=0),
    ]

    @pytest.mark.parametrize(
        "bank_ids, account_ids, last_four_digits, active, reference_entries",
        [
            [None, None, None, None, db_reference],
            [(2,), None, None, None, (db_reference[0], db_reference[2])],
            [None, (2,), None, None, (db_reference[0], db_reference[2])],
            [None, None, ("3335",), None, db_reference[:1]],
            [None, None, None, 1, db_reference[:2]],
        ],
    )
    def test_get_cards(
        self,
        card_handler,
        bank_ids,
        account_ids,
        last_four_digits,
        active,
        reference_entries,
    ):
        cards = card_handler.get_cards(bank_ids, account_ids, last_four_digits, active)
        self.assert_entries_match(cards, reference_entries)

    @pytest.mark.parametrize(
        "bank_name, last_four_digits, reference_entry",
        [
            ["Jail", "3334", db_reference[2]],
            [None, "3335", db_reference[0]],
            ["TheBank", "3336", db_reference[1]],
        ],
    )
    def test_find_card(
        self, card_handler, bank_name, last_four_digits, reference_entry
    ):
        card = card_handler.find_card(bank_name, last_four_digits)
        self.assert_entry_matches(card, reference_entry)

    @pytest.mark.parametrize(
        "bank_name, last_four_digits", [["Jail", "6666"], [None, None]]
    )
    def test_find_card_none_exist(self, card_handler, bank_name, last_four_digits):
        card = card_handler.find_card(bank_name, last_four_digits)
        assert card is None

    @pytest.mark.parametrize(
        "mapping",
        [
            {"account_id": 2, "last_four_digits": "4444", "active": 1},
            {"account_id": 3, "last_four_digits": "4444", "active": 0},
        ],
    )
    def test_add_entry(self, card_handler, mapping):
        card = card_handler.add_entry(**mapping)
        # Check that the entry object was properly created
        assert card.last_four_digits == "4444"
        # Check that the entry was added to the database
        self.assert_number_of_matches(
            1, CreditCard.id, CreditCard.last_four_digits == "4444"
        )

    @pytest.mark.parametrize("entry_id", [2, 3])
    def test_delete_entry(self, card_handler, entry_id):
        self.assert_entry_deletion_succeeds(card_handler, entry_id)
        # Check that the cascading entries were deleted
        self.assert_number_of_matches(
            0, CreditStatement.id, CreditStatement.card_id == entry_id
        )


class TestSaveFormFunctions:
    @patch("monopyly.credit.cards.CreditCardHandler")
    @patch("monopyly.credit.forms.CreditCardForm")
    def test_save_new_card(self, mock_form, mock_handler):
        # Mock the form and primary method
        mock_form.card_data = {"key": "test card data"}
        mock_method = mock_handler.add_entry
        # Call the function and check for proper call signatures
        card = save_card(mock_form)
        mock_method.assert_called_once_with(**mock_form.card_data)
        assert card == mock_method.return_value

    @patch("monopyly.credit.cards.CreditCardHandler")
    @patch("monopyly.credit.forms.CreditCardForm")
    def test_save_updated_card(self, mock_form, mock_handler):
        # Mock the form and primary method
        mock_form.card_data = {"key": "test card data"}
        mock_method = mock_handler.update_entry
        # Call the function and check for proper call signatures
        card_id = 2
        card = save_card(mock_form, card_id)
        mock_method.assert_called_once_with(card_id, **mock_form.card_data)
        assert card == mock_method.return_value
