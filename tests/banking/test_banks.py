"""Tests for the banking module managing banks."""

import pytest
from dry_foundation.testing.helpers import TestRepository

from monopyly.banking.banks import BankRepository
from monopyly.database.models import Bank, BankAccount


@pytest.fixture
def bank_repo(client_context):
    return BankRepository


class TestBankRepository(TestRepository):
    # Reference only includes entries accessible to the authorized login
    db_reference = [
        Bank(id=2, user_id=3, bank_name="Jail"),
        Bank(id=3, user_id=3, bank_name="TheBank"),
    ]

    @pytest.mark.parametrize(
        ("bank_names", "reference_entries"),
        [
            (None, db_reference),
            (("Jail",), db_reference[0:1]),
            (("Jail", "TheBank"), db_reference),
        ],
    )
    def test_get_banks(self, bank_repo, bank_names, reference_entries):
        banks = bank_repo.get_banks(bank_names)
        self.assert_entries_match(banks, reference_entries)

    @pytest.mark.parametrize("entry_id", [2, 3])
    def test_delete_entry(self, bank_repo, entry_id):
        self.assert_entry_deletion_succeeds(bank_repo, entry_id)
        # Check that the cascading entries were deleted
        self.assert_number_of_matches(
            0, BankAccount.id, BankAccount.bank_id == entry_id
        )
