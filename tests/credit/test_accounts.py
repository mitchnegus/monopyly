"""Tests for the credit module managing credit card accounts."""
import pytest
from authanor.test.helpers import TestHandler
from werkzeug.exceptions import NotFound

from monopyly.credit.accounts import CreditAccountHandler
from monopyly.database.models import CreditAccount, CreditCard


@pytest.fixture
def account_handler(client_context):
    return CreditAccountHandler


class TestCreditAccountHandler(TestHandler):
    # References only include entries accessible to the authorized login
    db_reference = [
        CreditAccount(id=2, bank_id=2, statement_issue_day=10, statement_due_day=5),
        CreditAccount(id=3, bank_id=3, statement_issue_day=6, statement_due_day=27),
    ]

    @pytest.mark.parametrize(
        "bank_ids, reference_entries", [[None, db_reference], [(2,), db_reference[:1]]]
    )
    def test_get_accounts(self, account_handler, bank_ids, reference_entries):
        accounts = account_handler.get_accounts(bank_ids)
        self.assert_entries_match(accounts, reference_entries)

    @pytest.mark.parametrize("entry_id", [2, 3])
    def test_delete_entry(self, account_handler, entry_id):
        self.assert_entry_deletion_succeeds(account_handler, entry_id)
        # Check that the cascading entries were deleted
        self.assert_number_of_matches(
            0, CreditCard.id, CreditCard.account_id == entry_id
        )
