"""Tests for the banking module forms."""
from unittest.mock import Mock, patch
from datetime import datetime, date

import pytest
from werkzeug.exceptions import NotFound

from monopyly.credit.forms import CreditTransactionForm, CreditCardForm


@pytest.fixture
def transaction_form(client_context):
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


class TestCreditTransactionForm:

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

    def test_get_transaction_statement(self, filled_transaction_form):
        statement = filled_transaction_form.get_transaction_statement()
        assert statement['id'] == 4

    @pytest.mark.parametrize(
        'mock_entry',
        [{'card_id': 1,       # must be an integer for field compatibility
          'bank_name': 'Test Bank',
          'last_four_digits': '2222'},
         {'statement_id': 1,  # must be an integer for field compatibility
          'bank_name': 'Test Bank',
          'last_four_digits': '2222',
          'issue_date': '2022-05-15'}]
    )
    def test_prepopulate(self, transaction_form, mock_entry):
        transaction_form.prepopulate(mock_entry)
        # Check that the form data matches the expectation
        mock_issue_date = mock_entry.get('issue_date')
        if mock_issue_date:
            test_issue_datetime = datetime.strptime(mock_issue_date,
                                                    '%Y-%m-%d')
            test_issue_date = test_issue_datetime.date()
        else:
            test_issue_date = None
        transaction_form_data = {
            'csrf_token': None,
            'statement_info': {
                'card_info': {
                    'bank_name': mock_entry.get('bank_name'),
                    'last_four_digits': mock_entry.get('last_four_digits'),
                },
                'issue_date': test_issue_date,
            },
            'transaction_date': None,
            'vendor': None,
            'subtransactions': [
                {'subtotal': None, 'note': None, 'tags': None},
            ],
            'submit': False,
        }
        assert transaction_form.data == transaction_form_data

    @patch('monopyly.credit.forms.CreditTagHandler')
    @patch('monopyly.credit.forms.CreditSubtransactionHandler')
    def test_prepopulate_transaction(self, mock_subtransaction_handler_type,
                                     mock_tag_handler_type, transaction_form):
        # Mock the transaction
        mock_transaction = {
            'id': Mock(),
            'internal_transaction_id': None,
            'bank_id': 100,       # must be an integer for field compatibility
            'bank_name': 'Test Bank',
            'account_id': 100,    # must be an integer for field compatibility
            'card_id': 100,       # must be an integer for field compatibility
            'last_four_digits': '7777',
            'active': True,
            'statement_id': 100,  # must be an integer for field compatibility
            'issue_date': '2022-06-05',
            'due_date': '2022-07-01',
            'transaction_date': '2022-06-01',
            'vendor': 'Test Vendor',
        }
        # Mock the subtransactions returned by the mock handler
        mock_subtransactions = [
            {'id': Mock(), 'subtotal': 25.00, 'note': 'test note one'},
            {'id': Mock(), 'subtotal': 50.00, 'note': 'test note two'},
            {'id': Mock(), 'subtotal': 75.00, 'note': 'test note three'},
        ]
        mock_subtransaction_db = mock_subtransaction_handler_type.return_value
        mock_subtransactions_method = mock_subtransaction_db.get_entries
        mock_subtransactions_method.return_value = mock_subtransactions
        # Mock the tags returned by the mock handler
        mock_tags = [
            [],
            [{'id': Mock(), 'parent_id': Mock(), 'tag_name': 'tag one'}],
            [{'id': Mock(), 'parent_id': Mock(), 'tag_name': 'tag one'},
             {'id': Mock(), 'parent_id': Mock(), 'tag_name': 'tag two'}]
        ]
        mock_tag_db = mock_tag_handler_type.return_value
        mock_tags_method = mock_tag_db.get_entries
        mock_tags_method.side_effect = mock_tags
        transaction_form.prepopulate_transaction(mock_transaction)
        # Check that the form data matches the expectation
        test_subtransactions = []
        for subtransaction, tags in zip(mock_subtransactions, mock_tags):
            test_subtransactions.append({
                **{key: subtransaction[key] for key in ('subtotal', 'note')},
                'tags': ', '.join([tag['tag_name'] for tag in tags]),
            })
        transaction_form_data = {
            'csrf_token': None,
            'statement_info': {
                'card_info': {
                    'bank_name': mock_transaction['bank_name'],
                    'last_four_digits': mock_transaction['last_four_digits'],
                },
                'issue_date': date(2022, 6, 5),
            },
            'transaction_date': date(2022, 6, 1),
            'vendor': mock_transaction['vendor'],
            'subtransactions': test_subtransactions,
            'submit': False,
        }
        assert transaction_form.data == transaction_form_data

    def test_autocompletion_fields(self):
        autocompleter = CreditTransactionForm.TransactionAutocompleter
        autocompletion_fields = [
            'bank_name',
            'last_four_digits',
            'vendor',
            'note',
        ]
        assert autocompleter.autocompletion_fields == autocompletion_fields

    @patch(
        'monopyly.credit.forms.CreditTransactionForm.TransactionAutocompleter'
    )
    def test_autocomplete(self, mock_autocompleter):
        mock_method = mock_autocompleter.autocomplete
        suggestions = CreditTransactionForm.autocomplete('test_field')
        assert suggestions == mock_method.return_value
        mock_method.assert_called_once_with('test_field')

    @pytest.mark.parametrize(
        'vendor, suggestion_order',
        [['Vendor 0', (0, 1, 2)],
         ['Vendor 1', (2, 0, 1)]]
    )
    @patch('monopyly.credit.forms.CreditSubtransactionHandler')
    @patch('monopyly.credit.forms.CreditTransactionForm.autocomplete')
    def test_autocomplete_note(self, mock_method, mock_handler_type,
                               client_context, vendor, suggestion_order):
        mock_suggestions = ['Vendor 0, test 0',
                            'Vendor 0, test 1',
                            'Vendor 1, test 0']
        mock_method.return_value = mock_suggestions.copy()
        mock_subtransactions = [
            {'vendor': 'Vendor 0', 'note': 'Vendor 0, test 0'},
            {'vendor': 'Vendor 0', 'note': 'Vendor 0, test 1'},
            {'vendor': 'Vendor 0', 'note': 'Vendor 0, test 0'},
            {'vendor': 'Vendor 1', 'note': 'Vendor 1, test 0'},
        ]
        mock_db = mock_handler_type.return_value
        mock_db.get_entries.return_value = mock_subtransactions
        suggestions = CreditTransactionForm.autocomplete_note(vendor)
        assert suggestions == [mock_suggestions[i] for i in suggestion_order]


@pytest.fixture
def card_form(client_context):
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

    def test_autocompletion_fields(self):
        autocompleter = CreditCardForm.CardAutocompleter
        autocompletion_fields = ['bank_name']
        assert autocompleter.autocompletion_fields == autocompletion_fields

    @patch('monopyly.credit.forms.CreditCardForm.CardAutocompleter')
    def test_autocomplete(self, mock_autocompleter):
        mock_method = mock_autocompleter.autocomplete
        CreditCardForm.autocomplete('test_field')
        mock_method.assert_called_once_with('test_field')

