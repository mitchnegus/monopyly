"""Tests for the credit module managing credit card accounts."""
import pytest
from werkzeug.exceptions import NotFound

from monopyly.credit.accounts import CreditAccountHandler
from ..helpers import TestHandler


@pytest.fixture
def account_db(app, client, auth):
    auth.login('mr.monopyly', 'MONOPYLY')
    with client:
        # Context variables (e.g. `g`) may be accessed only after response
        client.get('/')
        account_db = CreditAccountHandler()
        yield account_db


class TestCreditAccountHandler(TestHandler):

    # References only include entries accessible to the authorized login
    reference = {
        'keys': ('id', 'bank_id', 'statement_issue_day', 'statement_due_day'),
        'rows': [(2, 2, 10, 5),
                 (3, 3, 20, 12)]
    }

    def test_initialization(self, account_db):
        assert account_db.table == 'credit_accounts'
        assert account_db.user_id == 3

    @pytest.mark.parametrize(
        'bank_ids, fields, reference_entries',
        [[None, None,
          reference['rows']],
         [None, ('bank_id', 'statement_issue_day'),
          [row[:3] for row in reference['rows']]],
         [(2,), ('bank_id', 'statement_issue_day'),
          [row[:3] for row in reference['rows'][:1]]]]
    )
    def test_get_entries(self, account_db, bank_ids, fields,
                         reference_entries):
        accounts = account_db.get_entries(bank_ids, fields)
        if fields:
            self.assertMatchEntries(reference_entries, accounts)
        else:
            # Leaving fields unspecified acquires all fields from many tables
            self.assertContainEntries(reference_entries, accounts)

    @pytest.mark.parametrize(
        'account_id, fields, reference_entry',
        [[2, None,
          reference['rows'][0]],
         [3, None,
          reference['rows'][1]],
         [2, ('bank_id', 'statement_issue_day'),
          reference['rows'][0][:3]]]
    )
    def test_get_entry(self, account_db, account_id, fields, reference_entry):
        account = account_db.get_entry(account_id, fields)
        if fields:
            self.assertMatchEntry(reference_entry, account)
        else:
            # Leaving fields unspecified acquires all fields from many tables
            self.assertContainEntry(reference_entry, account)

    @pytest.mark.parametrize(
        'account_id, expectation',
        [[1, NotFound],  # Not the logged in user
         [4, NotFound]]  # Not in the database
    )
    def test_get_entry_invalid(self, account_db, account_id, expectation):
        with pytest.raises(expectation):
            account_db.get_entry(account_id)

    @pytest.mark.parametrize(
        'mapping',
        [{'bank_id': 2, 'statement_issue_day': 11, 'statement_due_day': 1},
         {'bank_id': 3, 'statement_issue_day': 21, 'statement_due_day': 1}]
    )
    def test_add_entry(self, app, account_db, mapping):
        account = account_db.add_entry(mapping)
        assert account['statement_due_day'] == 1
        # Check that the entry was added
        query = ("SELECT COUNT(id) FROM credit_accounts"
                 " WHERE statement_due_day = 1")
        self.assertQueryEqualsCount(app, query, 1)

    @pytest.mark.parametrize(
        'mapping',
        [{'bank_id': 2, 'invalid_field': 'Test', 'statement_due_day': 1},
         {'bank_id': 3, 'statement_issue_day': 21}]
    )
    def test_add_entry_invalid(self, account_db, mapping):
        with pytest.raises(ValueError):
            account_db.add_entry(mapping)

    @pytest.mark.parametrize(
        'mapping',
        [{'bank_id': 2, 'statement_issue_day': 10, 'statement_due_day': 1},
         {'bank_id': 2, 'statement_due_day': 1}]
    )
    def test_update_entry(self, app, account_db, mapping):
        account = account_db.update_entry(2, mapping)
        assert account['statement_due_day'] == 1
        # Check that the entry was updated
        query = ("SELECT COUNT(id) FROM credit_accounts"
                 " WHERE statement_due_day = 1")
        self.assertQueryEqualsCount(app, query, 1)

    @pytest.mark.parametrize(
        'account_id, mapping, expectation',
        [[1, {'bank_id': 2, 'statement_due_day': 1},  # another user
          NotFound],
         [2, {'bank_id': 2, 'invalid_field': 'Test'},
          ValueError],
         [4, {'bank_id': 2, 'statement_due_day': 1},  # nonexistent ID
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
            query = ("SELECT COUNT(id) FROM credit_accounts"
                    f" WHERE id = {entry_id}")
            self.assertQueryEqualsCount(app, query, 0)

    def test_delete_cascading_entries(self, app, account_db):
        account_db.delete_entries((3,))
        # Check that the cascading entries were deleted
        query = ("SELECT COUNT(id) FROM credit_cards"
                f" WHERE account_id = 3")
        self.assertQueryEqualsCount(app, query, 0)

    @pytest.mark.parametrize(
        'entry_ids, expectation',
        [[(1,), NotFound],   # should not be able to delete other user entries
         [(4,), NotFound]]   # should not be able to delete nonexistent entries
    )
    def test_delete_entries_invalid(self, account_db, entry_ids, expectation):
        with pytest.raises(expectation):
            account_db.delete_entries(entry_ids)

