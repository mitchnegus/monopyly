"""Tests for the banking module managing banks."""
import pytest
from werkzeug.exceptions import NotFound

from monopyly.banking.banks import BankHandler
from ..helpers import TestHandler


@pytest.fixture
def bank_db(client_context):
    bank_db = BankHandler()
    yield bank_db


class TestBankHandler(TestHandler):

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
        'bank_names, fields, reference_entries',
        [[None, None,
          reference['rows']],
         [('Jail',), None,
          reference['rows'][0:1]],
         [None, ('bank_name',),
          [(row[0], row[2]) for row in reference['rows']]]]
    )
    def test_get_entries(self, bank_db, bank_names, fields, reference_entries):
        banks = bank_db.get_entries(bank_names, fields)
        self.assertMatchEntries(reference_entries, banks)

    @pytest.mark.parametrize(
        'bank_id, fields, reference_entry',
        [[2, None,
          reference['rows'][0]],
         [3, None,
          reference['rows'][1]],
         [2, ('bank_name',),
          (reference['rows'][0][0], reference['rows'][0][2])]]
    )
    def test_get_entry(self, bank_db, bank_id, fields, reference_entry):
        bank = bank_db.get_entry(bank_id, fields)
        self.assertMatchEntry(reference_entry, bank)

    @pytest.mark.parametrize(
        'bank_id, exception',
        [[1, NotFound],  # Not the logged in user
         [5, NotFound]]  # Not in the database
    )
    def test_get_entry_invalid(self, bank_db, bank_id, exception):
        with pytest.raises(exception):
            bank_db.get_entry(bank_id)

    def test_add_entry(self, app, bank_db):
        bank = bank_db.add_entry({'user_id': 3,
                                  'bank_name': 'JP Morgan Chance'})
        assert bank.bank_name == 'JP Morgan Chance'
        # Check that the entry was added
        query = ("SELECT COUNT(id) FROM banks"
                 " WHERE bank_name LIKE '%Chance'")
        self.assertQueryEqualsCount(app, query, 1)

    @pytest.mark.parametrize(
        'mapping',
        [{'user_id': 3, 'invalid_field': 'Test'},
         {'user_id': 3}]
    )
    def test_add_entry_invalid(self, bank_db, mapping):
        with pytest.raises(ValueError):
            bank_db.add_entry(mapping)

    def test_add_entry_invalid_user(self, app, bank_db):
        query = ("SELECT COUNT(id) FROM banks"
                 " WHERE user_id = 1")
        self.assertQueryEqualsCount(app, query, 1)
        with pytest.raises(NotFound):
            mapping = {
                'user_id': 1,
                'bank_name': 'JP Morgan Chance',
            }
            bank_db.add_entry(mapping)
        # Check that the transaction was not added to a different account
        self.assertQueryEqualsCount(app, query, 1)

    @pytest.mark.parametrize(
        'mapping',
        [{'user_id': 3, 'bank_name': 'Corner Jail'},
         {'bank_name': 'Corner Jail'}]
    )
    def test_update_entry(self, app, bank_db, mapping):
        bank = bank_db.update_entry(2, mapping)
        assert bank.bank_name == 'Corner Jail'
        # Check that the entry was updated
        query = ("SELECT COUNT(id) FROM banks "
                 " WHERE bank_name LIKE 'Corner%'")
        self.assertQueryEqualsCount(app, query, 1)

    @pytest.mark.parametrize(
        'bank_id, mapping, exception',
        [[1, {'user_id': 3, 'bank_name': 'Test'}, NotFound],  # another user
         [2, {'user_id': 3, 'invalid_field': 'Test'}, ValueError],
         [5, {'user_id': 3, 'bank_name': 'Test'}, NotFound]]  # nonexistent ID
    )
    def test_update_entry_invalid(self, bank_db, bank_id, mapping,
                                  exception):
        with pytest.raises(exception):
            bank_db.update_entry(bank_id, mapping)

    def test_update_entry_value(self, bank_db):
        bank = bank_db.update_entry_value(2, 'bank_name', 'Corner Jail')
        assert bank.bank_name == 'Corner Jail'

    @pytest.mark.parametrize(
        'entry_ids', [(2,), (2, 3)]
    )
    def test_delete_entries(self, app, bank_db, entry_ids):
        bank_db.delete_entries(entry_ids)
        # Check that the entries were deleted
        for entry_id in entry_ids:
            query = ("SELECT COUNT(id) FROM banks"
                    f" WHERE id = {entry_id}")
            self.assertQueryEqualsCount(app, query, 0)

    def test_delete_cascading_entries(self, app, bank_db):
        bank_db.delete_entries((3,))
        # Check that the cascading entries were deleted
        query = ("SELECT COUNT(id) FROM bank_accounts"
                f" WHERE bank_id = 3")
        self.assertQueryEqualsCount(app, query, 0)

    @pytest.mark.parametrize(
        'entry_ids, exception',
        [[(1,), NotFound],   # should not be able to delete other user entries
         [(4,), NotFound]]   # should not be able to delete nonexistent entries
    )
    def test_delete_entries_invalid(self, bank_db, entry_ids, exception):
        with pytest.raises(exception):
            bank_db.delete_entries(entry_ids)

