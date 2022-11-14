"""Tests for the banking module managing bank accounts."""
from unittest.mock import patch

import pytest
from werkzeug.exceptions import NotFound
from sqlalchemy.exc import IntegrityError

from monopyly.database.models import (
    Bank, BankAccountType, BankAccountTypeView, BankAccount, BankAccountView,
    BankTransaction
)
from monopyly.banking.accounts import (
    BankAccountTypeHandler, BankAccountHandler, save_account
)
from ..helpers import TestHandler


@pytest.fixture
def account_type_handler(client_context):
    return BankAccountTypeHandler


class TestBankAccountTypeHandler(TestHandler):

    # References only include entries accessible to the authorized login
    db_reference = [
        BankAccountTypeView(id=1, user_id=0, type_name="Savings",
                            type_abbreviation=None,
                            type_common_name="Savings"),
        BankAccountTypeView(id=2, user_id=0, type_name="Checking",
                            type_abbreviation=None,
                            type_common_name="Checking"),
        BankAccountTypeView(id=3, user_id=0, type_name="Certificate of Deposit",
                            type_abbreviation="CD",
                            type_common_name="CD"),
        BankAccountTypeView(id=5, user_id=3, type_name="Trustworthy Player",
                            type_abbreviation="Trust",
                            type_common_name="Trust"),
        BankAccountTypeView(id=6, user_id=3,
                            type_name="Cooperative Enjoyment Depository",
                            type_abbreviation="Mutual FunD",
                            type_common_name="Mutual FunD"),
    ]

    def test_initialization(self, account_type_handler):
        assert account_type_handler.model == BankAccountType
        assert account_type_handler.table == "bank_account_types"
        assert account_type_handler.table_view == "bank_account_types_view"
        assert account_type_handler.user_id == 3

    def test_model_view_access(self, account_type_handler):
        assert account_type_handler.model == BankAccountType
        account_type_handler._view_context = True
        assert account_type_handler.model == BankAccountTypeView
        account_type_handler._view_context = False

    def test_get_account_types(self, account_type_handler):
        account_types = account_type_handler.get_account_types()
        self.assertEntriesMatch(account_types, self.db_reference)

    @pytest.mark.parametrize(
        "bank_id, reference_entries",
        [[2, db_reference[:2]],
         [3, db_reference[2:3]]]
    )
    def test_get_types_for_bank(self, account_type_handler, bank_id,
                                reference_entries):
        account_types = account_type_handler.get_types_for_bank(bank_id)
        self.assertEntriesMatch(account_types, reference_entries)

    @pytest.mark.parametrize(
        "account_type_id, reference_entry",
        [[2, db_reference[1]],
         [3, db_reference[2]]]
    )
    def test_get_entry(self, account_type_handler, account_type_id,
                       reference_entry):
        account_type = account_type_handler.get_entry(account_type_id)
        self.assertEntryMatches(account_type, reference_entry)

    @pytest.mark.parametrize(
        "account_type_id, exception",
        [[4, NotFound],  # Not the logged in user
         [7, NotFound]]  # Not in the database
    )
    def test_get_entry_invalid(self, account_type_handler, account_type_id,
                               exception):
        with pytest.raises(exception):
            account_type_handler.get_entry(account_type_id)

    @pytest.mark.parametrize(
        "type_name, type_abbreviation, reference_entry",
        [["Checking", None, db_reference[1]],
         ["Certificate of Deposit", None, db_reference[2]],
         [None, "CD", db_reference[2]],
         [None, "Trust", db_reference[3]],
         ["Certificate of Deposit", "CD", db_reference[2]]]
    )
    def test_find_account_type(self, account_type_handler, type_name,
                               type_abbreviation, reference_entry):
        account_type = account_type_handler.find_account_type(
            type_name, type_abbreviation
        )
        self.assertEntryMatches(account_type, reference_entry)

    @pytest.mark.parametrize(
        "type_name, type_abbreviation",
        [["Certificate of Deposit", "CoD"],
         [None, None]]
    )
    def test_find_account_type_none_exist(self, account_type_handler,
                                          type_name, type_abbreviation):
        account_type = account_type_handler.find_account_type(
            type_name, type_abbreviation
        )
        assert account_type is None

    @pytest.mark.parametrize(
        "mapping",
        [{"user_id": 3, "type_name": "Well Stocked Hand",
          "type_abbreviation": None},
         {"user_id": 3, "type_name": "Well Stocked Hand",
          "type_abbreviation": "Paper"}]
    )
    def test_add_entry(self, account_type_handler, mapping):
        account_type = account_type_handler.add_entry(**mapping)
        # Check that the entry object was properly created
        assert account_type.type_name == "Well Stocked Hand"
        # Check that the entry was added to the database
        self.assertNumberOfMatches(
            1,
            BankAccountType.id,
            BankAccountType.type_name.like("Well Stocked%"),
        )

    @pytest.mark.parametrize(
        "mapping, expectation",
        [[{"user_id": 3, "invalid_field": "Test", "type_abbreviation": None},
          TypeError],
         [{"user_id": 3, "type_abbreviation": None},
          IntegrityError]]
    )
    def test_add_entry_invalid(self, account_type_handler, mapping,
                               expectation):
        with pytest.raises(expectation):
            account_type_handler.add_entry(**mapping)

    def test_add_entry_invalid_user(self, account_type_handler):
        mapping = {
            "user_id": 1,
            "type_name": "Well Stocked Hand",
            "type_abbreviation": "Paper",
        }
        # Ensure that 'mr.monopyly' cannot add an entry for the test user
        self.assert_invalid_user_entry_add_fails(
            account_type_handler, mapping, invalid_user_id=1, invalid_matches=1
        )

    @pytest.mark.parametrize(
        "mapping",
        [{"user_id": 3, "type_name": "Trustworthy Friend",
          "type_abbreviation": "Trust"},
         {"type_name": "Trustworthy Friend"}]
    )
    def test_update_entry(self, account_type_handler, mapping):
        account_type = account_type_handler.update_entry(5, **mapping)
        # Check that the entry object was properly updated
        assert account_type.type_name == "Trustworthy Friend"
        # Check that the entry was updated in the database
        self.assertNumberOfMatches(
            1, BankAccountType.id, BankAccountType.type_name.like("%Friend")
        )

    @pytest.mark.parametrize(
        "account_type_id, mapping, exception",
        [[2, {"user_id": 3, "type_name": "Test"},
          NotFound],                                        # global user
         [3, {"user_id": 3, "type_name": "Test"},
          NotFound],                                        # wrong user
         [5, {"user_id": 3, "invalid_field": "Test"},
          ValueError],                                      # invalid field
         [7, {"user_id": 3, "type_name": "Test"},
          NotFound]]                                        # nonexistent ID
    )
    def test_update_entry_invalid(self, account_type_handler, account_type_id,
                                  mapping, exception):
        with pytest.raises(exception):
            account_type_handler.update_entry(account_type_id, **mapping)

    @pytest.mark.parametrize("entry_id", [5, 6])
    def test_delete_entry(self, account_type_handler, entry_id):
        self.assert_entry_deletion_succeeds(account_type_handler, entry_id)
        # Check that the cascading entries were deleted
        # INCLUDE TEST FOR CASCADING ENTRY DELETION

    @pytest.mark.parametrize(
        "entry_id, exception",
        [[1, NotFound],   # should not be able to delete common entries
         [4, NotFound],   # should not be able to delete other user entries
         [7, NotFound]]   # should not be able to delete nonexistent entries
    )
    def test_delete_entry_invalid(self, account_type_handler,
                                  entry_id, exception):
        with pytest.raises(exception):
            account_type_handler.delete_entry(entry_id)


@pytest.fixture
def account_handler(client_context):
    return BankAccountHandler


class TestBankAccountHandler(TestHandler):

    # References only include entries accessible to the authorized login
    db_reference = [
        BankAccountView(id=2, bank_id=2, account_type_id=1,
                        last_four_digits="5556", active=1, balance=443.90),
        BankAccountView(id=3, bank_id=2, account_type_id=2,
                        last_four_digits="5556", active=0, balance=-409.21),
        BankAccountView(id=4, bank_id=3, account_type_id=3,
                        last_four_digits="5557", active=1, balance=200.00),
    ]

    def test_initialization(self, account_handler):
        assert account_handler.model == BankAccount
        assert account_handler.table == "bank_accounts"
        assert account_handler.table_view == "bank_accounts_view"
        assert account_handler.user_id == 3

    def test_model_view_access(self, account_handler):
        assert account_handler.model == BankAccount
        account_handler._view_context = True
        assert account_handler.model == BankAccountView
        account_handler._view_context = False

    @pytest.mark.parametrize(
        "bank_ids, account_type_ids, reference_entries",
        [[None, None, db_reference],
         [(2,), None, db_reference[:2]],
         [None, (2, 3), db_reference[1:]]]
    )
    def test_get_accounts(self, account_handler, bank_ids, account_type_ids,
                          reference_entries):
        accounts = account_handler.get_accounts(bank_ids, account_type_ids)
        self.assertEntriesMatch(accounts, reference_entries)

    @pytest.mark.parametrize(
        "account_id, reference_entry",
        [[2, db_reference[0]],
         [3, db_reference[1]]]
    )
    def test_get_entry(self, account_handler, account_id, reference_entry):
        account = account_handler.get_entry(account_id)
        self.assertEntryMatches(account, reference_entry)

    @pytest.mark.parametrize(
        "account_id, exception",
        [[1, NotFound],  # Not the logged in user
         [5, NotFound]]  # Not in the database
    )
    def test_get_entry_invalid(self, account_handler, account_id, exception):
        with pytest.raises(exception):
            account_handler.get_entry(account_id)

    @pytest.mark.parametrize(
        "bank_id, expected_balance",
        [[2, (443.90 - 409.21)],
         [3, 200.00]]
    )
    def test_get_bank_balance(self, account_handler, bank_id, expected_balance):
        balance = account_handler.get_bank_balance(bank_id)
        assert balance == expected_balance

    @pytest.mark.parametrize(
        "bank_id, exception",
        [[1, NotFound],  # Not the logged in user
         [4, NotFound]]  # Not in the database
    )
    def test_get_bank_balance_invalid(self, account_handler, bank_id, exception):
        with pytest.raises(exception):
            balance = account_handler.get_bank_balance(bank_id)

    @pytest.mark.parametrize(
        "bank_name, account_type_name, last_four_digits, reference_entry",
        [["Jail", "Savings", "5556", db_reference[0]],
         ["Jail", "Checking", "5556", db_reference[1]],
         ["TheBank", "Certificate of Deposit", None, db_reference[2]],
         [None, "Certificate of Deposit", "5557", db_reference[2]]]
    )
    def test_find_account(self, account_handler, bank_name, account_type_name,
                          last_four_digits, reference_entry):
        account = account_handler.find_account(
            bank_name, account_type_name, last_four_digits
        )
        self.assertEntryMatches(account, reference_entry)

    @pytest.mark.parametrize(
        "bank_name, account_type_name, last_four_digits",
        [["Jail", "6666", None],
         [None, None, None]]
    )
    def test_find_account_none_exist(self, account_handler, bank_name,
                                     last_four_digits, account_type_name):
        account = account_handler.find_account(
            bank_name, account_type_name, last_four_digits
        )
        assert account is None

    @pytest.mark.parametrize(
        "mapping",
        [{"bank_id": 2, "account_type_id": 2, "last_four_digits": "6666",
          "active": 1},
         {"bank_id": 3, "account_type_id": 5, "last_four_digits": "6666",
          "active": 0}]
    )
    def test_add_entry(self, account_handler, mapping):
        account = account_handler.add_entry(**mapping)
        # Check that the entry object was properly created
        assert account.last_four_digits == "6666"
        # Check that the entry was added to the database
        self.assertNumberOfMatches(
            1, BankAccount.id, BankAccount.last_four_digits == "6666"
        )

    @pytest.mark.parametrize(
        "mapping, exception",
        [[{"bank_id": 2, "invalid_field": "Test", "last_four_digits": "6000",
           "active": 1}, TypeError],
         [{"bank_id": 3, "account_type_id": 5, "last_four_digits": "6666"},
          IntegrityError]]
    )
    def test_add_entry_invalid(self, account_handler, mapping, exception):
        with pytest.raises(exception):
            account_handler.add_entry(**mapping)

    def test_add_entry_invalid_user(self, account_handler):
        mapping = {
            "bank_id": 1,
            "account_type_id": 5,
            "last_four_digits": "6666",
            "active": 1,
        }
        # Ensure that 'mr.monopyly' cannot add an entry for the test user
        self.assert_invalid_user_entry_add_fails(
            account_handler, mapping, invalid_user_id=1, invalid_matches=1
        )

    @pytest.mark.parametrize(
        "mapping",
        [{"bank_id": 3, "account_type_id": 1, "last_four_digits": "6666",
          "active": 1},
         {"bank_id": 3, "last_four_digits": "6666"}]
    )
    def test_update_entry(self, account_handler, mapping):
        account = account_handler.update_entry(2, **mapping)
        # Check that the entry object was properly updated
        assert account.last_four_digits == "6666"
        # Check that the entry was updated in the database
        self.assertNumberOfMatches(
            1, BankAccount.id, BankAccount.last_four_digits == "6666"
        )

    @pytest.mark.parametrize(
        "account_id, mapping, exception",
        [[1, {"bank_id": 2, "last_four_digits": "6666"},
          NotFound],                                        # wrong user
         [2, {"bank_id": 2, "invalid_field": "Test"},
          ValueError],                                      # invalid field
         [5, {"bank_id": 2, "last_four_digits": "6666"},
          NotFound]]                                        # nonexistent ID
    )
    def test_update_entry_invalid(self, account_handler, account_id, mapping,
                                  exception):
        with pytest.raises(exception):
            account_handler.update_entry(account_id, **mapping)

    @pytest.mark.parametrize("entry_id", [2, 3])
    def test_delete_entry(self, account_handler, entry_id):
        self.assert_entry_deletion_succeeds(account_handler, entry_id)
        # Check that the cascading entries were deleted
        self.assertNumberOfMatches(
            0, BankTransaction.id, BankTransaction.account_id == entry_id
        )

    @pytest.mark.parametrize(
        "entry_id, exception",
        [[1, NotFound],   # should not be able to delete other user entries
         [5, NotFound]]   # should not be able to delete nonexistent entries
    )
    def test_delete_entry_invalid(self, account_handler, entry_id, exception):
        with pytest.raises(exception):
            account_handler.delete_entry(entry_id)


class TestSaveFormFunctions:

    @patch("monopyly.banking.accounts.BankAccountHandler")
    @patch("monopyly.banking.forms.BankAccountForm")
    def test_save_new_account(self, mock_form, mock_handler):
        # Mock the form and primary method
        mock_form.account_data = {"key": "test account data"}
        mock_method = mock_handler.add_entry
        # Call the function and check for proper call signatures
        account = save_account(mock_form)
        mock_method.assert_called_once_with(**mock_form.account_data)
        assert account == mock_method.return_value

