"""Tests for the banking module forms."""
from unittest.mock import Mock, patch
from datetime import date

import pytest
from flask_wtf import FlaskForm
from werkzeug.exceptions import NotFound

from monopyly.database.models import (
    CreditAccount, CreditCard, CreditStatementView, CreditTransactionView,
    CreditSubtransaction
)
from monopyly.credit.forms import (
    CreditAccountSelectField, CreditTransactionForm, CreditCardForm,
    CardStatementTransferForm
)
from ..helpers import helper


class TestCreditAccountSelectField:

    class SampleForm(FlaskForm):
        """A sample form to be used in the subsequent tests."""
        account_id = CreditAccountSelectField()

    def test_field_name(self, client_context):
        form = self.SampleForm()
        assert form.account_id.label.text == "Account"

    def test_prepare_account_choices(self, client_context):
        # The form should have properly generated values from the database
        # - choices include: user accounts, a null selection, and a new option
        expected_choices = [
            (-1, "-"),
            (2, "Jail (cards: *3335, *3334)"),
            (3, "TheBank (cards: *3336)"),
            (0, "New account"),
        ]
        form = self.SampleForm()
        assert form.account_id.choices == expected_choices


@pytest.fixture
def mock_account(client_context):
    mock_account = Mock(spec=CreditAccount)
    return mock_account


@pytest.fixture
def mock_card(mock_account):
    mock_card = Mock(spec=CreditCard)
    mock_card.account = mock_account
    return mock_card


@pytest.fixture
def mock_statement(mock_card):
    mock_statement = Mock(spec=CreditStatementView)
    mock_statement.card = mock_card
    return mock_statement


@pytest.fixture
def mock_transaction(mock_statement):
    mock_transaction = Mock(spec=CreditTransactionView)
    mock_transaction.statement = mock_statement
    mock_transaction.subtransactions = [
        Mock(spec=CreditSubtransaction),
        Mock(spec=CreditSubtransaction),
        Mock(spec=CreditSubtransaction),
    ]
    return mock_transaction


@pytest.fixture
def mock_subtransaction(mock_transaction):
    mock_subtransaction = Mock(spec=CreditSubtransaction)
    mock_subtransaction.transaction = mock_transaction
    mock_subtransaction.tags = []
    for tag_name in ("Tag1", "Tag2", "Tag3"):
        mock_tag = Mock()
        mock_tag.tag_name = tag_name
        mock_subtransaction.tags.append(mock_tag)
    return mock_subtransaction


@pytest.fixture
def card_form(client_context):
    form = CreditCardForm()
    return form


@pytest.fixture
def filled_card_form(card_form):
    # Mock the account info subform data
    card_form.account_info.account_id.data = 2
    # Mock the bank info subform data
    card_form.account_info.bank_info.bank_name.data = "Test Bank"
    # Mock the account data
    card_form.last_four_digits.data = "8888"
    card_form.active.data = True
    return card_form


class TestCreditCardForm:

    def test_initialization(self, card_form):
        form_fields = ("account_info", "last_four_digits", "active", "submit")
        for field in form_fields:
            assert hasattr(card_form, field)

    def test_account_subform_initialization(self, card_form):
        subform_fields = ("account_id", "bank_info", "statement_issue_day",
                          "statement_due_day")
        for field in subform_fields:
            assert hasattr(card_form.account_info, field)

    @patch("monopyly.credit.forms.CreditCardForm.AccountSubform.get_account")
    def test_card_data(self, mock_method, filled_card_form):
        expected_data = {
            "account_id": mock_method.return_value.id,
            "last_four_digits": filled_card_form.last_four_digits.data,
            "active": filled_card_form.active.data,
        }
        assert filled_card_form.card_data == expected_data

    @patch("monopyly.banking.forms.BankSubform.get_bank")
    def test_account_subform_prepare_mapping(self, mock_method, filled_card_form):
        account_subform = filled_card_form.account_info
        data = account_subform._prepare_mapping()
        expected_data = {
            "bank_id": mock_method.return_value.id,
            "statement_issue_day": account_subform.statement_issue_day.data,
            "statement_due_day": account_subform.statement_due_day.data,
        }
        assert data == expected_data

    @patch("monopyly.credit.forms.CreditCardForm.AccountSubform._db_handler")
    def test_account_subform_get_account(self, mock_handler, filled_card_form):
        account_subform = filled_card_form.account_info
        # Test that an existing account entry is returned
        account = account_subform.get_account()
        assert account == mock_handler.get_entry.return_value
        mock_handler.get_entry.assert_called_with(
            account_subform.account_id.data
        )

    @patch("monopyly.credit.forms.CreditCardForm.AccountSubform._db_handler")
    @patch("monopyly.credit.forms.CreditCardForm.AccountSubform._prepare_mapping")
    def test_account_subform_get_new_account(self, mock_method, mock_handler,
                                             filled_card_form):
        account_subform = filled_card_form.account_info
        # Mock the subform's mapping
        mock_method.return_value = {"test": "mapping"}
        # Set the account ID to 0, indicating that the account is a new submission
        account_subform.account_id.data = 0
        # Test that a new account entry is created and returned
        account = account_subform.get_account()
        assert account == mock_handler.add_entry.return_value
        mock_handler.add_entry.assert_called_with(
            **mock_method.return_value
        )

    def test_account_subform_gather_data(self, card_form, mock_account):
        account_subform = card_form.account_info
        data = account_subform.gather_entry_data(mock_account)
        expected_data = {
            "account_id": mock_account.id,
            "statement_issue_day": mock_account.statement_issue_day,
            "statement_due_day": mock_account.statement_due_day,
        }
        assert data == expected_data

    def test_account_subform_gather_data_invalid(self, card_form):
        account_subform = card_form.account_info
        with pytest.raises(TypeError):
            account_subform.gather_entry_data(None)

    @patch(
        "monopyly.credit.forms.CreditCardForm.AccountSubform.gather_entry_data"
    )
    def test_gather_data(self, mock_method, card_form, mock_card):
        data = card_form.gather_entry_data(mock_card)
        expected_data = {
            "last_four_digits": mock_card.last_four_digits,
            "active": mock_card.active,
            "account_info": mock_method.return_value
        }
        assert data == expected_data

    def test_gather_data_invalid(self, card_form):
        with pytest.raises(TypeError):
            card_form.gather_entry_data(None)

    @patch("monopyly.credit.forms.CreditCardForm.process")
    @patch("monopyly.credit.forms.CreditCardForm.gather_entry_data")
    def test_prepopulate(self, mock_gather_method, mock_process_method,
                         card_form, mock_card):
        card_form.prepopulate(mock_card)
        mock_process_method.assert_called_once_with(
            data=mock_gather_method.return_value
        )


class TestCardStatementTransferForm:

    def test_initialization(self, client_context):
        form = CardStatementTransferForm()
        for field in ("transfer", "submit"):
            assert hasattr(form, field)


@pytest.fixture
def transaction_form(client_context):
    return CreditTransactionForm()


@pytest.fixture
def filled_transaction_form(transaction_form):
    # Mock the statement info subform data
    transaction_form.statement_info.issue_date.data = date(2020, 5, 15)
    # Mock the card info subform data
    transaction_form.statement_info.card_info.bank_name.data = "Jail"
    transaction_form.statement_info.card_info.last_four_digits.data = "3335"
    # Mock the transaction data
    transaction_form.transaction_date.data = date(2020, 5, 4)
    transaction_form.vendor.data = "O.B. (Wan) Railroad"
    # Mock the subtransaction subform data
    transaction_form.subtransactions[0].subtotal.data = 42.00
    transaction_form.subtransactions[0].note.data = "Wrong SciFi movie?"
    transaction_form.subtransactions[0].tags.data = "TEST TAG"
    return transaction_form


class TestCreditTransactionForm:

    def test_initialization(self, transaction_form):
        form_fields = ("statement_info", "transaction_date", "vendor",
                       "subtransactions", "submit")
        for field in form_fields:
            assert hasattr(transaction_form, field)

    def test_statement_subform_initialization(self, transaction_form):
        subform_fields = ("card_info", "issue_date")
        for field in subform_fields:
            assert hasattr(transaction_form.statement_info, field)

    def test_card_subform_initialization(self, transaction_form):
        subform_fields = ("bank_name", "last_four_digits")
        for field in subform_fields:
            assert hasattr(transaction_form.statement_info.card_info, field)

    def test_subtransaction_subform_initialization(self, transaction_form):
        subform_fields = ("subtotal", "note", "tags")
        for subtransaction_form in transaction_form.subtransactions:
           for field in subform_fields:
                assert hasattr(subtransaction_form, field)

    @patch("monopyly.credit.forms.CreditTransactionForm.get_transaction_statement")
    def test_transaction_data(self, mock_method, filled_transaction_form):
        filled_form_subtransaction = filled_transaction_form.subtransactions[0]
        expected_data = {
            "internal_transaction_id": None,
            "statement_id": mock_method.return_value.id,
            "transaction_date": filled_transaction_form.transaction_date.data,
            "vendor": filled_transaction_form.vendor.data,
            "subtransactions": [{
                "note": filled_form_subtransaction.note.data,
                "subtotal": filled_form_subtransaction.subtotal.data,
                "tags": filled_form_subtransaction.tags.data.split(","),
            }],
        }
        assert filled_transaction_form.transaction_data == expected_data
        # Check that there was actually only one subtransaction
        assert len(filled_transaction_form.subtransactions) == 1

    @patch(
        "monopyly.credit.forms.CreditTransactionForm.StatementSubform.CardSubform._db_handler"
    )
    def test_card_subform_get_card(self, mock_handler, filled_transaction_form):
        card_subform = filled_transaction_form.statement_info.card_info
        card = card_subform.get_card()
        assert card == mock_handler.find_card.return_value
        mock_handler.find_card.assert_called_with(
            bank_name=card_subform.bank_name.data,
            last_four_digits=card_subform.last_four_digits.data
        )

    def test_card_subform_gather_data(self, transaction_form, mock_card):
        card_subform = transaction_form.statement_info.card_info
        data = card_subform.gather_entry_data(mock_card)
        expected_data = {
            "bank_name": mock_card.account.bank.bank_name,
            "last_four_digits": mock_card.last_four_digits,
        }
        assert data == expected_data

    def test_card_subform_gather_data_invalid(self, transaction_form):
        card_subform = transaction_form.statement_info.card_info
        with pytest.raises(TypeError):
            card_subform.gather_entry_data(None)

    @patch(
        "monopyly.credit.forms.CreditTransactionForm.StatementSubform"
        ".determine_statement"
    )
    def test_statement_subform_get_statement(self, mock_method,
                                             filled_transaction_form):
        statement = filled_transaction_form.statement_info.get_statement(
            date(2022, 6, 1)
        )
        assert statement == mock_method.return_value

    @patch(
        "monopyly.credit.forms.CreditTransactionForm.StatementSubform"
        ".CardSubform.get_card"
    )
    def test_statement_subform_get_statement_no_card(self, mock_method,
                                                     filled_transaction_form):
        mock_method.return_value = None
        with pytest.raises(NotFound):
            filled_transaction_form.statement_info.get_statement(None)

    @patch("monopyly.credit.forms.CreditTransactionForm.StatementSubform._db_handler")
    def test_statement_subform_determine_existing_statement(self, mock_handler,
                                                            transaction_form,
                                                            mock_card):
        statement_subform = transaction_form.statement_info
        mock_method = mock_handler.find_statement
        # Mock the requirements for returning an existing statement
        mock_issue_date = Mock()
        statement_subform.issue_date.data = mock_issue_date
        # Ensure that the existing statement is returned
        transaction_date = date(2022, 6, 1)
        statement = statement_subform.determine_statement(
            mock_card, transaction_date
        )
        assert statement == mock_method.return_value
        mock_method.assert_called_with(mock_card.id, mock_issue_date)

    @patch("monopyly.credit.forms.CreditTransactionForm.StatementSubform._db_handler")
    def test_statement_subform_determine_new_statement(self, mock_handler,
                                                       transaction_form,
                                                       mock_card):
        statement_subform = transaction_form.statement_info
        mock_method = mock_handler.add_statement
        # Mock the requirements for returning a new statement
        mock_issue_date = Mock()
        statement_subform.issue_date.data = mock_issue_date
        mock_handler.find_statement.return_value = None
        # Ensure that the new statement is returned
        transaction_date = date(2022, 6, 1)
        statement = statement_subform.determine_statement(
            mock_card, transaction_date
        )
        assert statement == mock_method.return_value
        mock_method.assert_called_with(mock_card, mock_issue_date)

    @patch("monopyly.credit.forms.CreditTransactionForm.StatementSubform._db_handler")
    def test_statement_subform_determine_inferred_statement(self, mock_handler,
                                                            transaction_form,
                                                            mock_card):
        statement_subform = transaction_form.statement_info
        mock_method = mock_handler.infer_statement
        # Mock the requirements for returning a new statement
        statement_subform.issue_date.data = None
        # Ensure that the new statement is returned
        transaction_date = date(2022, 6, 1)
        statement = statement_subform.determine_statement(
            mock_card, transaction_date
        )
        assert statement == mock_method.return_value
        mock_method.assert_called_with(
            mock_card, transaction_date, creation=True
        )

    @patch(
        "monopyly.credit.forms.CreditTransactionForm.StatementSubform"
        ".CardSubform.gather_entry_data"
    )
    def test_statement_subform_gather_statement_data(self, mock_method,
                                                     transaction_form,
                                                     mock_statement):
        statement_subform = transaction_form.statement_info
        data = statement_subform.gather_entry_data(mock_statement)
        expected_data = {
            "issue_date": mock_statement.issue_date,
            "card_info": mock_method.return_value
        }
        assert data == expected_data

    @patch(
        "monopyly.credit.forms.CreditTransactionForm.StatementSubform"
        ".CardSubform.gather_entry_data"
    )
    def test_statement_subform_gather_card_data(self, mock_method,
                                                transaction_form, mock_card):
        statement_subform = transaction_form.statement_info
        data = statement_subform.gather_entry_data(mock_card)
        expected_data = {
            "card_info": mock_method.return_value
        }
        assert data == expected_data

    def test_statement_subform_gather_data_invalid(self, transaction_form):
        statement_subform = transaction_form.statement_info
        with pytest.raises(TypeError):
            statement_subform.gather_entry_data(None)

    def test_subtransaction_subform_gather_data(self, transaction_form,
                                                mock_subtransaction):
        subtransaction_subform = transaction_form.subtransactions[0]
        data = subtransaction_subform.gather_entry_data(mock_subtransaction)
        expected_data = {
            "subtotal": mock_subtransaction.subtotal,
            "note": mock_subtransaction.note,
            "tags": ", ".join([_.tag_name for _ in mock_subtransaction.tags])
        }
        assert data == expected_data

    def test_subtransaction_subform_gather_data_invalid(self,
                                                        transaction_form):
        subtransaction_subform = transaction_form.subtransactions[0]
        with pytest.raises(TypeError):
            subtransaction_subform.gather_entry_data(None)

    @patch(
        "monopyly.credit.forms.CreditTransactionForm.StatementSubform.get_statement"
    )
    def test_get_transaction_statement(self, mock_method, transaction_form):
        statement = transaction_form.get_transaction_statement()
        assert statement == mock_method.return_value
        mock_method.assert_called_with(transaction_form.transaction_date.data)

    @patch(
        "monopyly.credit.forms.CreditTransactionForm.StatementSubform"
        ".gather_entry_data"
    )
    @patch(
        "monopyly.credit.forms.CreditTransactionForm.SubtransactionSubform"
        ".gather_entry_data"
    )
    def test_gather_transaction_data(self, mock_subtransaction_method,
                                     mock_statement_method, transaction_form,
                                     mock_transaction):
        # NOTE: We must delete the "_formfield" attribute of the
        # `SubtransactionForm.gather_entry_data` MagicMock object or else
        # WTForms will think that it is an unbound field; perhaps WTForms
        # should use a better method for determining unbound fields
        del mock_subtransaction_method._formfield
        data = transaction_form.gather_entry_data(mock_transaction)
        expected_data = {
            "transaction_date": mock_transaction.transaction_date,
            "vendor": mock_transaction.vendor,
            "subtransactions": 3*[mock_subtransaction_method.return_value],
            "statement_info": mock_statement_method.return_value
        }
        assert data == expected_data

    @patch(
        "monopyly.credit.forms.CreditTransactionForm.StatementSubform"
        ".gather_entry_data"
    )
    def test_gather_statement_data(self, mock_statement_method,
                                   transaction_form, mock_statement):
        data = transaction_form.gather_entry_data(mock_statement)
        expected_data = {
            "statement_info": mock_statement_method.return_value
        }
        assert data == expected_data

    @patch(
        "monopyly.credit.forms.CreditTransactionForm.StatementSubform"
        ".gather_entry_data"
    )
    def test_gather_card_data(self, mock_statement_method, transaction_form,
                              mock_card):
        data = transaction_form.gather_entry_data(mock_card)
        expected_data = {
            "statement_info": mock_statement_method.return_value
        }
        assert data == expected_data

    def test_gather_data_invalid(self, transaction_form):
        with pytest.raises(TypeError):
            transaction_form.gather_entry_data(None)

    @patch("monopyly.credit.forms.CreditTransactionForm.process")
    @patch("monopyly.credit.forms.CreditTransactionForm.gather_entry_data")
    def test_prepopulate(self, mock_gather_method, mock_process_method,
                         transaction_form, mock_transaction):
        transaction_form.prepopulate(mock_transaction)
        mock_process_method.assert_called_once_with(
            data=mock_gather_method.return_value
        )

    @pytest.mark.parametrize(
        "field, sort_fields, top_expected_suggestions, expected_suggestions",
        [["vendor", {},                       # sorted by frequency [only]
          ("Boardwalk",),
          ("Income Tax Board", "Pennsylvania Avenue",
           "Park Place", "Community Chest",
           "Electric Company", "Water Works",
           "Reading Railroad", "JP Morgan Chance",
           "Top Left Corner", "Marvin Gardens",
           "Boardwalk")],
         ["note", {"vendor": "Park Place"},   # sorted by vendor key, then note frequency
          ("One for the park", "One for the place"),
          ("Parking (thought it was free)", "Big house tour",
           "Conducting business", "Tough loss",
           "Electric bill", "Refund",
           "Merry-go-round", "Credit card payment",
           "One for the park", "One for the place",
           "Expensive real estate", "Back for more...")]]
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

