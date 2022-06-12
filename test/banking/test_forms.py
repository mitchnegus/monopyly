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

    def test_get_transaction_account(self, filled_transaction_form):
        account = filled_transaction_form.get_transaction_account()
        assert account['id'] == 2

    def test_get_transfer_account(self, filled_transaction_form_with_transfer):
        account = filled_transaction_form_with_transfer.get_transfer_account()
        assert account['id'] == 4

    @pytest.mark.parametrize(
        'mock_entry',
        [{'bank_id': 1,     # must be an integer for field compatibility
          'bank_name': 'Test Bank'},
         {'account_id': 1,  # must be an integer for field compatibility
          'bank_name': 'Test Bank',
          'last_four_digits': '2222',
          'type_name': 'test_type'}]
    )
    def test_prepopulate(self, transaction_form, mock_entry):
        transaction_form.prepopulate(mock_entry)
        # Check that the form data matches the expectation
        transaction_form_data = {
            'csrf_token': None,
            'account_info': {
                'bank_name': mock_entry.get('bank_name'),
                'last_four_digits': mock_entry.get('last_four_digits'),
                'type_name': mock_entry.get('type_name'),
            },
            'transaction_date': None,
            'subtransactions': [{'subtotal': None, 'note': None}],
            'transfer_account_info': [],
            'submit': False,
        }
        assert transaction_form.data == transaction_form_data

    @patch('monopyly.banking.forms.BankSubtransactionHandler')
    def test_prepopulate_transaction(self, mock_handler_type,
                                     transaction_form):
        # Mock the transaction
        mock_transaction = {
            'id': Mock(),
            'internal_transaction_id': None,
            'bank_id': 100,        # must be an integer for field compatibility
            'bank_name': 'Test Bank',
            'account_id': 100,     # must be an integer for field compatibility
            'last_four_digits': '2222',
            'active': True,
            'account_type_id': 100,# must be an integer for field compatibility
            'type_name': 'test_type',
            'transaction_date': '2022-06-05',
        }
        # Mock the subtransactions returned by the mock handler
        mock_subtransactions = [
            {'subtotal': 100.00, 'note': 'test note one'},
            {'subtotal': 200.00, 'note': 'test note two'},
        ]
        mock_db = mock_handler_type.return_value
        mock_method = mock_db.get_entries
        mock_method.return_value = mock_subtransactions
        transaction_form.prepopulate_transaction(mock_transaction)
        # Check that the form data matches the expectation
        transaction_form_data = {
            'csrf_token': None,
            'account_info': {
                'bank_name': mock_transaction['bank_name'],
                'last_four_digits': mock_transaction['last_four_digits'],
                'type_name': mock_transaction['type_name'],
            },
            'transaction_date': date(2022, 6, 5),
            'subtransactions': mock_subtransactions,
            'transfer_account_info': [],
            'submit': False,
        }
        assert transaction_form.data == transaction_form_data

    @patch('monopyly.banking.forms.BankSubtransactionHandler')
    def test_prepopulate_transaction_no_transfer(self, mock_handler_type,
                                                 transaction_form):
        # Mock the transaction
        mock_transaction = {
            'id': Mock(),
            'bank_id': 1,     # must be an integer for field compatibility
            'bank_name': 'Test Bank',
            'account_id': 1,  # must be an integer for field compatibility
            'last_four_digits': '2222',
            'user_id': Mock(),
            'type_name': 'test_type',
            'transaction_date': '2022-06-05',
        }
        # Mock the subtransactions returned by the mock handler
        mock_subtransactions = [
            {'subtotal': 100.00, 'note': 'test note one'},
            {'subtotal': 200.00, 'note': 'test note two'},
        ]
        mock_db = mock_handler_type.return_value
        mock_method = mock_db.get_entries
        mock_method.return_value = mock_subtransactions
        transaction_form.prepopulate_transaction(mock_transaction)
        # Check that the form data matches the expectation
        transaction_form_data = {
            'csrf_token': None,
            'account_info': {
                'bank_name': mock_transaction['bank_name'],
                'last_four_digits': mock_transaction['last_four_digits'],
                'type_name': mock_transaction['type_name'],
            },
            'transaction_date': date(2022, 6, 5),
            'subtransactions': mock_subtransactions,
            'transfer_account_info': [],
            'submit': False,
        }
        assert transaction_form.data == transaction_form_data

    def test_autocompletion_fields(self):
        autocompleter = BankTransactionForm.TransactionAutocompleter
        autocompletion_fields = [
            'bank_name',
            'last_four_digits',
            'type_name',
            'note',
        ]
        assert autocompleter.autocompletion_fields == autocompletion_fields

    @patch(
        'monopyly.banking.forms.BankTransactionForm.TransactionAutocompleter'
    )
    def test_autocomplete(self, mock_autocompleter):
        mock_method = mock_autocompleter.autocomplete
        suggestions = BankTransactionForm.autocomplete('test_field')
        assert suggestions == mock_method.return_value
        mock_method.assert_called_once_with('test_field')


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

    def test_prepopulate_bank(self, account_form):
        mock_bank = {
            'bank_id': 1,  # must be an integer for field compatibility
            'bank_name': 'test_name',
        }
        account_form.prepopulate(mock_bank)
        # Check that the form data matches the expectation
        account_form_data = {
            'csrf_token': None,
            'bank_info': {
                'bank_id': mock_bank['bank_id'],
                'bank_name': mock_bank['bank_name'],
            },
            'account_type_info': {
                'account_type_id': None,
                'type_name': None,
            },
            'last_four_digits': None,
            'active': True,
            'submit': False,
        }
        assert account_form.data == account_form_data

