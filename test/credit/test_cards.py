"""Tests for the credit module managing credit cards."""
from unittest.mock import patch

import pytest
from werkzeug.exceptions import NotFound
from sqlalchemy.exc import IntegrityError

from monopyly.database.models import CreditCard, CreditStatement
from monopyly.credit.cards import CreditCardHandler, save_card
from ..helpers import TestHandler


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

    def test_initialization(self, card_handler):
        assert card_handler.model == CreditCard
        assert card_handler.table == "credit_cards"
        assert card_handler.user_id == 3

    @pytest.mark.parametrize(
        "bank_ids, account_ids, last_four_digits, active, reference_entries",
        [[None, None, None, None, db_reference],
         [(2,), None, None, None, [db_reference[0], db_reference[2]]],
         [None, (2,), None, None, [db_reference[0], db_reference[2]]],
         [None, None, ("3335",), None, db_reference[:1]],
         [None, None, None, 1, db_reference[:2]]]
    )
    def test_get_cards(self, card_handler, bank_ids, account_ids,
                       last_four_digits, active, reference_entries):
        cards = card_handler.get_cards(bank_ids, account_ids, last_four_digits,
                                       active)
        self.assertEntriesMatch(cards, reference_entries)

    @pytest.mark.parametrize(
        "card_id, reference_entry",
        [[2, db_reference[2]],
         [3, db_reference[0]]]
    )
    def test_get_entry(self, card_handler, card_id, reference_entry):
        card = card_handler.get_entry(card_id)
        self.assertEntryMatches(card, reference_entry)

    @pytest.mark.parametrize(
        "card_id, exception",
        [[1, NotFound],  # Not the logged in user
         [5, NotFound]]  # Not in the database
    )
    def test_get_entry_invalid(self, card_handler, card_id, exception):
        with pytest.raises(exception):
            card_handler.get_entry(card_id)

    @pytest.mark.parametrize(
        "bank_name, last_four_digits, reference_entry",
        [["Jail", "3334", db_reference[2]],
         [None, "3335", db_reference[0]],
         ["TheBank", "3336", db_reference[1]]]
    )
    def test_find_card(self, card_handler, bank_name, last_four_digits,
                       reference_entry):
        card = card_handler.find_card(bank_name, last_four_digits)
        self.assertEntryMatches(card, reference_entry)

    @pytest.mark.parametrize(
        "bank_name, last_four_digits",
        [["Jail", "6666"],
         [None, None]]
    )
    def test_find_card_none_exist(self, card_handler, bank_name,
                                  last_four_digits):
        card = card_handler.find_card(bank_name, last_four_digits)
        assert card is None

    @pytest.mark.parametrize(
        "mapping",
        [{"account_id": 2, "last_four_digits": "4444", "active": 1},
         {"account_id": 3, "last_four_digits": "4444", "active": 0}]
    )
    def test_add_entry(self, card_handler, mapping):
        card = card_handler.add_entry(**mapping)
        # Check that the entry object was properly created
        assert card.last_four_digits == "4444"
        # Check that the entry was added to the database
        self.assertNumberOfMatches(
            1, CreditCard.id, CreditCard.last_four_digits == "4444"
        )

    @pytest.mark.parametrize(
        "mapping, exception",
        [[{"account_id": 2, "invalid_field": "Test", "active": 1}, TypeError],
         [{"account_id": 3, "last_four_digits": "4444"}, IntegrityError]]
    )
    def test_add_entry_invalid(self, card_handler, mapping, exception):
        with pytest.raises(exception):
            card_handler.add_entry(**mapping)

    def test_add_entry_invalid_user(self, card_handler):
        mapping = {
            "account_id": 1,
            "last_four_digits": "4444",
            "active": 1,
        }
        # Ensure that 'mr.monopyly' cannot add an entry for the test user
        self.assert_invalid_user_entry_add_fails(
            card_handler, mapping, invalid_user_id=1, invalid_matches=1
        )

    @pytest.mark.parametrize(
        "mapping",
        [{"account_id": 2, "last_four_digits": "4444", "active": 1},
         {"account_id": 2, "last_four_digits": "4444"}]
    )
    def test_update_entry(self, card_handler, mapping):
        card = card_handler.update_entry(2, **mapping)
        # Check that the entry object was properly updated
        assert card.last_four_digits == "4444"
        # Check that the entry was updated in the database
        self.assertNumberOfMatches(
            1, CreditCard.id, CreditCard.last_four_digits == "4444"
        )

    @pytest.mark.parametrize(
        "card_id, mapping, exception",
        [[1, {"account_id": 2, "last_four_digits": "4444"},
          NotFound],                                        # wrong user
         [2, {"account_id": 2, "invalid_field": "Test"},
          ValueError],                                      # invalid field
         [5, {"account_id": 2, "last_four_digits": "4444"},
          NotFound]]                                        # nonexistent ID
    )
    def test_update_entry_invalid(self, card_handler, card_id, mapping,
                                  exception):
        with pytest.raises(exception):
            card_handler.update_entry(card_id, **mapping)

    @pytest.mark.parametrize("entry_id", [2, 3])
    def test_delete_entry(self, card_handler, entry_id):
        self.assert_entry_deletion_succeeds(card_handler, entry_id)
        # Check that the cascading entries were deleted
        self.assertNumberOfMatches(
            0, CreditStatement.id, CreditStatement.card_id == entry_id
        )

    @pytest.mark.parametrize(
        "entry_id, exception",
        [[1, NotFound],   # should not be able to delete other user entries
         [5, NotFound]]   # should not be able to delete nonexistent entries
    )
    def test_delete_entry_invalid(self, card_handler, entry_id, exception):
        with pytest.raises(exception):
            card_handler.delete_entry(entry_id)


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

