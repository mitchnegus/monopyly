"""Tests for the credit module managing credit card accounts."""
import pytest
from werkzeug.exceptions import NotFound
from sqlalchemy.exc import IntegrityError

from monopyly.database.models import CreditAccount, CreditCard
from monopyly.credit.accounts import CreditAccountHandler
from ..helpers import TestHandler


@pytest.fixture
def account_handler(client_context):
    return CreditAccountHandler


class TestCreditAccountHandler(TestHandler):

    # References only include entries accessible to the authorized login
    db_reference = [
        CreditAccount(id=2, bank_id=2, statement_issue_day=10,
                      statement_due_day=5),
        CreditAccount(id=3, bank_id=3, statement_issue_day=6,
                      statement_due_day=27),
    ]

    def test_initialization(self, account_handler):
        assert account_handler.model == CreditAccount
        assert account_handler.table == 'credit_accounts'
        assert account_handler.user_id == 3

    @pytest.mark.parametrize(
        'bank_ids, reference_entries',
        [[None, db_reference],
         [(2,), db_reference[:1]]]
    )
    def test_get_accounts(self, account_handler, bank_ids, reference_entries):
        accounts = account_handler.get_accounts(bank_ids)
        self.assertEntriesMatch(accounts, reference_entries)

    @pytest.mark.parametrize(
        'account_id, reference_entry',
        [[2, db_reference[0]],
         [3, db_reference[1]]]
    )
    def test_get_entry(self, account_handler, account_id, reference_entry):
        account = account_handler.get_entry(account_id)
        self.assertEntryMatches(account, reference_entry)

    @pytest.mark.parametrize(
        'account_id, exception',
        [[1, NotFound],  # Not the logged in user
         [4, NotFound]]  # Not in the database
    )
    def test_get_entry_invalid(self, account_handler, account_id, exception):
        with pytest.raises(exception):
            account_handler.get_entry(account_id)

    @pytest.mark.parametrize(
        'mapping',
        [{'bank_id': 2, 'statement_issue_day': 11, 'statement_due_day': 1},
         {'bank_id': 3, 'statement_issue_day': 21, 'statement_due_day': 1}]
    )
    def test_add_entry(self, account_handler, mapping):
        account = account_handler.add_entry(**mapping)
        # Check that the entry object was properly created
        assert account.statement_due_day == 1
        # Check that the entry was added to the database
        self.assertNumberOfMatches(
            1, CreditAccount.id, CreditAccount.statement_due_day == 1
        )

    @pytest.mark.parametrize(
        'mapping, exception',
        [[{'bank_id': 2, 'invalid_field': 'Test', 'statement_due_day': 1},
         TypeError],
         [{'bank_id': 3, 'statement_issue_day': 21},
         IntegrityError]]
    )
    def test_add_entry_invalid(self, account_handler, mapping, exception):
        with pytest.raises(exception):
            account_handler.add_entry(**mapping)

    def test_add_entry_invalid_user(self, account_handler):
        mapping = {
            "bank_id": 1,
            "statement_issue_day": 11,
            "statement_due_day": 1,
        }
        # Ensure that 'mr.monopyly' cannot add an entry for the test user
        self.assert_invalid_user_entry_add_fails(
            account_handler, mapping, invalid_user_id=1, invalid_matches=1
        )

    @pytest.mark.parametrize(
        'mapping',
        [{'bank_id': 2, 'statement_issue_day': 10, 'statement_due_day': 1},
         {'bank_id': 2, 'statement_due_day': 1}]
    )
    def test_update_entry(self, account_handler, mapping):
        account = account_handler.update_entry(2, **mapping)
        # Check that the entry object was properly updated
        assert account.statement_due_day == 1
        # Check that the entry was updated in the database
        self.assertNumberOfMatches(
            1, CreditAccount.id, CreditAccount.statement_due_day == 1
        )

    @pytest.mark.parametrize(
        "account_id, mapping, exception",
        [[1, {"bank_id": 2, "statement_due_day": 1},
          NotFound],                                        # wrong user
         [2, {"bank_id": 2, "invalid_field": "Test"},
          ValueError],                                      # invalid field
         [4, {"bank_id": 2, "statement_due_day": 1},
          NotFound]]                                        # nonexistent ID
    )
    def test_update_entry_invalid(self, account_handler, account_id, mapping,
                                  exception):
        with pytest.raises(exception):
            account_handler.update_entry(account_id, **mapping)

    @pytest.mark.parametrize('entry_id', [2, 3])
    def test_delete_entry(self, account_handler, entry_id):
        self.assert_entry_deletion_succeeds(account_handler, entry_id)
        # Check that the cascading entries were deleted
        self.assertNumberOfMatches(
            0, CreditCard.id, CreditCard.account_id == entry_id
        )

    @pytest.mark.parametrize(
        'entry_id, exception',
        [[1, NotFound],   # should not be able to delete other user entries
         [4, NotFound]]   # should not be able to delete nonexistent entries
    )
    def test_delete_entry_invalid(self, account_handler, entry_id, exception):
        with pytest.raises(exception):
            account_handler.delete_entry(entry_id)

