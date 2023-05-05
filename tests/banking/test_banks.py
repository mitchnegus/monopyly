"""Tests for the banking module managing banks."""
import pytest
from authanor.test.helpers import TestHandler
from werkzeug.exceptions import NotFound

from monopyly.banking.banks import BankHandler
from monopyly.database.models import Bank, BankAccount


@pytest.fixture
def bank_handler(client_context):
    return BankHandler


class TestBankHandler(TestHandler):
    # Reference only includes entries accessible to the authorized login
    db_reference = [
        Bank(id=2, user_id=3, bank_name="Jail"),
        Bank(id=3, user_id=3, bank_name="TheBank"),
    ]

    @pytest.mark.parametrize(
        "bank_names, reference_entries",
        [
            [None, db_reference],
            [("Jail",), db_reference[0:1]],
            [("Jail", "TheBank"), db_reference],
        ],
    )
    def test_get_banks(self, bank_handler, bank_names, reference_entries):
        banks = bank_handler.get_banks(bank_names)
        self.assertEntriesMatch(banks, reference_entries)

    @pytest.mark.parametrize("entry_id", [2, 3])
    def test_delete_entry(self, bank_handler, entry_id):
        self.assert_entry_deletion_succeeds(bank_handler, entry_id)
        # Check that the cascading entries were deleted
        self.assertNumberOfMatches(0, BankAccount.id, BankAccount.bank_id == entry_id)
