"""Tests for the credit module managing transactions/subtransactions."""
from datetime import date
from unittest.mock import patch
from sqlite3 import IntegrityError

import pytest
from werkzeug.exceptions import NotFound

from monopyly.credit.transactions import (
    CreditTransactionHandler, CreditSubtransactionHandler, save_transaction
)
from ..helpers import TestHandler


@pytest.fixture
def transaction_db(client_context):
    transaction_db = CreditTransactionHandler()
    yield transaction_db


@pytest.fixture
def subtransaction_db(client_context):
    subtransaction_db = CreditSubtransactionHandler()
    yield subtransaction_db


class TestCreditTransactionHandler(TestHandler):

    # References only include entries accessible to the authorized login
    #   - ordered by date (most recent first)
    reference = {
        'keys': ('id', 'internal_transaction_id', 'statement_id',
                 'transaction_date', 'vendor'),
        'rows': [(11, None, 7, date(2020, 6, 5), 'Reading Railroad'),
                 (8, None, 5, date(2020, 5, 30), 'Water Works'),
                 (10, None, 6, date(2020, 5, 10), 'Income Tax Board'),
                 (7, 2, 4, date(2020, 5, 4), 'JP Morgan Chance'),
                 (6, None, 4, date(2020, 5, 1), 'Marvin Gardens'),
                 (5, None, 4, date(2020, 4, 25), 'Electric Company'),
                 (9, None, 6, date(2020, 4, 20), 'Pennsylvania Avenue'),
                 (2, None, 2, date(2020, 4, 13), 'Top Left Corner'),
                 (4, None, 3, date(2020, 4, 5), 'Park Place'),
                 (3, None, 3, date(2020, 3, 20), 'Boardwalk'),
                 (12, None, 2, date(2020, 3, 10), 'Community Chest')]
    }
    view_reference = {
        'keys': ('id', 'internal_transaction_id', 'statement_id',
                 'transaction_date', 'vendor', 'total', 'notes'),
        'rows': [(11, None, 7, date(2020, 6, 5), 'Reading Railroad',
                  253.99, 'Conducting business'),
                 (8, None, 5, date(2020, 5, 30), 'Water Works',
                  26.87, 'Tough loss'),
                 (10, None, 6, date(2020, 5, 10), 'Income Tax Board',
                  -123.00, 'Refund'),
                 (7, 2, 4, date(2020, 5, 4), 'JP Morgan Chance',
                  -109.21, 'Credit card payment'),
                 (6, None, 4, date(2020, 5, 1), 'Marvin Gardens',
                  6500.00, 'Expensive real estate'),
                 (5, None, 4, date(2020, 4, 25), 'Electric Company',
                  99.00, 'Electric bill'),
                 (9, None, 6, date(2020, 4, 20), 'Pennsylvania Avenue',
                  1600.00, 'Expensive house tour'),
                 (2, None, 2, date(2020, 4, 13), 'Top Left Corner',
                  1.00, 'Parking (thought it was free)'),
                 (4, None, 3, date(2020, 4, 5), 'Park Place',
                  65.00, 'One for the park; One for the place'),
                 (3, None, 3, date(2020, 3, 20), 'Boardwalk',
                  43.21, 'Merry-go-round'),
                 (12, None, 2, date(2020, 3, 10), 'Community Chest',
                  None, None)]
    }

    def test_initialization(self, transaction_db):
        assert transaction_db.table == 'credit_transactions'
        assert transaction_db.table_view == 'credit_transactions_view'
        assert transaction_db.user_id == 3

    @pytest.mark.parametrize(
        'card_ids, statement_ids, active, sort_order, fields, '
        'reference_entries',
        [[None, None, False, 'DESC', None,  # defaults
          view_reference['rows']],
         [None, None, False, 'DESC', view_reference['keys'][1:],
          view_reference['rows']],
         [(2, 3), None, False, 'DESC', view_reference['keys'][1:],
          [row for row in view_reference['rows'] if row[2] in (2, 3, 4, 5)]],
         [None, (3,), False, 'DESC', view_reference['keys'][1:],
          [row for row in view_reference['rows'] if row[2] == 3]],
         [None, None, True, 'DESC', view_reference['keys'][1:],
          [row for row in view_reference['rows'] if row[2] != 2]],
         [None, None, False, 'ASC', view_reference['keys'][1:],
          view_reference['rows'][::-1]]]
    )
    def test_get_entries(self, transaction_db, card_ids, statement_ids, active,
                         sort_order, fields, reference_entries):
        transactions = transaction_db.get_entries(card_ids, statement_ids,
                                                  active, sort_order, fields)
        if fields:
            self.assertMatchEntries(reference_entries, transactions,
                                    order=True)
        else:
            # Leaving fields unspecified acquires all fields from many tables
            self.assertContainEntries(reference_entries, transactions)

    @pytest.mark.parametrize(
        'transaction_id, fields, reference_entry',
        [[2, None,
          view_reference['rows'][7]],
         [3, None,
          view_reference['rows'][9]],
         [2, ('transaction_date', 'vendor'),
          (view_reference['rows'][7][0],
           view_reference['rows'][7][3],
           view_reference['rows'][7][4])],
         [2, ('vendor', 'total', 'notes'),  # use fields from the view
          (view_reference['rows'][7][0],
           view_reference['rows'][7][4],
           view_reference['rows'][7][5],
           view_reference['rows'][7][6])]]
    )
    def test_get_entry(self, transaction_db, transaction_id, fields,
                       reference_entry):
        transaction = transaction_db.get_entry(transaction_id, fields)
        if fields:
            self.assertMatchEntry(reference_entry, transaction)
        else:
            # Leaving fields unspecified acquires all fields from many tables
            self.assertContainEntry(reference_entry, transaction)

    @pytest.mark.parametrize(
        'transaction_id',
        [1,   # Not the logged in user
         13]  # Not in the database
    )
    def test_get_entry_invalid(self, transaction_db, transaction_id):
        with pytest.raises(NotFound):
            transaction_db.get_entry(transaction_id)

    @pytest.mark.parametrize(
        'mapping',
        [{'internal_transaction_id': None, 'statement_id': 4,
          'transaction_date': '2020-05-03', 'vendor': 'Baltic Avenue',
          'subtransactions': [{'test': 1}]},
         {'internal_transaction_id': 2, 'statement_id': 6,
          'transaction_date': '2020-05-03', 'vendor': 'Mediterranean Avenue',
          'subtransactions': [{'test': 1}]}]
    )
    @patch(
        'monopyly.credit.transactions.CreditSubtransactionHandler.add_entry',
        return_value='new subtransaction'
    )
    def test_add_entry(self, mock_method, app, transaction_db, mapping):
        transaction, subtransactions = transaction_db.add_entry(mapping)
        assert transaction['transaction_date'] == date(2020, 5, 3)
        assert subtransactions == ['new subtransaction']
        # Check that the entry was added
        query = ("SELECT COUNT(id) FROM credit_transactions"
                 " WHERE transaction_date = '2020-05-03'")
        self.assertQueryEqualsCount(app, query, 1)

    @pytest.mark.parametrize(
        'mapping, exception',
        [[{'internal_transaction_id': None, 'invalid_field': 'Test',
           'transaction_date': '2022-05-03', 'vendor': 'Baltic Avenue',
           'subtransactions': [{'test': 1}]},
          ValueError],
         [{'internal_transaction_id': 2, 'statement_id': 4,
           'transaction_date': '2022-05-03',
           'subtransactions': [{'test': 1}]},
          ValueError],
         [{'internal_transaction_id': 2, 'statement_id': 4,
           'transaction_date': '2022-05-03', 'vendor': 'Baltic Avenue'},
          KeyError]]
    )
    def test_add_entry_invalid(self, transaction_db, mapping, exception):
        with pytest.raises(exception):
            transaction_db.add_entry(mapping)

    def test_add_entry_invalid_user(self, app, transaction_db):
        query = ("SELECT COUNT(id) FROM credit_transactions"
                 " WHERE statement_id = 1")
        self.assertQueryEqualsCount(app, query, 1)
        with pytest.raises(NotFound):
            mapping = {
                'internal_transaction_id': 2,
                'statement_id': 1,
                'transaction_date': '2022-05-03',
                'vendor': 'Baltic Avenue',
                'subtransactions': [{'test': 1}],
            }
            transaction_db.add_entry(mapping)
        # Check that the transaction was not added to a different account
        self.assertQueryEqualsCount(app, query, 1)

    @pytest.mark.parametrize(
        'mapping',
        [{'internal_transaction_id': None, 'statement_id': 4,
          'transaction_date': '2022-05-03', 'subtransactions': [{'test': 1}]},
         {'transaction_date': '2022-05-03'}]
    )
    @patch(
        'monopyly.credit.transactions.CreditSubtransactionHandler.add_entry',
        return_value='new subtransaction'
    )
    def test_update_entry(self, mock_method, app, transaction_db, mapping):
        transaction, subtransactions = transaction_db.update_entry(5, mapping)
        assert transaction['transaction_date'] == date(2022, 5, 3)
        if 'subtransactions' in mapping:
            assert subtransactions == ['new subtransaction']
        # Check that the entry was updated
        query = ("SELECT COUNT(id) FROM credit_transactions"
                 " WHERE transaction_date = '2022-05-03'")
        self.assertQueryEqualsCount(app, query, 1)

    @pytest.mark.parametrize(
        'transaction_id, mapping, exception',
        [[1, {'statement_id': 1, 'transaction_date': '2020-05-03'},
          NotFound],  # another user
         [5, {'statement_id': 4, 'invalid_field': 'Test'},
          ValueError],
         [13, {'statement_id': 4, 'transaction_date': '2022-05-03'},
          NotFound]]   # nonexistent ID
    )
    def test_update_entry_invalid(self, transaction_db, transaction_id,
                                  mapping, exception):
        with pytest.raises(exception):
            transaction_db.update_entry(transaction_id, mapping)

    def test_update_entry_value(self, transaction_db):
        transaction = transaction_db.update_entry_value(2, 'transaction_date',
                                                        date(2022, 5, 3))[0]
        assert transaction['transaction_date'] == date(2022, 5, 3)

    @pytest.mark.parametrize(
        'entry_ids', [(4,), (4, 7)]
    )
    def test_delete_entries(self, app, transaction_db, entry_ids):
        transaction_db.delete_entries(entry_ids)
        # Check that the entries were deleted
        for entry_id in entry_ids:
            query = ("SELECT COUNT(id) FROM credit_transactions"
                    f" WHERE id = {entry_id}")
            self.assertQueryEqualsCount(app, query, 0)

    def test_delete_cascading_entries(self, app, transaction_db):
        transaction_db.delete_entries((2,))
        # Check that the cascading entries were deleted
        query = ("SELECT COUNT(id) FROM credit_subtransactions"
                f" WHERE transaction_id = 2")
        self.assertQueryEqualsCount(app, query, 0)

    @pytest.mark.parametrize(
        'entry_ids, exception',
        [[(1,), NotFound],    # should not be able to delete other user entries
         [(13,), NotFound]]   # should not be able to delete nonexistent entries
    )
    def test_delete_entries_invalid(self, transaction_db, entry_ids,
                                    exception):
        with pytest.raises(exception):
            transaction_db.delete_entries(entry_ids)


class TestCreditSubtransactionsHandler(TestHandler):

    # References only include entries accessible to the authorized login
    reference = {
        'keys': ('id', 'transaction_id', 'subtotal', 'note'),
        'rows': [(2, 2, 1.00, 'Parking (thought it was free)'),
                 (3, 3, 43.21, 'Merry-go-round'),
                 (4, 4, 30.00, 'One for the park'),
                 (5, 4, 35.00, 'One for the place'),
                 (6, 5, 99.00, 'Electric bill'),
                 (7, 6, 6500.00, 'Expensive real estate'),
                 (8, 7, -109.21, 'Credit card payment'),
                 (9, 8, 26.87, 'Tough loss'),
                 (10, 9, 1600.00, 'Expensive house tour'),
                 (11, 10, -123.00, 'Refund'),
                 (12, 11, 253.99, 'Conducting business')]
    }

    def test_initialization(self, subtransaction_db):
        assert subtransaction_db.table == 'credit_subtransactions'
        assert subtransaction_db.user_id == 3

    @pytest.mark.parametrize(
        'transaction_ids, fields, reference_entries',
        [[None, None,
          reference['rows']],
         [(2, 3, 4, 5), None,
          reference['rows'][:5]],
         [None, ('subtotal', 'note'),
          [(row[0], row[2], row[3]) for row in reference['rows']]],
         [(2, 3, 4, 5), ('subtotal', 'note'),
          [(row[0], row[2], row[3]) for row in reference['rows'][:5]]]]
    )
    def test_get_entries(self, subtransaction_db, transaction_ids, fields,
                         reference_entries):
        subtransactions = subtransaction_db.get_entries(transaction_ids,
                                                         fields)
        if fields:
            self.assertMatchEntries(reference_entries, subtransactions)
        else:
            # Leaving fields unspecified acquires all fields from many tables
            self.assertContainEntries(reference_entries, subtransactions)

    @pytest.mark.parametrize(
        'subtransaction_id, fields, reference_entry',
        [[2, None,
          reference['rows'][0]],
         [3, None,
          reference['rows'][1]],
         [4, None,
          reference['rows'][2]],
         [2, ('subtotal',),
          (reference['rows'][0][1], reference['rows'][0][2])]]
    )
    def test_get_entry(self, subtransaction_db, subtransaction_id, fields,
                       reference_entry):
        subtransaction = subtransaction_db.get_entry(subtransaction_id, fields)
        if fields:
            self.assertMatchEntry(reference_entry, subtransaction)
        else:
            # Leaving fields unspecified acquires all fields from many tables
            self.assertContainEntry(reference_entry, subtransaction)

    @pytest.mark.parametrize(
        'subtransaction_id, exception',
        [[1, NotFound],   # Not the logged in user
         [13, NotFound]]  # Not in the database
    )
    def test_get_entry_invalid(self, subtransaction_db, subtransaction_id,
                               exception):
        with pytest.raises(exception):
            subtransaction_db.get_entry(subtransaction_id)

    @pytest.mark.parametrize(
        'mapping',
        [{'transaction_id': 4, 'subtotal': 40.00,
          'note': 'TEST subtransaction',  # sibling subtransactions exist
          'tags': ['test tag']},
         {'transaction_id': 12, 'subtotal': 250.00,
          'note': 'TEST subtransaction',  # first subtransaction
          'tags': ['test tag']},
         {'transaction_id': 12, 'subtotal': 250.00,
          'note': 'TEST subtransaction',  # first subtransaction, no tags
          'tags': []}]
    )
    @patch('monopyly.credit.transactions.CreditTagHandler.update_tag_links')
    def test_add_entry(self, mock_method, app, subtransaction_db, mapping):
        subtransaction_db.add_entry(mapping)
        # Check that the entry was added
        query = ("SELECT COUNT(id) FROM credit_subtransactions"
                 " WHERE note = 'TEST subtransaction'")
        self.assertQueryEqualsCount(app, query, 1)

    @pytest.mark.parametrize(
        'mapping, exception',
        [[{'transaction_id': 4, 'invalid_field': 'Test', 'note': 'TEST',
           'tags': ['test tag']},
          ValueError],
         [{'transaction_id': 4, 'subtotal': 5.00, 'tags': ['test tag']},
          ValueError],
         [{'transaction_id': 13, 'subtotal': 5.00, 'note': 'TEST',
           'tags': ['test tag']},
          IntegrityError]]  # transaction does not exist
    )
    def test_add_entry_invalid(self, subtransaction_db, mapping, exception):
        with pytest.raises(exception):
            subtransaction_db.add_entry(mapping)

    @pytest.mark.skip(reason="never update subtransactions; only replace")
    @pytest.mark.parametrize(
        'subtransaction_id, mapping',
        [[2, {'transaction_id': 2, 'subtotal': 41.00, 'note': 'TEST update',
              'tags': ['test tag']}],
         [4, {'transaction_id': 4, 'subtotal': 58.90, 'note': 'TEST update'}],
         [4, {'transaction_id': 4, 'note': 'TEST update'}]]
    )
    def test_update_entry(self, app, subtransaction_db, subtransaction_id,
                          mapping):
        subtransaction = subtransaction_db.update_entry(subtransaction_id,
                                                        mapping)
        assert subtransaction['note'] == 'TEST update'
        # Check that the entry was updated
        query = ("SELECT COUNT(id) FROM credit_subtransactions"
                 " WHERE note = 'TEST update'")
        self.assertQueryEqualsCount(app, query, 1)

    @pytest.mark.skip(reason="never update subtransactions; only replace")
    @pytest.mark.parametrize(
        'subtransaction_id, mapping, exception',
        [[1, {'transaction_id': 1, 'note': 'TEST update'},  # another user
          NotFound],
         [2, {'transaction_id': 2, 'invalid_field': 'Test'},
          ValueError],
         [9, {'transaction_id': 2, 'note': 'TEST update'},  # nonexistent ID
          NotFound],
         [8, {'transaction_id': 9, 'note': 'TEST update'},  # nonexistent
          IntegrityError]]                                  # transaction ID
    )
    def test_update_entry_invalid(self, subtransaction_db, subtransaction_id,
                                  mapping, exception):
        with pytest.raises(exception):
            subtransaction_db.update_entry(subtransaction_id, mapping)

    def test_update_entry_value(self, subtransaction_db):
        subtransaction = subtransaction_db.update_entry_value(2, 'note',
                                                              'TEST update')
        assert subtransaction['note'] == 'TEST update'

    @pytest.mark.parametrize(
        'entry_ids', [(2,), (2, 3)]
    )
    def test_delete_entries(self, app, subtransaction_db, entry_ids):
        subtransaction_db.delete_entries(entry_ids)
        # Check that the entries were deleted
        for entry_id in entry_ids:
            query = ("SELECT COUNT(id) FROM credit_subtransactions"
                    f" WHERE id = {entry_id}")
            self.assertQueryEqualsCount(app, query, 0)

    @pytest.mark.parametrize(
        'entry_ids, exception',
        [[(1,), NotFound],   # should not be able to delete other user entries
         [(13,), NotFound]]  # should not be able to delete nonexistent entries
    )
    def test_delete_entries_invalid(self, subtransaction_db, entry_ids,
                                    exception):
        with pytest.raises(exception):
            subtransaction_db.delete_entries(entry_ids)


class TestSaveFormFunctions:

    @patch('monopyly.credit.transactions.CreditTransactionHandler')
    @patch('monopyly.credit.forms.CreditTransactionForm')
    def test_save_new_transaction(self, mock_form, mock_handler_type):
        # Mock the return values and data
        mock_method = mock_handler_type.return_value.add_entry
        mock_transaction = {'id': 0, 'internal_transaction_id': 0}
        mock_subtransactions = ['subtransactions']
        mock_method.return_value = ({'id': 0, 'internal_transaction_id': 0},
                                    ['subtransactions'])
        mock_form.transaction_data = {'key': 'test transaction data'}
        # Call the function and check for proper call signatures
        transaction, subtransactions = save_transaction(mock_form)
        mock_method.assert_called_once_with(mock_form.transaction_data)
        assert transaction == mock_transaction
        assert subtransactions == mock_subtransactions

    @patch('monopyly.credit.transactions.CreditTransactionHandler')
    @patch('monopyly.credit.forms.CreditTransactionForm')
    def test_save_updated_transaction(self, mock_form, mock_handler_type):
        # Mock the return values and data
        mock_method = mock_handler_type.return_value.update_entry
        mock_transaction = {'id': 0, 'internal_transaction_id': 0}
        mock_subtransactions = ['subtransactions']
        mock_method.return_value = (mock_transaction, mock_subtransactions)
        mock_form.transaction_data = {'key': 'test transaction data'}
        # Call the function and check for proper call signatures
        transaction_id = 2
        transaction, subtransactions = save_transaction(mock_form,
                                                        transaction_id)
        mock_method.assert_called_once_with(transaction_id,
                                            mock_form.transaction_data)
        assert transaction == mock_transaction
        assert subtransactions == mock_subtransactions

