"""Tests for the banking module managing banks."""
import pytest
from werkzeug.exceptions import NotFound
from sqlalchemy.exc import IntegrityError

from monopyly.database import db
from monopyly.database.models import Bank, BankAccount
from monopyly.banking.banks import BankHandler
from ..helpers import TestHandler


@pytest.fixture
def handler(client_context):
    return BankHandler


class TestBankHandler(TestHandler):

    # Reference only includes entries accessible to the authorized login
    db_reference = [
        Bank(id=2, user_id=3, bank_name="Jail"),
        Bank(id=3, user_id=3, bank_name="TheBank"),
    ]

    def test_initialization(self, handler):
        assert handler.model == Bank
        assert handler.user_id == 3

    @pytest.mark.parametrize(
        "bank_names, reference_entries",
        [[None, db_reference],
         [("Jail",), db_reference[0:1]],
         [("Jail", "TheBank"), db_reference]]
    )
    def test_get_banks(self, handler, bank_names, reference_entries):
        banks = handler.get_banks(bank_names)
        self.assertMatchEntries(banks, reference_entries)

    @pytest.mark.parametrize(
        "bank_id, reference_entry",
        [[2, db_reference[0]],
         [3, db_reference[1]]]
    )
    def test_get_entry(self, handler, bank_id, reference_entry):
        bank = handler.get_entry(bank_id)
        self.assertMatchEntry(reference_entry, bank)

    @pytest.mark.parametrize(
        "bank_id, exception",
        [[1, NotFound],  # Not the logged in user
         [5, NotFound]]  # Not in the database
    )
    def test_get_entry_invalid(self, handler, bank_id, exception):
        with pytest.raises(exception):
            handler.get_entry(bank_id)

    def test_add_entry(self, handler):
        bank = handler.add_entry(user_id=3, bank_name="JP Morgan Chance")
        # Check that the entry was properly created
        assert bank.bank_name == "JP Morgan Chance"
        # Check  that the entry was properly added to the database
        self.assertNumberOfMatches(1, Bank.id, Bank.bank_name.like("%Chance"))

    @pytest.mark.parametrize(
        "mapping, expectation",
        [[{"user_id": 3, "invalid_field": "Test"}, TypeError],
         [{"user_id": 3}, IntegrityError]]
    )
    def test_add_entry_invalid(self, handler, mapping, expectation):
        with pytest.raises(expectation):
            handler.add_entry(**mapping)

    def test_add_entry_invalid_user(self, handler):
        # Count the number of users by the test user
        self.assertNumberOfMatches(1, Bank.id, Bank.user_id == 1)
        # Ensure that 'mr.monopyly' user cannot add an entry for the test user
        mapping = {
            "user_id": 1,
            "bank_name": "JP Morgan Chance",
        }
        with pytest.raises(NotFound):
            handler.add_entry(**mapping)
        # Rollback and ensure the transaction was not added for the test user
        db.session.close()
        self.assertNumberOfMatches(1, Bank.id, Bank.user_id == 1)

    @pytest.mark.parametrize(
        "mapping",
        [{"user_id": 3, "bank_name": "Corner Jail"},
         {"bank_name": "Corner Jail"}]
    )
    def test_update_entry(self, handler, mapping):
        bank = handler.update_entry(2, **mapping)
        assert bank.bank_name == "Corner Jail"
        # Check that the entry was updated
        self.assertNumberOfMatches(1, Bank.id, Bank.bank_name.like("Corner%"))

    @pytest.mark.parametrize(
        "bank_id, mapping, exception",
        [[1, {"user_id": 3, "bank_name": "Test"},           # wrong user
          NotFound],
         [2, {"user_id": 3, "invalid_field": "Test"},       # invalid field
          ValueError],
         [5, {"user_id": 3, "bank_name": "Test"},           # nonexistent ID
          NotFound]]
    )
    def test_update_entry_invalid(self, handler, bank_id, mapping, exception):
        with pytest.raises(exception):
            handler.update_entry(bank_id, **mapping)

    @pytest.mark.parametrize(
        "entry_id", [2, 3]
    )
    def test_delete_entries(self, handler, entry_id):
        handler.delete_entry(entry_id)
        # Check that the entries were deleted
        self.assertNumberOfMatches(0, Bank.id, Bank.id == entry_id)

    def test_delete_cascading_entries(self, app, handler):
        handler.delete_entry(3)
        # Check that the cascading entries were deleted
        self.assertNumberOfMatches(0, BankAccount.id, BankAccount.bank_id == 3)

    @pytest.mark.parametrize(
        "entry_id, exception",
        [[1, NotFound],   # should not be able to delete other user entries
         [4, NotFound]]   # should not be able to delete nonexistent entries
    )
    def test_delete_entries_invalid(self, handler, entry_id, exception):
        with pytest.raises(exception):
            handler.delete_entry(entry_id)

