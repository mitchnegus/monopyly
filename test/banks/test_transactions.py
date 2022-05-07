"""Tests for the banking module managing transactions/subtransactions."""
from datetime import date
from unittest.mock import patch
from sqlite3 import IntegrityError

import pytest
from werkzeug.exceptions import NotFound

from monopyly.banking.transactions import (
    BankTransactionHandler, BankSubtransactionHandler
)
from ..helpers import TestHandler


@pytest.fixture
def transaction_db(app, client, auth):
    auth.login('mr.monopyly', 'MONOPYLY')
    with client:
        # Context variables (e.g. `g`) may be accessed only after response
        client.get('/')
        transaction_db = BankTransactionHandler()
        yield transaction_db


@pytest.fixture
def subtransaction_db(app, client, auth):
    auth.login('mr.monopyly', 'MONOPYLY')
    with client:
        # Context variables (e.g. `g`) may be accessed only after response
        client.get('/')
        subtransaction_db = BankSubtransactionHandler()
        yield subtransaction_db


class TestBankTransactionHandler(TestHandler):

    # References only include entries accessible to the authorized login
    #   - ordered by date (most recent first)
    reference = {
        'keys': ('id', 'internal_transaction_id', 'account_id',
                 'transaction_date'),
        'rows': [(8, None, 4, date(2020, 5, 7)),
                 (7, None, 4, date(2020, 5, 6)),
                 (4, None, 2, date(2020, 5, 6)),
                 (6, 1, 3, date(2020, 5, 5)),
                 (3, 1, 2, date(2020, 5, 5)),
                 (5, 2, 3, date(2020, 5, 4)),
                 (2, None, 2, date(2020, 5, 4))]
    }
    view_reference = {
        'keys': ('id', 'internal_transaction_id', 'account_id',
                 'transaction_date', 'total', 'notes'),
        'rows': [(8, None, 4, date(2020, 5, 7), None, None),
                 (7, None, 4, date(2020, 5, 6), 200.00,
                  '"Go" Corner ATM deposit'),
                 (4, None, 2, date(2020, 5, 6), 58.90,
                  'What else is there to do in Jail?'),
                 (6, 1, 3, date(2020, 5, 5), -300.00,
                  'Transfer out'),
                 (3, 1, 2, date(2020, 5, 5), 300.00,
                  'Transfer in'),
                 (5, 2, 3, date(2020, 5, 4), -109.21,
                  'Credit card payment'),
                 (2, None, 2, date(2020, 5, 4), 85.00,
                  'Jail subtransaction 1; Jail subtransaction 2')]
    }

    def test_initialization(self, transaction_db):
        assert transaction_db.table == 'bank_transactions'
        assert transaction_db.table_view == 'bank_transactions_view'
        assert transaction_db.user_id == 3

    @pytest.mark.parametrize(
        'account_ids, active, sort_order, fields, reference_entries',
        [[None, False, 'DESC', None,  # defaults
          view_reference['rows']],
         [None, False, 'DESC', view_reference['keys'][1:],
          view_reference['rows']],
         [(2, 3), False, 'DESC', view_reference['keys'][1:],
          view_reference['rows'][2:]],
         [None, True, 'DESC', view_reference['keys'][1:],  # account 3 inactive
          [row for row in view_reference['rows'] if row[2] != 3]],
         [None, False, 'ASC', view_reference['keys'][1:],
          view_reference['rows'][::-1]]]
    )
    def test_get_entries(self, transaction_db, account_ids, active, sort_order,
                         fields, reference_entries):
        transactions = transaction_db.get_entries(account_ids, active,
                                                  sort_order, fields)
        if fields:
            self.assertMatchEntries(reference_entries, transactions,
                                    order=True)
        else:
            # Leaving fields unspecified acquires all fields from many tables
            self.assertContainEntries(reference_entries, transactions)

    @pytest.mark.parametrize(
        'transaction_id, fields, reference_entry',
        [[2, None,
          view_reference['rows'][6]],
         [3, None,
          view_reference['rows'][4]],
         [2, ('account_id', 'transaction_date'),
          (view_reference['rows'][6][0],
           view_reference['rows'][6][2],
           view_reference['rows'][6][3])],
         [2, ('total', 'notes'),  # use fields from the view
          (view_reference['rows'][6][0],
           view_reference['rows'][6][4],
           view_reference['rows'][6][5])]]
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
        [1,  # Not the logged in user
         9]  # Not in the database
    )
    def test_get_entry_invalid(self, transaction_db, transaction_id):
        with pytest.raises(NotFound):
            transaction_db.get_entry(transaction_id)

    @pytest.mark.parametrize(
        'mapping',
        [{'internal_transaction_id': None, 'account_id': 3,
          'transaction_date': '2022-05-08', 'subtransactions': [{'test': 1}]},
         {'internal_transaction_id': 2, 'account_id': 3,
          'transaction_date': '2022-05-08', 'subtransactions': [{'test': 1}]}]
    )
    @patch('monopyly.banking.transactions.BankSubtransactionHandler.add_entry',
           return_value='new subtransaction')
    def test_add_entry(self, mock_method, app, transaction_db, mapping):
        transaction, subtransactions = transaction_db.add_entry(mapping)
        assert transaction['transaction_date'] == date(2022, 5, 8)
        assert subtransactions == ['new subtransaction']
        # Check that the entry was added
        query = ("SELECT COUNT(id) FROM bank_transactions"
                 " WHERE transaction_date = '2022-05-08'")
        self.assertQueryEqualsCount(app, query, 1)

    @pytest.mark.parametrize(
        'mapping, expectation',
        [[{'internal_transaction_id': None, 'invalid_field': 'Test',
           'transaction_date': '2022-05-08',
           'subtransactions': [{'test': 1}]},
          ValueError],
         [{'internal_transaction_id': 2, 'account_id': 3,
           'subtransactions': [{'test': 1}]},
          ValueError],
         [{'internal_transaction_id': 2, 'account_id': 3,
           'transaction_date': '2022-05-08'},
          KeyError]]
    )
    def test_add_entry_invalid(self, transaction_db, mapping, expectation):
        with pytest.raises(expectation):
            transaction_db.add_entry(mapping)

    @pytest.mark.parametrize(
        'mapping',
        [{'internal_transaction_id': None, 'account_id': 3,
          'transaction_date': '2022-05-08', 'subtransactions': [{'test': 1}]},
         {'transaction_date': '2022-05-08'}]
    )
    @patch('monopyly.banking.transactions.BankSubtransactionHandler.add_entry',
           return_value='new subtransaction')
    def test_update_entry(self, mock_method, app, transaction_db, mapping):
        transaction, subtransactions = transaction_db.update_entry(5, mapping)
        assert transaction['transaction_date'] == date(2022, 5, 8)
        if 'subtransactions' in mapping:
            assert subtransactions == ['new subtransaction']
        # Check that the entry was updated
        query = ("SELECT COUNT(id) FROM bank_transactions"
                 " WHERE transaction_date = '2022-05-08'")
        self.assertQueryEqualsCount(app, query, 1)

    @pytest.mark.parametrize(
        'transaction_id, mapping, expectation',
        [[1, {'account_id': 1, 'transaction_date': '2020-05-08'},
          NotFound],  # another user
         [5, {'account_id': 3, 'invalid_field': 'Test'},
          ValueError],
         [9, {'account_id': 3, 'transaction_date': '2022-05-08'},
          NotFound]]   # nonexistent ID
    )
    def test_update_entry_invalid(self, transaction_db, transaction_id,
                                  mapping, expectation):
        with pytest.raises(expectation):
            transaction_db.update_entry(transaction_id, mapping)

    @pytest.mark.parametrize(
        'entry_ids', [(4,), (4, 7)]
    )
    def test_delete_entries(self, app, transaction_db, entry_ids):
        transaction_db.delete_entries(entry_ids)
        # Check that the entries were deleted
        for entry_id in entry_ids:
            query = ("SELECT COUNT(id) FROM bank_transactions"
                    f" WHERE id = {entry_id}")
            self.assertQueryEqualsCount(app, query, 0)

    def test_delete_cascading_entries(self, app, transaction_db):
        transaction_db.delete_entries((2,))
        # Check that the cascading entries were deleted
        query = ("SELECT COUNT(id) FROM bank_subtransactions"
                f" WHERE transaction_id = 2")
        self.assertQueryEqualsCount(app, query, 0)

    @pytest.mark.parametrize(
        'entry_ids, expectation',
        [[(1,), NotFound],   # should not be able to delete other user entries
         [(9,), NotFound]]   # should not be able to delete nonexistent entries
    )
    def test_delete_entries_invalid(self, transaction_db, entry_ids,
                                    expectation):
        with pytest.raises(expectation):
            transaction_db.delete_entries(entry_ids)


class TestBankSubtransactionsHandler(TestHandler):

    # References only include entries accessible to the authorized login
    reference = {
        'keys': ('id', 'transaction_id', 'subtotal', 'note'),
        'rows': [(2, 2, 42.00, 'Jail subtransaction 1'),
                 (3, 2, 43.00, 'Jail subtransaction 2'),
                 (4, 3, 300.00, 'Transfer in'),
                 (5, 4, 58.90, 'What else is there to do in Jail?'),
                 (6, 5, -109.21, 'Credit card payment'),
                 (7, 6, -300.00, 'Transfer out'),
                 (8, 7, 200.00, '"Go" Corner ATM deposit')]
    }

    def test_initialization(self, subtransaction_db):
        assert subtransaction_db.table == 'bank_subtransactions'
        assert subtransaction_db.user_id == 3

    @pytest.mark.parametrize(
        'transaction_ids, fields, reference_entries',
        [[None, None,
          reference['rows']],
         [(2, 3, 4), None,
          reference['rows'][:4]],
         [None, ('subtotal', 'note'),
          [(row[0], row[2], row[3]) for row in reference['rows']]],
         [(2, 3, 4), ('subtotal', 'note'),
          [(row[0], row[2], row[3]) for row in reference['rows'][:4]]]]
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
        'subtransaction_id, expectation',
        [[1, NotFound],  # Not the logged in user
         [9, NotFound]]  # Not in the database
    )
    def test_get_entry_invalid(self, subtransaction_db, subtransaction_id,
                               expectation):
        with pytest.raises(expectation):
            subtransaction_db.get_entry(subtransaction_id)

    @pytest.mark.parametrize(
        'mapping',
        [{'transaction_id': 2, 'subtotal': 43.00,
          'note': 'TEST subtransaction'},  # sibling subtransactions exist
         {'transaction_id': 8, 'subtotal': 123.00,
          'note': 'TEST subtransaction'}]  # first subtransaction
    )
    def test_add_entry(self, app, subtransaction_db, mapping):
        subtransaction_db.add_entry(mapping)
        # Check that the entry was added
        query = ("SELECT COUNT(id) FROM bank_subtransactions"
                 " WHERE note = 'TEST subtransaction'")
        self.assertQueryEqualsCount(app, query, 1)

    @pytest.mark.parametrize(
        'mapping, expectation',
        [[{'transaction_id': 2, 'invalid_field': 'Test', 'note': 'TEST'},
          ValueError],
         [{'transaction_id': 2, 'subtotal': 5.00,},
          ValueError],
         [{'transaction_id': 9, 'subtotal': 5.00, 'note': 'TEST'},
          IntegrityError]]
    )
    def test_add_entry_invalid(self, subtransaction_db, mapping, expectation):
        with pytest.raises(expectation):
            subtransaction_db.add_entry(mapping)

    @pytest.mark.parametrize(
        'subtransaction_id, mapping',
        [[2, {'transaction_id': 2, 'subtotal': 41.00, 'note': 'TEST update'}],
         [4, {'transaction_id': 4, 'subtotal': 58.90, 'note': 'TEST update'}],
         [4, {'transaction_id': 4, 'note': 'TEST update'}]]
    )
    def test_update_entry(self, app, subtransaction_db, subtransaction_id,
                          mapping):
        subtransaction_db.update_entry(subtransaction_id, mapping)
        # Check that the entry was updated
        query = ("SELECT COUNT(id) FROM bank_subtransactions"
                 " WHERE note = 'TEST update'")
        self.assertQueryEqualsCount(app, query, 1)

    @pytest.mark.parametrize(
        'subtransaction_id, mapping, expectation',
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
                                  mapping, expectation):
        with pytest.raises(expectation):
            subtransaction_db.update_entry(subtransaction_id, mapping)

    @pytest.mark.parametrize(
        'entry_ids', [(2,), (2, 3)]
    )
    def test_delete_entries(self, app, subtransaction_db, entry_ids):
        subtransaction_db.delete_entries(entry_ids)
        # Check that the entries were deleted
        for entry_id in entry_ids:
            query = ("SELECT COUNT(id) FROM bank_subtransactions"
                    f" WHERE id = {entry_id}")
            self.assertQueryEqualsCount(app, query, 0)

    @pytest.mark.parametrize(
        'entry_ids, expectation',
        [[(1,), NotFound],   # should not be able to delete other user entries
         [(9,), NotFound]]   # should not be able to delete nonexistent entries
    )
    def test_delete_entries_invalid(self, subtransaction_db, entry_ids,
                                    expectation):
        with pytest.raises(expectation):
            subtransaction_db.delete_entries(entry_ids)

