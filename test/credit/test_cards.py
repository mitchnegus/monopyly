"""Tests for the credit module managing credit cards."""
from unittest.mock import patch

import pytest
from werkzeug.exceptions import NotFound

from monopyly.credit.cards import CreditCardHandler, save_card
from ..helpers import TestHandler


@pytest.fixture
def card_db(client_context):
    card_db = CreditCardHandler()
    yield card_db


class TestCreditCardHandler(TestHandler):

    # References only include entries accessible to the authorized login
    #   - ordered by active status (active first)
    reference = {
        'keys': ('id', 'account_id', 'last_four_digits', 'active'),
        'rows': [(3, 2, '3335', 1),
                 (4, 3, '3336', 1),
                 (2, 2, '3334', 0)]
    }

    def test_initialization(self, card_db):
        assert card_db.table == 'credit_cards'
        assert card_db.user_id == 3

    @pytest.mark.parametrize(
        'bank_ids, account_ids, last_four_digits, active, fields, '
        'reference_entries',
        [[None, None, None, None, None,
          reference['rows']],
         [None, None, None, None, ('account_id', 'last_four_digits'),
          [row[:3] for row in reference['rows']]],
         [(2,), None, None, None, ('account_id', 'last_four_digits'),
          [reference['rows'][0][:3], reference['rows'][2][:3]]],
         [None, (2,), None, None, ('account_id', 'last_four_digits'),
          [reference['rows'][0][:3], reference['rows'][2][:3]]],
         [None, None, ('3335',), None, ('account_id', 'last_four_digits'),
          [reference['rows'][0][:3]]],
         [None, None, None, 1, ('account_id', 'last_four_digits'),
          [row[:3] for row in reference['rows'][:2]]]]
    )
    def test_get_entries(self, card_db, bank_ids, account_ids,
                         last_four_digits, active, fields,
                         reference_entries):
        cards = card_db.get_entries(bank_ids, account_ids, last_four_digits,
                                    active, fields)
        if fields:
            self.assertMatchEntries(reference_entries, cards)
        else:
            # Leaving fields unspecified acquires all fields from many tables
            self.assertContainEntries(reference_entries, cards)

    @pytest.mark.parametrize(
        'card_id, fields, reference_entry',
        [[2, None,
          reference['rows'][2]],
         [3, None,
          reference['rows'][0]],
         [2, ('account_id', 'last_four_digits'),
          reference['rows'][2][:3]]]
    )
    def test_get_entry(self, card_db, card_id, fields, reference_entry):
        card = card_db.get_entry(card_id, fields)
        if fields:
            self.assertMatchEntry(reference_entry, card)
        else:
            # Leaving fields unspecified acquires all fields from many tables
            self.assertContainEntry(reference_entry, card)

    @pytest.mark.parametrize(
        'card_id, exception',
        [[1, NotFound],  # Not the logged in user
         [5, NotFound]]  # Not in the database
    )
    def test_get_entry_invalid(self, card_db, card_id, exception):
        with pytest.raises(exception):
            card_db.get_entry(card_id)

    @pytest.mark.parametrize(
        'bank_name, last_four_digits, fields, reference_entry',
        [['Jail', '3334', None,
          reference['rows'][2]],
         [None, '3335', None,
          reference['rows'][0]],
         ['TheBank', '3336', None,
          reference['rows'][1]],
         ['TheBank', '3336', ('account_id', 'last_four_digits'),
          reference['rows'][1][:3]]]
    )
    def test_find_card(self, card_db, bank_name, last_four_digits, fields,
                          reference_entry):
        card = card_db.find_card(bank_name, last_four_digits, fields)
        if fields:
            self.assertMatchEntry(reference_entry, card)
        else:
            # Leaving fields unspecified acquires all fields from many tables
            self.assertContainEntry(reference_entry, card)

    @pytest.mark.parametrize(
        'bank_name, last_four_digits, fields, reference_entry',
        [('Jail', '6666', None,
          None),
         (None, None, None,
          None)]
    )
    def test_find_card_none_exist(self, card_db, bank_name, last_four_digits,
                                     fields, reference_entry):
        card = card_db.find_card(bank_name, last_four_digits, fields)
        assert card is None

    @pytest.mark.parametrize(
        'mapping',
        [{'account_id': 2, 'last_four_digits': '4444', 'active': 1},
         {'account_id': 3, 'last_four_digits': '4444', 'active': 0}]
    )
    def test_add_entry(self, app, card_db, mapping):
        card = card_db.add_entry(mapping)
        assert card['last_four_digits'] == '4444'
        # Check that the entry was added
        query = ("SELECT COUNT(id) FROM credit_cards"
                 " WHERE last_four_digits = 4444")
        self.assertQueryEqualsCount(app, query, 1)

    @pytest.mark.parametrize(
        'mapping',
        [{'account_id': 2, 'invalid_field': 'Test', 'active': 1},
         {'account_id': 3, 'last_four_digits': '4444'}]
    )
    def test_add_entry_invalid(self, card_db, mapping):
        with pytest.raises(ValueError):
            card_db.add_entry(mapping)

    @pytest.mark.parametrize(
        'mapping',
        [{'account_id': 2, 'last_four_digits': '4444', 'active': 1},
         {'account_id': 2, 'last_four_digits': '4444'}]
    )
    def test_update_entry(self, app, card_db, mapping):
        card = card_db.update_entry(2, mapping)
        assert card['last_four_digits'] == '4444'
        # Check that the entry was updated
        query = ("SELECT COUNT(id) FROM credit_cards"
                 " WHERE last_four_digits =  '4444'")
        self.assertQueryEqualsCount(app, query, 1)

    @pytest.mark.parametrize(
        'card_id, mapping, exception',
        [[1, {'account_id': 2, 'last_four_digits': '4444'},  # another user
          NotFound],
         [2, {'account_id': 2, 'invalid_field': 'Test'},
          ValueError],
         [5, {'account_id': 2, 'last_four_digits': '4444'},  # nonexistent ID
          NotFound]]
    )
    def test_update_entry_invalid(self, card_db, card_id, mapping,
                                  exception):
        with pytest.raises(exception):
            card_db.update_entry(card_id, mapping)

    @pytest.mark.parametrize(
        'entry_ids', [(2,), (2, 3)]
    )
    def test_delete_entries(self, app, card_db, entry_ids):
        card_db.delete_entries(entry_ids)
        # Check that the entries were deleted
        for entry_id in entry_ids:
            query = ("SELECT COUNT(id) FROM credit_cards"
                    f" WHERE id = {entry_id}")
            self.assertQueryEqualsCount(app, query, 0)

    def test_delete_cascading_entries(self, app, card_db):
        card_db.delete_entries((3,))
        # Check that the cascading entries were deleted
        query = ("SELECT COUNT(id) FROM credit_statements"
                f" WHERE card_id = 3")
        self.assertQueryEqualsCount(app, query, 0)

    @pytest.mark.parametrize(
        'entry_ids, exception',
        [[(1,), NotFound],   # should not be able to delete other user entries
         [(5,), NotFound]]   # should not be able to delete nonexistent entries
    )
    def test_delete_entries_invalid(self, card_db, entry_ids, exception):
        with pytest.raises(exception):
            card_db.delete_entries(entry_ids)


class TestSaveFormFunctions:

    @patch('monopyly.credit.cards.CreditCardHandler')
    @patch('monopyly.credit.forms.CreditCardForm')
    def test_save_new_card(self, mock_form, mock_handler_type):
        # Mock the return values and data
        mock_method = mock_handler_type.return_value.add_entry
        mock_card = {'id': 0, 'last_four_digits': '2222'}
        mock_method.return_value = mock_card
        mock_form.card_data = {'key': 'test card data'}
        # Call the function and check for proper call signatures
        card = save_card(mock_form)
        mock_method.assert_called_once_with(mock_form.card_data)
        assert card == mock_card

    @patch('monopyly.credit.cards.CreditCardHandler')
    @patch('monopyly.credit.forms.CreditCardForm')
    def test_save_updated_card(self, mock_form, mock_handler_type):
        # Mock the return values and data
        mock_method = mock_handler_type.return_value.update_entry
        mock_card = {'id': 0, 'last_four_digits': '2222'}
        mock_method.return_value = mock_card
        mock_form.card_data = {'key': 'test card data'}
        # Call the function and check for proper call signatures
        card_id = 2
        card = save_card(mock_form, card_id)
        mock_method.assert_called_once_with(card_id, mock_form.card_data)
        assert card == mock_card

