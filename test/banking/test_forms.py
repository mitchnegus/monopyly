"""Tests for the banking module forms."""
from unittest.mock import Mock, PropertyMock, patch
from datetime import date

import pytest
from flask_wtf import FlaskForm
from wtforms.fields import FormField

from monopyly.database.models import (
    Bank, BankAccountTypeView, BankAccountView, BankTransactionView,
    BankSubtransaction
)
from monopyly.banking.forms import (
    BankSelectField, BankAccountTypeSelectField, BankSubform,
    BankTransactionForm, BankAccountForm
)
from monopyly.banking.banks import BankHandler
from monopyly.banking.accounts import BankAccountTypeHandler
from ..helpers import helper


class TestBankSelectField:

    class SampleForm(FlaskForm):
        """A sample form to be used in the subsequent tests."""
        bank_id = BankSelectField()

    def test_field_name(self, client_context):
        form = self.SampleForm()
        assert form.bank_id.label.text == "Bank"

    def test_prepare_bank_choices(self, client_context):
        # The form should have properly generated values from the database
        # - choices include: user banks, a null selection, and a new option
        expected_choices = [
            (-1, "-"),
            (2, "Jail"),
            (3, "TheBank"),
            (0, "New bank"),
        ]
        form = self.SampleForm()
        assert form.bank_id.choices == expected_choices


class TestBankAccountTypeSelectField:

    class SampleForm(FlaskForm):
        """A sample form to be used in the subsequent tests."""
        account_type_id = BankAccountTypeSelectField()

    def test_field_name(self, client_context):
        form = self.SampleForm()
        assert form.account_type_id.label.text == "Account Type"

    def test_prepare_account_type_choices(self, client_context):
        # The form should have properly generated values from the database
        # - choices include: global account types, user account types, a null
        #   selection, and a new option
        expected_choices = [
            (-1, "-"),
            (1, "Savings"),
            (2, "Checking"),
            (3, "Certificate of Deposit (CD)"),
            (5, "Trustworthy Player (Trust)"),
            (6, "Cooperative Enjoyment Depository (Mutual FunD)"),
            (0, "New account type"),
        ]
        form = self.SampleForm()
        assert form.account_type_id.choices == expected_choices


@pytest.fixture
def mock_bank(client_context):
    mock_bank = Mock(spec=Bank)
    return mock_bank


@pytest.fixture
def mock_account_type(client_context):
    mock_account_type = Mock(spec=BankAccountTypeView)
    return mock_account_type


@pytest.fixture
def mock_account(mock_bank, mock_account_type):
    mock_account = Mock(spec=BankAccountView)
    mock_account.bank = mock_bank
    mock_account.account_type = mock_account_type
    return mock_account


@pytest.fixture
def mock_transaction(mock_account):
    mock_transaction = Mock(spec=BankTransactionView)
    mock_transaction.account = mock_account
    mock_transaction.subtransactions = [
        Mock(spec=BankSubtransaction),
        Mock(spec=BankSubtransaction),
        Mock(spec=BankSubtransaction),
    ]
    return mock_transaction


@pytest.fixture
def mock_subtransaction(mock_transaction):
    mock_subtransaction = Mock(spec=BankSubtransaction)
    mock_subtransaction.transaction = mock_transaction
    return mock_subtransaction


class TestBankSubform:

    class SampleForm(FlaskForm):
        """A sample form to be used in the subsequent tests."""
        bank_info = FormField(BankSubform)

    def test_bank_subform_initialization(self, client_context):
        subform = self.SampleForm().bank_info
        subform_fields = ("bank_id", "bank_name")
        for field in subform_fields:
            assert hasattr(subform, field)

    def test_bank_subform_prepare_mapping(self, client_context):
        subform = self.SampleForm().bank_info
        subform.bank_name.data = Mock()
        data = subform._prepare_mapping()
        expected_data = {
            "user_id": 3,  # "mr.monopyly" user ID is 3
            "bank_name": subform.bank_name.data,
        }
        assert data == expected_data

    def test_bank_subform_prepare_mapping_invalid(self, client_context):
        subform = self.SampleForm().bank_info
        with pytest.raises(ValueError):
            subform._prepare_mapping()

    @patch("monopyly.banking.forms.BankSubform._db_handler")
    def test_bank_subform_get_bank(self, mock_handler, client_context):
        subform = self.SampleForm().bank_info
        subform.bank_id.data = 100
        # Test that an existing bank entry is returned
        bank = subform.get_bank()
        assert bank == mock_handler.get_entry.return_value
        mock_handler.get_entry.assert_called_with(
            subform.bank_id.data
        )

    @patch("monopyly.banking.forms.BankSubform._db_handler")
    @patch("monopyly.banking.forms.BankSubform._prepare_mapping")
    def test_bank_subform_get_new_bank(self, mock_method, mock_handler,
                                       client_context):
        subform = self.SampleForm().bank_info
        # Mock the subform"s mapping
        mock_method.return_value = {"test": "mapping"}
        # Set the bank ID to 0, indicating that the bank is a new submission
        subform.bank_id.data = 0
        # Test that a new bank entry is created and returned
        bank = subform.get_bank()
        assert bank == mock_handler.add_entry.return_value
        mock_handler.add_entry.assert_called_with(
            **mock_method.return_value
        )

    def test_bank_subform_gather_data(self, client_context, mock_bank):
        bank_subform = self.SampleForm().bank_info
        data = bank_subform.gather_entry_data(mock_bank)
        expected_data = {
            "bank_id": mock_bank.id,
            "bank_name": mock_bank.bank_name,
        }
        assert data == expected_data

    def test_bank_subform_gather_data_invalid(self, client_context):
        bank_subform = self.SampleForm().bank_info
        with pytest.raises(TypeError):
            bank_subform.gather_entry_data(None)


@pytest.fixture
def account_form(client_context):
    form = BankAccountForm()
    return form


@pytest.fixture
def filled_account_form(account_form):
    # Mock the bank info subform data
    account_form.bank_info.bank_id.data = 2
    # Mock the account type info subform data
    account_form.account_type_info.account_type_id.data = 5
    # Mock the account data
    account_form.last_four_digits.data = "8888"
    account_form.active.data = True
    return account_form


class TestBankAccountForm:

    def test_initialization(self, account_form):
        form_fields = ("bank_info", "account_type_info", "last_four_digits",
                       "active", "submit")
        for field in form_fields:
            assert hasattr(account_form, field)

    def test_account_info_subform_initialization(self, account_form):
        subform_fields = ("account_type_id", "type_name")
        for field in subform_fields:
            assert hasattr(account_form.account_type_info, field)

    @patch(
        "monopyly.banking.forms.BankAccountForm.AccountTypeSubform.get_account_type"
    )
    @patch("monopyly.banking.forms.BankSubform.get_bank")
    def test_account_data(self, mock_bank_method, mock_account_type_method,
                          filled_account_form):
        expected_data = {
            "bank_id": mock_bank_method.return_value.id,
            "account_type_id": mock_account_type_method.return_value.id,
            "last_four_digits": filled_account_form.last_four_digits.data,
            "active": filled_account_form.active.data,
        }
        assert filled_account_form.account_data == expected_data

    def test_account_type_subform_prepare_mapping(self, filled_account_form):
        account_type_subform = filled_account_form.account_type_info
        data = account_type_subform._prepare_mapping()
        expected_data = {
            "user_id": 3,  # "mr.monopyly" user ID is 3
            "type_name": account_type_subform.type_name.data,
            "type_abbreviation": None,
        }
        assert data == expected_data

    @patch("monopyly.banking.forms.BankAccountForm.AccountTypeSubform._db_handler")
    def test_account_type_subform_get_account_type(self, mock_handler,
                                                   filled_account_form):
        account_type_subform = filled_account_form.account_type_info
        # Test that an existing account entry is returned
        account = account_type_subform.get_account_type()
        assert account == mock_handler.get_entry.return_value
        mock_handler.get_entry.assert_called_with(
            account_type_subform.account_type_id.data
        )

    @patch("monopyly.banking.forms.BankAccountForm.AccountTypeSubform._db_handler")
    @patch("monopyly.banking.forms.BankAccountForm.AccountTypeSubform._prepare_mapping")
    def test_account_type_subform_get_new_account_type(self, mock_method,
                                                       mock_handler,
                                                       filled_account_form):
        account_type_subform = filled_account_form.account_type_info
        # Mock the subform"s mapping
        mock_method.return_value = {"test": "mapping"}
        # Set the account type ID to 0, indicating that the account is a new submission
        account_type_subform.account_type_id.data = 0
        # Test that a new account entry is created and returned
        account_type = account_type_subform.get_account_type()
        assert account_type == mock_handler.add_entry.return_value
        mock_handler.add_entry.assert_called_with(
            **mock_method.return_value
        )

    @patch("monopyly.banking.forms.BankSubform.gather_entry_data")
    def test_gather_data(self, mock_method, account_form, mock_bank):
        data = account_form.gather_entry_data(mock_bank)
        expected_data = {
            "bank_info": mock_method.return_value,
        }
        assert data == expected_data

    def test_gather_data_invalid(self, account_form):
        with pytest.raises(TypeError):
            account_form.gather_entry_data(None)

    @patch("monopyly.banking.forms.BankAccountForm.process")
    @patch("monopyly.banking.forms.BankAccountForm.gather_entry_data")
    def test_prepopulate(self, mock_gather_method, mock_process_method,
                         account_form, mock_account):
        account_form.prepopulate(mock_account)
        mock_process_method.assert_called_once_with(
            data=mock_gather_method.return_value
        )


@pytest.fixture
def transaction_form(client_context):
   form = BankTransactionForm()
   return form


@pytest.fixture
def filled_transaction_form(transaction_form):
    # Mock the account info subform data
    transaction_form.account_info.bank_name.data = "Jail"
    transaction_form.account_info.last_four_digits.data = "5556"
    transaction_form.account_info.type_name.data = "Savings"
    # Mock the transaction data
    transaction_form.transaction_date.data = date(2020, 12, 25)
    # Mock the subtransaction subform data
    transaction_form.subtransactions[0].subtotal.data = 25.00
    transaction_form.subtransactions[0].note.data = "Christmas gift"
    return transaction_form


@pytest.fixture
def transaction_form_with_transfer(transaction_form):
    transaction_form.transfer_accounts_info.append_entry()
    return transaction_form


# NOTE: use property to avoid indexing field list with 0 or 1 entry?
@pytest.fixture
def filled_transaction_form_with_transfer(filled_transaction_form):
    # Mock the transfer account info subform data
    filled_transaction_form.transfer_accounts_info.append_entry()
    account_info = filled_transaction_form.transfer_account_info
    account_info.bank_name.data = "TheBank"
    account_info.last_four_digtis = "5557"
    account_info.type_name.data = "Certificate of Deposit"
    yield filled_transaction_form


class TestBankTransactionForm:

    def test_initialization(self, transaction_form):
        form_fields = ("account_info", "transaction_date", "subtransactions",
                       "transfer_accounts_info", "submit")
        for field in form_fields:
            assert hasattr(transaction_form, field)

    def test_account_info_subform_initialization(self, transaction_form):
        subform_fields = ("bank_name", "last_four_digits", "type_name")
        for field in subform_fields:
            assert hasattr(transaction_form.account_info, field)

    def test_subtransaction_subform_initialization(self, transaction_form):
        subform_fields = ("subtotal", "note")
        for subtransaction_form in transaction_form.subtransactions:
           for field in subform_fields:
                assert hasattr(subtransaction_form, field)

    @patch("monopyly.banking.forms.BankTransactionForm.get_transaction_account")
    def test_transaction_data(self, mock_method, filled_transaction_form):
        subtransaction = filled_transaction_form.subtransactions[0]
        data = {
            "internal_transaction_id": None,
            "account_id": mock_method.return_value.id,
            "transaction_date": filled_transaction_form.transaction_date.data,
            "subtransactions": [{
                "note": subtransaction.note.data,
                "subtotal": subtransaction.subtotal.data,
            }],
        }
        assert filled_transaction_form.transaction_data == data
        # Check that there was actually only one subtransaction
        assert len(filled_transaction_form.subtransactions) == 1

    @patch("monopyly.banking.forms.BankTransactionForm.get_transfer_account")
    def test_transfer_data(self, mock_method,
                           filled_transaction_form_with_transfer):
        subtransaction = filled_transaction_form_with_transfer.subtransactions[0]
        data = {
            "internal_transaction_id": None,
            "account_id": mock_method.return_value.id,
            "transaction_date": filled_transaction_form_with_transfer.transaction_date.data,
            "subtransactions": [{
                "note": subtransaction.note.data,
                "subtotal": -subtransaction.subtotal.data,
            }],
        }
        assert filled_transaction_form_with_transfer.transfer_data == data
        # Check that there was actually only one subtransaction
        assert len(filled_transaction_form_with_transfer.subtransactions) == 1

    def test_no_transfer_data(self, filled_transaction_form):
        assert filled_transaction_form.transfer_data is None

    @patch("monopyly.banking.forms.BankTransactionForm.AccountSubform._db_handler")
    def test_account_subform_get_account(self, mock_handler,
                                         filled_transaction_form):
        account_subform = filled_transaction_form.account_info
        account = account_subform.get_account()
        assert account == mock_handler.find_account.return_value
        mock_handler.find_account.assert_called_with(
            bank_name=account_subform.bank_name.data,
            account_type_name=account_subform.type_name.data,
            last_four_digits=account_subform.last_four_digits.data,
        )

    def test_account_subform_gather_account_data(self, transaction_form,
                                                 mock_account):
        account_subform = transaction_form.account_info
        data = account_subform.gather_entry_data(mock_account)
        expected_data = {
            "bank_name": mock_account.bank.bank_name,
            "last_four_digits": mock_account.last_four_digits,
            "type_name": mock_account.account_type.type_name
        }
        assert data == expected_data

    def test_account_subform_gather_bank_data(self, transaction_form,
                                              mock_bank):
        account_subform = transaction_form.account_info
        data = account_subform.gather_entry_data(mock_bank)
        expected_data = {
            "bank_name": mock_bank.bank_name
        }
        assert data == expected_data

    def test_account_subform_gather_data_invalid(self, transaction_form,
                                                 mock_account):
        account_subform = transaction_form.account_info
        with pytest.raises(TypeError):
            account_subform.gather_entry_data(None)

    def test_subtransaction_subform_gather_data(self, transaction_form,
                                                mock_subtransaction):
        subtransaction_subform = transaction_form.subtransactions[0]
        data = subtransaction_subform.gather_entry_data(mock_subtransaction)
        expected_data = {
            "subtotal": mock_subtransaction.subtotal,
            "note": mock_subtransaction.note,
        }
        assert data == expected_data

    def test_subtransaction_subform_gather_data_invalid(self,
                                                        transaction_form):
        subtransaction_subform = transaction_form.subtransactions[0]
        with pytest.raises(TypeError):
            subtransaction_subform.gather_entry_data(None)

    @patch("monopyly.banking.forms.BankTransactionForm.AccountSubform.get_account")
    def test_get_transaction_account(self, mock_method, transaction_form):
        account = transaction_form.get_transaction_account()
        assert account == mock_method.return_value

    @patch("monopyly.banking.forms.BankTransactionForm.AccountSubform.get_account")
    def test_get_transfer_account(self, mock_method,
                                  transaction_form_with_transfer):
        transfer_account = transaction_form_with_transfer.get_transfer_account()
        assert transfer_account == mock_method.return_value

    @patch(
        "monopyly.banking.forms.BankTransactionForm.AccountSubform.gather_entry_data"
    )
    @patch(
        "monopyly.banking.forms.BankTransactionForm.SubtransactionSubform"
        ".gather_entry_data"
    )
    def test_gather_transaction_data(self, mock_subtransaction_method,
                                     mock_account_method, transaction_form,
                                     mock_transaction):
        # NOTE: We must delete the "_formfield" attribute of the
        # `SubtransactionForm.gather_entry_data` MagicMock object or else
        # WTForms will think that it is an unbound field; perhaps WTForms
        # should use a better method for determining unbound fields
        del mock_subtransaction_method._formfield
        data = transaction_form.gather_entry_data(mock_transaction)
        expected_data = {
            "transaction_date": mock_transaction.transaction_date,
            "subtransactions": 3*[mock_subtransaction_method.return_value],
            "account_info": mock_account_method.return_value
        }
        assert data == expected_data

    @patch(
        "monopyly.banking.forms.BankTransactionForm.AccountSubform.gather_entry_data"
    )
    def test_gather_account_data(self, mock_account_method, transaction_form,
                                 mock_account):
        data = transaction_form.gather_entry_data(mock_account)
        expected_data = {
            "account_info": mock_account_method.return_value
        }
        assert data == expected_data

    @patch(
        "monopyly.banking.forms.BankTransactionForm.AccountSubform.gather_entry_data"
    )
    def test_gather_bank_data(self, mock_account_method, transaction_form,
                              mock_bank):
        data = transaction_form.gather_entry_data(mock_bank)
        expected_data = {
            "account_info": mock_account_method.return_value
        }
        assert data == expected_data

    def test_gather_data_invalid(self, transaction_form):
        with pytest.raises(TypeError):
            transaction_form.gather_entry_data(None)

    @patch("monopyly.banking.forms.BankTransactionForm.process")
    @patch("monopyly.banking.forms.BankTransactionForm.gather_entry_data")
    def test_prepopulate(self, mock_gather_method, mock_process_method,
                         transaction_form, mock_transaction):
        transaction_form.prepopulate(mock_transaction)
        mock_process_method.assert_called_once_with(
            data=mock_gather_method.return_value
        )

    @pytest.mark.parametrize(
        "field, sort_fields, top_expected_suggestions, expected_suggestions",
        [["note", {},
          (),
          ("Jail subtransaction 1", "Jail subtransaction 2",
           "Transfer in", "What else is there to do in Jail?",
           "Credit card payment", "Transfer out",
           "'Go' Corner ATM deposit")],
         ["note",
          {"bank_name": "Jail",
           "last_four_digits": "5556",
           "type_name": "Savings"},
          ("Jail subtransaction 1", "Jail subtransaction 2",
           "Transfer in", "What else is there to do in Jail?"),
          ("Jail subtransaction 1", "Jail subtransaction 2",
           "Transfer in", "What else is there to do in Jail?",
           "Credit card payment", "Transfer out",
           "'Go' Corner ATM deposit")]]
    )
    def test_autocomplete(self, transaction_form, field, sort_fields,
                          top_expected_suggestions, expected_suggestions):
        suggestions = transaction_form.autocomplete(field, **sort_fields)
        top_suggestions = suggestions[:len(top_expected_suggestions)]
        helper.assertCountEqual(top_suggestions, top_expected_suggestions)
        helper.assertCountEqual(suggestions, expected_suggestions)

    def test_autocomplete_invalid(self, transaction_form):
        with pytest.raises(KeyError):
            transaction_form.autocomplete("test_field")

