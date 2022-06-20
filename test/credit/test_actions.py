"""Tests for the actions performed by the credit blueprint."""
import datetime
from unittest.mock import MagicMock, patch

import pytest

from monopyly.credit.actions import *
from test.helpers import TestGrouper, TestHandler


class TestGroupingActions(TestGrouper):

    def test_get_card_statement_groupings(self, client_context):
        cards = [MagicMock(), MagicMock()]
        cards[0].__getitem__.return_value = 3
        cards[1].__getitem__.return_value = 4
        statement_id_groupings = {3: [3, 4, 5], 4: [6, 7]}
        groupings = get_card_statement_groupings(cards)
        self.compare_groupings(groupings, statement_id_groupings)
        # Ensure that date fields are returned as `datetime.date` objects
        for card, statements in groupings.items():
            for statement in statements:
                for key in statement.keys():
                    if key.endswith('_date') and statement[key] is not None:
                        assert isinstance(statement[key], datetime.date)


@pytest.mark.parametrize(
    'mock_card, expected_preceding_card',
    [[{'id': 5, 'account_id': 2, 'last_four_digits': '3337', 'active': 1},
      (3, '3335')],
     [{'id': 5, 'account_id': 3, 'last_four_digits': '3337', 'active': 1},
      (4, '3336')]]
)
def test_get_potential_preceding_card(client_context, mock_card,
                                      expected_preceding_card):
    preceding_card = get_potential_preceding_card(mock_card)
    TestHandler.assertMatchEntry(expected_preceding_card, preceding_card)


@pytest.mark.parametrize(
    'mock_card, mock_active_cards, mock_statements',
    [#inactive new card
     [{'id': 100, 'account_id': 2, 'last_four_digits': '3337', 'active': 0},
      None, None],
     # multiple active existing cards
     [{'id': 100, 'account_id': 2, 'last_four_digits': '3337', 'active': 1},
      [{'id': 100, 'account_id': 2, 'last_four_digits': '3337', 'active': 1},
       {'id': 100, 'account_id': 2, 'last_four_digits': '3338', 'active': 1},
       {'id': 100, 'account_id': 2, 'last_four_digits': '3339', 'active': 1}],
      None],
     # no statements for eligible preceding card
     [{'id': 100, 'account_id': 2, 'last_four_digits': '3337', 'active': 1},
      [{'id': 100, 'account_id': 2, 'last_four_digits': '3337', 'active': 1},
       {'id': 100, 'account_id': 2, 'last_four_digits': '3338', 'active': 1}],
      []],
     # no balance on most recent statement for eligible preceding card
     [{'id': 100, 'account_id': 2, 'last_four_digits': '3337', 'active': 1},
      [{'id': 100, 'account_id': 2, 'last_four_digits': '3337', 'active': 1},
       {'id': 100, 'account_id': 2, 'last_four_digits': '3338', 'active': 1}],
      [{'id': 501, 'card_id': 100, 'balance': 0},
       {'id': 500, 'card_id': 100, 'balance': 25.00}]]]
)
@patch('monopyly.credit.actions.CreditStatementHandler')
@patch('monopyly.credit.actions.CreditCardHandler')
def test_get_potential_preceding_card_none_exist(mock_card_handler_type,
                                                 mock_statement_handler_type,
                                                 mock_card, mock_active_cards,
                                                 mock_statements):
    # Mock the values returned from querying the database
    mock_card_db = mock_card_handler_type.return_value
    mock_card_db.get_entries.return_value = mock_active_cards
    mock_statement_db = mock_statement_handler_type.return_value
    mock_statement_db.get_entries.return_value = mock_statements
    assert get_potential_preceding_card(mock_card) == None


@pytest.mark.parametrize('mock_form_data', ['yes', 'no'])
@patch('monopyly.credit.actions.CreditStatementHandler')
@patch('monopyly.credit.actions.CreditCardHandler')
def test_transfer_credit_card_statement(mock_card_handler_type,
                                        mock_statement_handler_type,
                                        mock_form_data):
    # Mock the values returned from querying the database
    mock_card_db = mock_card_handler_type.return_value
    mock_card_update_method = mock_card_db.update_entry_value
    mock_statement_db = mock_statement_handler_type.return_value
    mock_statement_db.get_entries.return_value = [{'id': 100}, {'id': 101}]
    mock_statement_update_method = mock_statement_db.update_entry_value
    # Mock the transffer inquiry form
    mock_form = MagicMock()
    mock_form.__getitem__.return_value.data = mock_form_data
    # Test the method
    transfer_credit_card_statement(mock_form, 5, 4)
    if mock_form_data == 'yes':
        mock_statement_update_method.assert_called_once_with(100, 'card_id', 5)
        mock_card_update_method.assert_called_once_with(4, 'active', 0)


@pytest.mark.parametrize(
    'payment_account_id, transfer_count',
    [[3, 1],
     [None, 0]]
)
def test_make_payment(app, client_context, payment_account_id, transfer_count):
    make_payment(4, payment_account_id, datetime.date(2020, 7, 1), 500)
    bank_query = ("SELECT COUNT(id) FROM bank_transactions_view"
                  " WHERE transaction_date = '2020-07-01' AND total = -500")
    TestHandler.assertQueryEqualsCount(app, bank_query, transfer_count)
    credit_query = ("SELECT COUNT(id) FROM credit_transactions_view"
                    " WHERE transaction_date = '2020-07-01' AND total = -500")
    TestHandler.assertQueryEqualsCount(app, credit_query, 1)


@patch('monopyly.credit.actions.CreditTransactionHandler')
@patch('monopyly.credit.actions.CreditStatementHandler')
def test_get_bank_account_details(mock_statement_handler_type,
                                  mock_transaction_handler_type):
    mock_statement = {'id': 'test id'}
    mock_statement_db = mock_statement_handler_type()
    mock_statement_db.get_entry.return_value = mock_statement
    mock_transaction_db = mock_transaction_handler_type()
    mock_transaction_db.get_entries.return_value = ['test entries']
    default_args = {
        'statement_ids': ('test id',),
        'sort_order': 'DESC',
        'fields': (
            'transaction_date',
            'vendor',
            'total',
            'notes',
            'internal_transaction_id',
        )
    }
    details = get_credit_statement_details(mock_statement['id'])
    assert details == (mock_statement, ['test entries'])
    mock_transaction_db.get_entries.assert_called_once_with(**default_args)

