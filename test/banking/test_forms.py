"""Tests for the banking module forms."""
from unittest.mock import patch

import pytest

from monopyly.banking.forms import BankTransactionForm


@pytest.fixture
def transaction_form(app, client, auth):
    auth.login('mr.monopyly', 'MONOPYLY')
    with client:
        # Context variables (e.g. `g`) may be accessed only after response
        client.get('/')
        form = BankTransactionForm()
        yield form

@pytest.fixture
def filled_transaction_form(transaction_form):
    # Mock the account info subform data
    transaction_form.account_info.bank_name.data = 'Jail'
    transaction_form.account_info.last_four_digits.data = '5556'
    transaction_form.account_info.type_name.data = 'Savings'
    # Mock the transaction data
    transaction_form.transaction_date.data = '2020-12-25'
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
            'transaction_date': '2020-12-25',
            'subtransactions': [
                {'note': 'Christmas gift', 'subtotal': 25.00}
            ],
        }
        assert filled_transaction_form.transaction_data == data

    def test_transfer_data(self, filled_transaction_form_with_transfer):
        data = {
            'internal_transaction_id': None,
            'account_id': 4,
            'transaction_date': '2020-12-25',
            'subtransactions': [
                {'note': 'Christmas gift', 'subtotal': -25.00}
            ],
        }
        assert filled_transaction_form_with_transfer.transfer_data == data

    def test_no_transfer_data(self, filled_transaction_form):
        assert filled_transaction_form.transfer_data is None

