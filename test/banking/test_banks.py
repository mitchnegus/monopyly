"""Tests for the banking module managing banks."""
import pytest
from werkzeug.exceptions import NotFound
from sqlalchemy.exc import IntegrityError

from monopyly.database.models import Bank, BankAccount
from monopyly.banking.banks import BankHandler
from ..helpers import TestHandler


@pytest.fixture
def bank_handler(client_context):
    return BankHandler


class TestBankHandler(TestHandler):

    # Reference only includes entries accessible to the authorized login
    db_reference = [
        Bank(id=2, user_id=3, bank_name="Jail"),
        Bank(id=3, user_id=3, bank_name="TheBank"),
    ]

    def test_initialization(self, bank_handler):
        assert bank_handler.model == Bank
        assert bank_handler.table == "banks"
        assert bank_handler.user_id == 3

    @pytest.mark.parametrize(
        "bank_names, reference_entries",
        [[None, db_reference],
         [("Jail",), db_reference[0:1]],
         [("Jail", "TheBank"), db_reference]]
    )
    def test_get_banks(self, bank_handler, bank_names, reference_entries):
        banks = bank_handler.get_banks(bank_names)
        self.assertEntriesMatch(banks, reference_entries)

    @pytest.mark.parametrize(
        "bank_id, reference_entry",
        [[2, db_reference[0]],
         [3, db_reference[1]]]
    )
    def test_get_entry(self, bank_handler, bank_id, reference_entry):
        bank = bank_handler.get_entry(bank_id)
        self.assertEntryMatches(bank, reference_entry)

    @pytest.mark.parametrize(
        "bank_id, exception",
        [[1, NotFound],  # Not the logged in user
         [5, NotFound]]  # Not in the database
    )
    def test_get_entry_invalid(self, bank_handler, bank_id, exception):
        with pytest.raises(exception):
            bank_handler.get_entry(bank_id)

    def test_add_entry(self, bank_handler):
        bank = bank_handler.add_entry(user_id=3, bank_name="JP Morgan Chance")
        # Check that the entry object was properly created
        assert bank.bank_name == "JP Morgan Chance"
        # Check  that the entry was properly added to the database
        self.assertNumberOfMatches(1, Bank.id, Bank.bank_name.like("%Chance"))

    @pytest.mark.parametrize(
        "mapping, expectation",
        [[{"user_id": 3, "invalid_field": "Test"}, TypeError],
         [{"user_id": 3}, IntegrityError]]
    )
    def test_add_entry_invalid(self, bank_handler, mapping, expectation):
        with pytest.raises(expectation):
            bank_handler.add_entry(**mapping)

    def test_add_entry_invalid_user(self, bank_handler):
        mapping = {
            "user_id": 1,
            "bank_name": "JP Morgan Chance",
        }
        # Ensure that 'mr.monopyly' cannot add an entry for the test user
        self.assert_invalid_user_entry_add_fails(
            bank_handler, mapping, invalid_user_id=1, invalid_matches=1
        )

    @pytest.mark.parametrize(
        "mapping",
        [{"user_id": 3, "bank_name": "Corner Jail"},
         {"bank_name": "Corner Jail"}]
    )
    def test_update_entry(self, bank_handler, mapping):
        bank = bank_handler.update_entry(2, **mapping)
        # Check that the entry object was properly updated
        assert bank.bank_name == "Corner Jail"
        # Check that the entry was updated in the database
        self.assertNumberOfMatches(1, Bank.id, Bank.bank_name.like("Corner%"))

    @pytest.mark.parametrize(
        "bank_id, mapping, exception",
        [[1, {"user_id": 3, "bank_name": "Test"},
          NotFound],                                        # wrong user
         [2, {"user_id": 3, "invalid_field": "Test"},
          ValueError],                                      # invalid field
         [5, {"user_id": 3, "bank_name": "Test"},
          NotFound]]                                        # nonexistent ID
    )
    def test_update_entry_invalid(self, bank_handler, bank_id, mapping, exception):
        with pytest.raises(exception):
            bank_handler.update_entry(bank_id, **mapping)

    @pytest.mark.parametrize("entry_id", [2, 3])
    def test_delete_entry(self, bank_handler, entry_id):
        self.assert_entry_deletion_succeeds(bank_handler, entry_id)
        # Check that the cascading entries were deleted
        self.assertNumberOfMatches(
            0, BankAccount.id, BankAccount.bank_id == entry_id
        )

    @pytest.mark.parametrize(
        "entry_id, exception",
        [[1, NotFound],   # should not be able to delete other user entries
         [4, NotFound]]   # should not be able to delete nonexistent entries
    )
    def test_delete_entry_invalid(self, bank_handler, entry_id, exception):
        with pytest.raises(exception):
            bank_handler.delete_entry(entry_id)

