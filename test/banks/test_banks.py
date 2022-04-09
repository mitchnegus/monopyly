"""Tests for the banking module managing banks."""
import unittest

import pytest
from werkzeug.exceptions import NotFound

from monopyly.db import get_db
from monopyly.banking.banks import BankHandler


@pytest.fixture
def bank_db(app, client, auth):
    auth.login('mr.monopyly', 'MONOPYLY')
    with client:
        # Context variables (e.g. `g`) may be accessed only after response
        client.get('/')
        bank_db = BankHandler()
        yield bank_db


class TestBankHandler:

    def assertQueryMatchSingle(self, query, reference):
        assert tuple(query) == reference

    def assertQueryMatchMultiple(self, query, reference):
        helper = unittest.TestCase()
        helper.assertCountEqual(map(tuple, query), reference)

    # Reference only includes entries accessible to the authorized login
    reference = {
        'keys': ('id', 'user_id', 'bank_name'),
        'rows': [(2, 3, 'Jail'),
                 (3, 3, 'TheBank')]
    }

    def test_initialization(self, bank_db):
        assert bank_db.table == 'banks'
        assert bank_db.user_id == 3

    @pytest.mark.parametrize(
        'bank_names, fields, entries',
        [[None, None,
          reference['rows']],
         [('Jail',), None,
          reference['rows'][0:1]],
         [None, ('bank_name',),
          [(row[0], row[2]) for row in reference['rows']]]]
    )
    def test_get_entries(self, bank_db, bank_names, fields, entries):
        banks = bank_db.get_entries(bank_names, fields)
        self.assertQueryMatchMultiple(banks, entries)

    @pytest.mark.parametrize(
        'bank_id, fields, entry',
        [[2, None,
          reference['rows'][0]],
         [3, None,
          reference['rows'][1]],
         [2, ('bank_name',),
          (reference['rows'][0][0], reference['rows'][0][2])]]
    )
    def test_get_entry(self, bank_db, bank_id, fields, entry):
        bank = bank_db.get_entry(bank_id, fields)
        self.assertQueryMatchSingle(bank, entry)

    @pytest.mark.parametrize(
        'bank_id, expectation',
        [[1, NotFound],  # Not the logged in user
         [5, NotFound]]  # Not in the database
    )
    def test_get_entry_invalid(self, bank_db, bank_id, expectation):
        with pytest.raises(expectation):
            bank_db.get_entry(bank_id)

    def test_add_entry(self, app, bank_db):
        bank = bank_db.add_entry({'user_id': 3,
                                  'bank_name': 'JP Morgan Chance'})
        assert bank['bank_name'] == 'JP Morgan Chance'
        # Check that the entry was added
        with app.app_context():
            db = get_db()
            count = db.execute("SELECT COUNT(id) FROM banks"
                               " WHERE bank_name LIKE '%Chance'").fetchone()[0]
            assert count == 1

    def test_add_entry_invalid(self, bank_db):
        with pytest.raises(ValueError):
            bank_db.add_entry({'user_id': 3, 'invalid_field': 'Test'})

    @pytest.mark.parametrize(
        'mapping',
        [{'user_id': 3, 'bank_name': 'Corner Jail'},
         {'bank_name': 'Corner Jail'}]
    )
    def test_update_entry(self, app, bank_db, mapping):
        bank = bank_db.update_entry(2, mapping)
        assert bank['bank_name'] == 'Corner Jail'
        # Check that the entry was updated
        with app.app_context():
            db = get_db()
            count = db.execute("SELECT COUNT(id) FROM banks"
                               " WHERE bank_name LIKE 'Corner%'").fetchone()[0]
            assert count == 1

    @pytest.mark.parametrize(
        'bank_id, mapping, expectation',
        [[1, {'user_id': 3, 'bank_name': 'Test'}, NotFound],  # another user
         [2, {'user_id': 3, 'invalid_field': 'Test'}, ValueError],
         [5, {'user_id': 3, 'bank_name': 'Test'}, NotFound]]  # nonexistent ID
    )
    def test_update_entry_invalid(self, bank_db, bank_id, mapping,
                                  expectation):
        with pytest.raises(expectation):
            bank_db.update_entry(bank_id, mapping)

    @pytest.mark.parametrize(
        'entry_ids', [(2,), (2, 3)]
    )
    def test_delete_entries(self, app, bank_db, entry_ids):
        bank_db.delete_entries(entry_ids)
        # Check that the entries were deleted
        with app.app_context():
            db = get_db()
            for entry_id in entry_ids:
                query = ("SELECT COUNT(id) FROM banks"
                        f" WHERE id == {entry_id}")
                count = db.execute("SELECT COUNT(id) FROM banks"
                                  f" WHERE id == {entry_id}").fetchone()[0]
                assert count == 0

    def test_delete_entries_invalid(self, bank_db):
        with pytest.raises(NotFound):
            bank_db.delete_entries((1,))

