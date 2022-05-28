"""Tests for the banking module forms."""
from unittest.mock import patch
from datetime import date

import pytest
from werkzeug.exceptions import NotFound

from monopyly.credit.forms import CreditTransactionForm, CreditCardForm


@pytest.fixture
def transaction_form(app, client, auth):
    auth.login('mr.monopyly', 'MONOPYLY')
    with client:
        # Context variables (e.g. `g`) may be accessed only after response
        client.get('/')
        form = CreditTransactionForm()
        yield form


@pytest.fixture
def filled_transaction_form(transaction_form):
    # Mock the statement info subform data
    transaction_form.statement_info.issue_date.data = date(2020, 5, 15)
    # Mock the card info subform data
    transaction_form.statement_info.card_info.bank_name.data = 'Jail'
    transaction_form.statement_info.card_info.last_four_digits.data = '3335'
    # Mock the transaction data
    transaction_form.transaction_date.data = date(2020, 5, 4)
    transaction_form.vendor.data = 'O.B. (Wan) Railroad'
    # Mock the subtransaction subform data
    transaction_form.subtransactions[0].subtotal.data = 42.00
    transaction_form.subtransactions[0].note.data = 'Wrong SciFi movie?'
    transaction_form.subtransactions[0].tags.data = 'TEST TAG'
    yield transaction_form


class TestBankTransactionForm:

    def test_initialization(self, transaction_form):
        form_fields = ('statement_info', 'transaction_date', 'vendor',
                       'subtransactions', 'submit')
        for field in form_fields:
            assert hasattr(transaction_form, field)

    def test_statement_info_subform_initialization(self, transaction_form):
        subform_fields = ('card_info', 'issue_date')
        for field in subform_fields:
            assert hasattr(transaction_form['statement_info'], field)

    def test_card_info_subform_initialization(self, transaction_form):
        subform_fields = ('bank_name', 'last_four_digits')
        for field in subform_fields:
            assert hasattr(transaction_form['statement_info']['card_info'],
                           field)

    def test_subtransaction_subform_initialization(self, transaction_form):
        subform_fields = ('subtotal', 'note', 'tags')
        for subtransaction_form in transaction_form['subtransactions']:
           for field in subform_fields:
                assert hasattr(subtransaction_form, field)

    def test_transaction_data(self, filled_transaction_form):
        data = {
            'internal_transaction_id': None,
            'statement_id': 4,
            'transaction_date': date(2020, 5, 4),
            'vendor': 'O.B. (Wan) Railroad',
            'subtransactions': [
                {'note': 'Wrong SciFi movie?', 'subtotal': 42.00,
                 'tags': ['TEST TAG']}
            ],
        }
        assert filled_transaction_form.transaction_data == data

    def test_transaction_data_new_statement(self, filled_transaction_form):
        statement_info = filled_transaction_form.statement_info
        # Set the transaction form statement info to be a new statement
        statement_info.issue_date.data = date(2020, 8, 15)
        data = {
            'internal_transaction_id': None,
            'statement_id': 8,
            'transaction_date': date(2020, 5, 4),
            'vendor': 'O.B. (Wan) Railroad',
            'subtransactions': [
                {'note': 'Wrong SciFi movie?', 'subtotal': 42.00,
                 'tags': ['TEST TAG']}
            ],
        }
        assert filled_transaction_form.transaction_data == data

    @patch('monopyly.credit.statements.CreditStatementHandler.infer_statement')
    def test_transaction_data_infer_statement(self, mock_method,
                                              filled_transaction_form):
        statement_info = filled_transaction_form.statement_info
        # Set the transaction form statement issue date to require inference
        statement_info.issue_date.data = None
        filled_transaction_form.transaction_data
        mock_method.assert_called_once()

    def test_transaction_data_card_invalid(self, filled_transaction_form):
        card_info = filled_transaction_form.statement_info.card_info
        # Set the transaction form card info to be a non-existent card
        card_info.bank_name.data = 'Invalid Bank'
        with pytest.raises(NotFound):
            filled_transaction_form.transaction_data


@pytest.fixture
def card_form(app, client, auth):
    auth.login('mr.monopyly', 'MONOPYLY')
    with client:
        # Context variables (e.g. `g`) may be accessed only after response
        client.get('/')
        form = CreditCardForm()
        yield form


@pytest.fixture
def filled_card_form(card_form):
    # Mock the account info subform data
    card_form.account_info.account_id.data = 2
    # Mock the account data
    card_form.last_four_digits.data = '8888'
    card_form.active = True
    yield card_form


class TestCreditCardForm:

    def test_initialization(self, card_form):
        form_fields = ('account_info', 'last_four_digits', 'active', 'submit')
        for field in form_fields:
            assert hasattr(card_form, field)

    def test_account_info_subform_initialization(self, card_form):
        subform_fields = ('account_id', 'bank_name', 'statement_issue_day',
                          'statement_due_day')
        for field in subform_fields:
            assert hasattr(card_form['account_info'], field)

    def test_prepare_account_choices(self, card_form):
        # Choices should be all user cards, a null selection, and a new option
        choices = [
            (-1, '-'),
            (2, 'Jail (cards: *3335, *3334)'),
            (3, 'TheBank (cards: *3336)'),
            (0, 'New account'),
        ]
        account_id_field = card_form.account_info.account_id
        assert account_id_field.choices == choices

    def test_card_data(self, filled_card_form):
        data = {
            'account_id': 2,
            'last_four_digits': '8888',
            'active': 1,
        }
        assert filled_card_form.card_data == data

    def test_card_data_new_card(self, filled_card_form):
        account_info = filled_card_form.account_info
        # Set the account form bank info to be a new bank
        account_info.account_id.data = 0
        account_info.bank_name.data = 'Jail'
        account_info.statement_issue_day.data = 15
        account_info.statement_due_day.data = 25
        data = {
            'account_id': 4,
            'last_four_digits': '8888',
            'active': 1,
        }
        assert filled_card_form.card_data == data

    def test_account_data_new_bank(self, filled_card_form):
        account_info = filled_card_form.account_info
        # Set the account form bank info to be a new bank
        account_info.account_id.data = 0
        account_info.bank_name.data = 'Test Bank'
        account_info.statement_issue_day.data = 15
        account_info.statement_due_day.data = 25
        data = {
            'account_id': 4,
            'last_four_digits': '8888',
            'active': 1,
        }
        assert filled_card_form.card_data == data

