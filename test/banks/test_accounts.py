"""Tests for the banking module managing bank accounts."""
import unittest

import pytest
from werkzeug.exceptions import Forbidden, NotFound

from monopyly.db import get_db
from monopyly.banking.accounts import (
    BankAccountTypeHandler, BankAccountHandler
)
from ..helpers import TestHandler


@pytest.fixture
def account_type_db(app, client, auth):
    auth.login('mr.monopyly', 'MONOPYLY')
    with client:
        # Context variables (e.g. `g`) may be accessed only after response
        client.get('/')
        account_type_db = BankAccountTypeHandler()
        yield account_type_db


@pytest.fixture
def account_db(app, client, auth):
    auth.login('mr.monopyly', 'MONOPYLY')
    with client:
        # Context variables (e.g. `g`) may be accessed only after response
        client.get('/')
        account_db = BankAccountHandler()
        yield account_db


class TestBankAccountTypeHandler(TestHandler):

    # References only include entries accessible to the authorized login
    reference = {
        'keys': ('id', 'user_id', 'type_name', 'type_abbreviation'),
        'rows': [(1, 0, 'Savings', None),
                 (2, 0, 'Checking', None),
                 (3, 0, 'Certificate of Deposit', 'CD'),
                 (5, 3, 'Trustworthy Player', 'Trust'),
                 (6, 3, 'Cooperative Enjoyment Depository', 'Mutual FunD')]
    }
    view_reference = {
        'keys': ('id', 'user_id', 'type_name', 'type_common_name'),
        'rows': [(1, 0, 'Savings', 'Savings'),
                 (2, 0, 'Checking', 'Checking'),
                 (3, 0, 'Certificate of Deposit', 'CD'),
                 (5, 3, 'Trustworthy Player', 'Trust'),
                 (6, 3, 'Cooperative Enjoyment Depository', 'Mutual FunD')]
    }

    def test_initialization(self, account_type_db):
        assert account_type_db.table == 'bank_account_types'
        assert account_type_db.table_view == 'bank_account_types_view'
        assert account_type_db.user_id == 3

    @pytest.mark.parametrize(
        'fields, reference_entries',
        [[None,
          view_reference['rows']],
         [('type_name', 'type_common_name'),  # use the fields from the view
          [(row[0], row[2], row[3]) for row in view_reference['rows']]]]
    )
    def test_get_entries(self, account_type_db, fields, reference_entries):
        account_types = account_type_db.get_entries(fields)
        self.assertMatchEntries(reference_entries, account_types)

    @pytest.mark.parametrize(
        'bank_id, reference_entries',
        [[2, view_reference['rows'][:2]],
         [3, view_reference['rows'][2:3]]]
    )
    def test_get_types_for_bank(self, account_type_db, bank_id,
                                reference_entries):
        account_types = account_type_db.get_types_for_bank(bank_id)
        self.assertMatchEntries(reference_entries, account_types)

    @pytest.mark.parametrize(
        'account_type_id, fields, reference_entry',
        [[2, None,
          view_reference['rows'][1]],
         [3, None,
          view_reference['rows'][2]],
         [2, ('type_name',),
          (view_reference['rows'][1][0], view_reference['rows'][1][2],)],
         [3, ('type_name', 'type_common_name'),  # use the fields from the view
          (view_reference['rows'][2][0],
           view_reference['rows'][2][2],
           view_reference['rows'][2][3])]]
    )
    def test_get_entry(self, account_type_db, account_type_id, fields,
                       reference_entry):
        account_type = account_type_db.get_entry(account_type_id, fields)
        self.assertMatchEntry(reference_entry, account_type)

    @pytest.mark.parametrize(
        'account_type_id, expectation',
        [[4, NotFound],  # Not the logged in user
         [7, NotFound]]  # Not in the database
    )
    def test_get_entry_invalid(self, account_type_db, account_type_id,
                               expectation):
        with pytest.raises(expectation):
            account_type_db.get_entry(account_type_id)

    @pytest.mark.parametrize(
        'type_name, type_abbreviation, fields, reference_entry',
        [['Checking', None, None,
          reference['rows'][1]],
         ['Certificate of Deposit', None, None,
          reference['rows'][2]],
         [None, 'CD', None,
          reference['rows'][2]],
         [None, 'Trust', None,
          reference['rows'][3]],
         ['Certificate of Deposit', 'CD', None,
          reference['rows'][2]],
         [None, 'CD', ('type_name', 'type_abbreviation'),
          (reference['rows'][2][0],
           reference['rows'][2][2],
           reference['rows'][2][3])]]
    )
    def test_find_account_type(self, account_type_db, type_name,
                               type_abbreviation, fields, reference_entry):
        account_type = account_type_db.find_account_type(type_name,
                                                         type_abbreviation,
                                                         fields)
        self.assertMatchEntry(reference_entry, account_type)

    @pytest.mark.parametrize(
        'type_name, type_abbreviation, fields',
        [('Certificate of Deposit', 'CoD', None),
         (None, None, None)]
    )
    def test_find_account_type_none_exist(self, account_type_db, type_name,
                                          type_abbreviation, fields):
        account_type = account_type_db.find_account_type(type_name,
                                                         type_abbreviation,
                                                         fields)
        assert account_type is None

    @pytest.mark.parametrize(
        'mapping',
        [{'user_id': 3, 'type_name': 'Well Stocked Hand',
          'type_abbreviation': None},
         {'user_id': 3, 'type_name': 'Well Stocked Hand',
          'type_abbreviation': 'Paper'}]
    )
    def test_add_entry(self, app, account_type_db, mapping):
        account_type = account_type_db.add_entry(mapping)
        assert account_type['type_name'] == 'Well Stocked Hand'
        # Check that the entry was added
        query = ("SELECT COUNT(id) FROM bank_account_types"
                 " WHERE type_name LIKE '%Hand'")
        self.assertQueryEqualsCount(app, query, 1)

    @pytest.mark.parametrize(
        'mapping',
        [{'user_id': 3, 'invalid_field': 'Test', 'type_abbreviation': None},
         {'user_id': 3, 'type_name': 'Test'}]
    )
    def test_add_entry_invalid(self, account_type_db, mapping):
        with pytest.raises(ValueError):
            account_type_db.add_entry(mapping)

    @pytest.mark.parametrize(
        'mapping',
        [{'user_id': 3, 'type_name': 'Trustworthy Friend',
          'type_abbreviation': 'Trust'},
         {'type_name': 'Trustworthy Friend'}]
    )
    def test_update_entry(self, app, account_type_db, mapping):
        account_type = account_type_db.update_entry(5, mapping)
        assert account_type['type_name'] == 'Trustworthy Friend'
        # Check that the entry was updated
        query = ("SELECT COUNT(id) FROM bank_account_types"
                 " WHERE type_name LIKE '%Friend'")
        self.assertQueryEqualsCount(app, query, 1)

    @pytest.mark.parametrize(
        'account_type_id, mapping, expectation',
        [[2, {'user_id': 3, 'type_name': 'Test'}, Forbidden], # another user
         [5, {'user_id': 3, 'invalid_field': 'Test'}, ValueError],
         [7, {'user_id': 3, 'type_name': 'Test'}, NotFound]]  # nonexistent ID
    )
    def test_update_entry_invalid(self, account_type_db, account_type_id,
                                  mapping, expectation):
        with pytest.raises(expectation):
            account_type_db.update_entry(account_type_id, mapping)

    @pytest.mark.parametrize(
        'entry_ids', [(5,), (5, 6)]
    )
    def test_delete_entries(self, app, account_type_db, entry_ids):
        account_type_db.delete_entries(entry_ids)
        # Check that the entries were deleted
        for entry_id in entry_ids:
            query = ("SELECT COUNT(id) FROM bank_account_types"
                    f" WHERE id = {entry_id}")
            self.assertQueryEqualsCount(app, query, 0)

    @pytest.mark.parametrize(
        'entry_ids, expectation',
        [[(1,), Forbidden],  # should not be able to delete common entries
         [(4,), NotFound],   # should not be able to delete other user entries
         [(7,), NotFound]]   # should not be able to delete nonexistent entries
    )
    def test_delete_entries_invalid(self, account_type_db, entry_ids,
                                    expectation):
        with pytest.raises(expectation):
            account_type_db.delete_entries(entry_ids)


class TestBankAccountHandler(TestHandler):

    # References only include entries accessible to the authorized login
    reference = {
        'keys': ('id', 'bank_id', 'account_type_id', 'last_four_digits',
                 'active'),
        'rows': [(2, 2, 1, '5556', 1),
                 (3, 2, 2, '5557', 0),
                 (4, 3, 3, '5558', 1)]
    }

    def test_initialization(self, account_db):
        assert account_db.table == 'bank_accounts'
        assert account_db.table_view == 'bank_accounts_view'
        assert account_db.user_id == 3

    @pytest.mark.parametrize(
        'mapping',
        [{'bank_id': 2, 'account_type_id': 2, 'last_four_digits': '6666',
          'active': 1},
         {'bank_id': 3, 'account_type_id': 5, 'last_four_digits': '6666',
          'active': 0}]
    )
    def test_add_entry(self, app, account_db, mapping):
        account = account_db.add_entry(mapping)
        assert account['last_four_digits'] == '6666'
        # Check that the entry was added
        query = ("SELECT COUNT(id) FROM bank_accounts"
                 " WHERE last_four_digits = '6666'")
        self.assertQueryEqualsCount(app, query, 1)

    @pytest.mark.parametrize(
        'mapping',
        [{'bank_id': 2, 'invalid_field': 'Test', 'last_four_digits': 6000,
          'active': 1},
         {'bank_id': 3, 'account_type_id': 5, 'last_four_digits': 6666}]
    )
    def test_add_entry_invalid(self, account_db, mapping):
        with pytest.raises(ValueError):
            account_db.add_entry(mapping)

    @pytest.mark.parametrize(
        'mapping',
        [{'bank_id': 3, 'account_type_id': 1, 'last_four_digits': '6666',
          'active': 1},
         {'bank_id': 3, 'last_four_digits': '6666'}]
    )
    def test_update_entry(self, app, account_db, mapping):
        account = account_db.update_entry(2, mapping)
        assert account['last_four_digits'] == '6666'
        # Check that the entry was updated
        query = ("SELECT COUNT(id) FROM bank_accounts"
                 " WHERE last_four_digits = 6666")
        self.assertQueryEqualsCount(app, query, 1)

    @pytest.mark.parametrize(
        'account_id, mapping, expectation',
        [[1, {'bank_id': 2, 'last_four_digits': '6666'},  # another user
          NotFound],
         [2, {'bank_id': 2, 'invalid_field': 'Test'},
          ValueError],
         [5, {'bank_id': 2, 'last_four_digits': '6666'},  # nonexistent ID
          NotFound]]
    )
    def test_update_entry_invalid(self, account_db, account_id, mapping,
                                  expectation):
        with pytest.raises(expectation):
            account_db.update_entry(account_id, mapping)

    @pytest.mark.parametrize(
        'entry_ids', [(2,), (2, 3)]
    )
    def test_delete_entries(self, app, account_db, entry_ids):
        account_db.delete_entries(entry_ids)
        # Check that the entries were deleted
        for entry_id in entry_ids:
            query = ("SELECT COUNT(id) FROM bank_accounts"
                    f" WHERE id = {entry_id}")
            self.assertQueryEqualsCount(app, query, 0)

    @pytest.mark.skip(reason="needs transactions to cause cascading delete")
    def test_delete_cascading_entries(self):
        pass

    @pytest.mark.parametrize(
        'entry_ids, expectation',
        [[(1,), NotFound],   # should not be able to delete other user entries
         [(5,), NotFound]]   # should not be able to delete nonexistent entries
    )
    def test_delete_entries_invalid(self, account_db, entry_ids, expectation):
        with pytest.raises(expectation):
            account_db.delete_entries(entry_ids)

