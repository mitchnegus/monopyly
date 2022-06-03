"""Tests for the banking module forms."""
from unittest.mock import Mock, PropertyMock, patch
from datetime import date

import pytest

from monopyly.banking.forms import BankTransactionForm, BankAccountForm
from monopyly.banking.banks import BankHandler
from monopyly.banking.accounts import BankAccountTypeHandler
from ..helpers import helper


@pytest.fixture
def transaction_form(client_context):
   form = BankTransactionForm()
   yield form


@pytest.fixture
def filled_transaction_form(transaction_form):
    # Mock the account info subform data
    transaction_form.account_info.bank_name.data = 'Jail'
    transaction_form.account_info.last_four_digits.data = '5556'
    transaction_form.account_info.type_name.data = 'Savings'
    # Mock the transaction data
    transaction_form.transaction_date.data = date(2020, 12, 25)
    # Mock the subtransaction subform data
    transaction_form.subtransactions[0].subtotal.data = 25.00
    transaction_form.subtransactions[0].note.data = 'Christmas gift'
    yield transaction_form


@pytest.fixture
def transaction_form_with_transfer(transaction_form):
    transaction_form.transfer_account_info.append_entry()
    yield transaction_form


# NOTE: use property to avoid indexing field list with 0 or 1 entry?
@pytest.fixture
def filled_transaction_form_with_transfer(filled_transaction_form):
    # Mock the transfer account info subform data
    filled_transaction_form.transfer_account_info.append_entry()
    account_info = filled_transaction_form.transfer_account_info[0]
    account_info.bank_name.data = 'TheBank'
    account_info.last_four_digtis = '5557'
    account_info.type_name.data = 'Certificate of Deposit'
    yield filled_transaction_form


class TestBankTransactionForm:

    def test_initialization(self, transaction_form):
        form_fields = ('account_info', 'transaction_date', 'subtransactions',
                       'transfer_account_info', 'submit')
        for field in form_fields:
            assert hasattr(transaction_form, field)

    def test_account_info_subform_initialization(self, transaction_form):
        subform_fields = ('bank_name', 'last_four_digits', 'type_name')
        for field in subform_fields:
            assert hasattr(transaction_form['account_info'], field)

    def test_subtransaction_subform_initialization(self, transaction_form):
        subform_fields = ('subtotal', 'note')
        for subtransaction_form in transaction_form['subtransactions']:
           for field in subform_fields:
                assert hasattr(subtransaction_form, field)

    def test_get_transaction_account(self, filled_transaction_form):
        account = filled_transaction_form.get_transaction_account()
        assert account['id'] == 2

    def test_get_transfer_account(self, filled_transaction_form_with_transfer):
        account = filled_transaction_form_with_transfer.get_transfer_account()
        assert account['id'] == 4

    def test_transaction_data(self, filled_transaction_form):
        data = {
            'internal_transaction_id': None,
            'account_id': 2,
            'transaction_date': date(2020, 12, 25),
            'subtransactions': [
                {'note': 'Christmas gift', 'subtotal': 25.00}
            ],
        }
        assert filled_transaction_form.transaction_data == data

    def test_transfer_data(self, filled_transaction_form_with_transfer):
        data = {
            'internal_transaction_id': None,
            'account_id': 4,
            'transaction_date': date(2020, 12, 25),
            'subtransactions': [
                {'note': 'Christmas gift', 'subtotal': -25.00}
            ],
        }
        assert filled_transaction_form_with_transfer.transfer_data == data

    def test_no_transfer_data(self, filled_transaction_form):
        assert filled_transaction_form.transfer_data is None

    @pytest.mark.parametrize(
        'bank_id, account_id',
        [[None, None],
         [Mock(), None],
         [Mock(), Mock()]]
    )
    @patch('monopyly.banking.forms.BankAccountHandler')
    @patch('monopyly.banking.forms.BankHandler')
    def test_generate_new(self, mock_bank_handler_type,
                          mock_account_handler_type,
                          client_context, bank_id, account_id):
        mock_bank_db = mock_bank_handler_type.return_value
        mock_account_db = mock_account_handler_type.return_value
        # Mock the bank info (if an ID was provided)
        bank_info = {'bank_name': 'test_bank' if bank_id else None}
        mock_bank_db.get_entry.return_value = bank_info
        # Mock the account info (if an ID was provided)
        other_account_info = {
            'last_four_digits': '2222' if account_id else None,
            'type_name': 'test_type' if account_id else None,
        }
        mock_account_db.get_entry.return_value = other_account_info
        form = BankTransactionForm.generate_new(bank_id, account_id)
        assert form.account_info.data == {**bank_info, **other_account_info}

    @patch('monopyly.banking.forms.BankSubtransactionHandler')
    @patch('monopyly.banking.forms.BankTransactionHandler')
    def test_generate_update(self, mock_transaction_handler_type,
                             mock_subtransaction_handler_type, client_context):
        mock_transaction_id = Mock()
        mock_transaction_db = mock_transaction_handler_type.return_value
        mock_subtransaction_db = mock_subtransaction_handler_type.return_value
        # Mock the transaction info
        transaction_info = {
            'id': 0,
            'transaction_date': 'test_date',
        }
        account_info = {
            'bank_name': 'test_bank',
            'last_four_digits': '2222',
            'type_name': 'test_type',
        }
        mock_transaction_db.get_entry.return_value = {**transaction_info,
                                                      **account_info}
        # Mock the subtransaction info
        subtransaction_info = [
            {'subtotal': 100.00, 'note': 'test_note 1'},
            {'subtotal': 200.00, 'note': 'test note 2'},
        ]
        mock_subtransaction_db.get_entries.return_value = subtransaction_info
        form = BankTransactionForm.generate_update(mock_transaction_id)
        assert form.transaction_date.data == 'test_date'
        assert form.account_info.data == account_info
        for subform, data in zip(form.subtransactions, subtransaction_info):
            assert subform.data == data

    @pytest.mark.parametrize(
        'field, expected_suggestions',
        [['test_field_0', [0, 1, 3]],
         ['test_field_1', [3, 1, 2]],
         ['test_field_2', [2, 3, 4, 5]]]
    )
    @patch(
        'monopyly.banking.forms.BankTransactionForm.TransactionAutocompleter'
        '._autocompletion_handler_map',
        new_callable=PropertyMock
    )
    @patch(
        'monopyly.common.form_utils.validate_field',
        new=lambda field, autocompletion_fields: None)
    def test_autocomplete(self, mock_property, field, expected_suggestions):
        mock_handler_type = mock_property.return_value.__getitem__.return_value
        mock_db = mock_handler_type.return_value
        mock_db.get_entries.return_value = [
            {'test_field_0': 0, 'test_field_1': 1, 'test_field_2': 2},
            {'test_field_0': 0, 'test_field_1': 2, 'test_field_2': 4},
            {'test_field_0': 1, 'test_field_1': 3, 'test_field_2': 5},
            {'test_field_0': 3, 'test_field_1': 3, 'test_field_2': 3},
        ]
        suggestions = BankTransactionForm.autocomplete(field)
        assert suggestions == expected_suggestions

    def test_autocompletion_fields(self):
        autocompleter = BankTransactionForm.TransactionAutocompleter
        autocompletion_fields = [
            'bank_name',
            'last_four_digits',
            'type_name',
            'note'
        ]
        assert autocompleter.autocompletion_fields == autocompletion_fields


@pytest.fixture
def account_form(client_context):
    form = BankAccountForm()
    yield form


@pytest.fixture
def filled_account_form(account_form):
    # Mock the bank info subform data
    account_form.bank_info.bank_id.data = 2
    # Mock the account type info subform data
    account_form.account_type_info.account_type_id.data = 5
    # Mock the account data
    account_form.last_four_digits.data = '8888'
    account_form.active = True
    yield account_form


class TestBankAccountForm:

    def test_initialization(self, account_form):
        form_fields = ('bank_info', 'account_type_info', 'last_four_digits',
                       'submit')
        for field in form_fields:
            assert hasattr(account_form, field)

    def test_bank_subform_initialization(self, account_form):
        subform_fields = ('bank_id', 'bank_name')
        for field in subform_fields:
            assert hasattr(account_form['bank_info'], field)

    def test_account_info_subform_initialization(self, account_form):
        subform_fields = ('account_type_id', 'type_name')
        for field in subform_fields:
            assert hasattr(account_form['account_type_info'], field)

    def test_prepare_bank_choices(self, account_form):
        # Choices should be all user banks, a null selection, and a new option
        choices = [
            (-1, '-'),
            (2, 'Jail'),
            (3, 'TheBank'),
            (0, 'New bank'),
        ]
        bank_id_field = account_form.bank_info.bank_id
        assert bank_id_field.choices == choices

    def test_prepare_account_type_choices(self, account_form):
        # Choices should be all user account types, all common account types,
        # a null selection, and a new option
        choices = [
            (-1, '-'),
            (1, 'Savings'),
            (2, 'Checking'),
            (3, 'Certificate of Deposit (CD)'),
            (5, 'Trustworthy Player (Trust)'),
            (6, 'Cooperative Enjoyment Depository (Mutual FunD)'),
            (0, 'New account type'),
        ]
        account_type_id_field = account_form.account_type_info.account_type_id
        helper.assertCountEqual(account_type_id_field.choices, choices)

    def test_account_data(self, filled_account_form):
        data = {
            'bank_id': 2,
            'account_type_id': 5,
            'last_four_digits': '8888',
            'active': 1,
        }
        assert filled_account_form.account_data == data

    def test_account_data_new_bank(self, filled_account_form):
        bank_info = filled_account_form.bank_info
        # Set the account form bank info to be a new bank
        bank_info.bank_id.data = 0
        bank_info.bank_name.data = 'Test Bank'
        data = {
            'bank_id': 4,
            'account_type_id': 5,
            'last_four_digits': '8888',
            'active': 1,
        }
        assert filled_account_form.account_data == data

    def test_account_data_new_account_type(self, filled_account_form):
        account_type_info = filled_account_form.account_type_info
        # Set the account form account type info to be a new account type
        account_type_info.account_type_id.data = 0
        account_type_info.type_name.data = 'Test Account Type'
        data = {
            'bank_id': 2,
            'account_type_id': 7,
            'last_four_digits': '8888',
            'active': 1,
        }
        assert filled_account_form.account_data == data

