"""Tests for the credit module managing credit card accounts."""

import pytest
from dry_foundation.testing.helpers import TestRepository

from monopyly.credit.accounts import CreditAccountRepository
from monopyly.database.models import CreditAccount, CreditCard


@pytest.fixture
def account_repo(client_context):
    return CreditAccountRepository


class TestCreditAccountRepository(TestRepository):
    # References only include entries accessible to the authorized login
    db_reference = [
        CreditAccount(id=2, bank_id=2, statement_issue_day=10, statement_due_day=5),
        CreditAccount(id=3, bank_id=3, statement_issue_day=6, statement_due_day=27),
    ]

    @pytest.mark.parametrize(
        ("bank_ids", "reference_entries"),
        [(None, db_reference), ((2,), db_reference[:1])],
    )
    def test_get_accounts(self, account_repo, bank_ids, reference_entries):
        accounts = account_repo.get_accounts(bank_ids)
        self.assert_entries_match(accounts, reference_entries)

    @pytest.mark.parametrize("entry_id", [2, 3])
    def test_delete_entry(self, account_repo, entry_id):
        self.assert_entry_deletion_succeeds(account_repo, entry_id)
        # Check that the cascading entries were deleted
        self.assert_number_of_matches(
            0, CreditCard.id, CreditCard.account_id == entry_id
        )
