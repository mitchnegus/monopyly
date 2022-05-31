"""
Generate credit card forms for the user to complete.
"""
from werkzeug.exceptions import abort
from wtforms.fields import (
    FormField, DecimalField, IntegerField, TextField, BooleanField,
    RadioField, SubmitField, FieldList
)
from wtforms.validators import Optional, DataRequired, Length

from ..common.utils import parse_date
from ..common.form_utils import (
    MonopylyForm, Subform, AcquisitionSubform, CustomChoiceSelectField,
    NumeralsOnly, SelectionNotBlank
)
from ..banking.banks import BankHandler
from .accounts import CreditAccountHandler
from .cards import CreditCardHandler
from .statements import CreditStatementHandler


class CreditTransactionForm(MonopylyForm):
    """Form to input/edit credit card transactions."""

    class StatementSubform(Subform):
        """Form to input/edit credit statement identification."""

        class CardSubform(Subform):
            """Form to input/edit credit account identification."""
            bank_name = TextField('Bank')
            last_four_digits = TextField(
                'Last Four Digits',
                validators=[DataRequired(), Length(4), NumeralsOnly()],
            )

            def get_card(self):
                """Get the credit card described by the form data."""
                card_db = CreditCardHandler()
                return card_db.find_card(self.bank_name.data,
                                         self.last_four_digits.data)

        # Fields to identify the card/bank information for the transaction
        card_info = FormField(CardSubform)
        issue_date = TextField('Statement Date', filters=[parse_date])

        def get_statement(self, transaction_date):
            """Get the credit card statement described by the form data."""
            # Get the card for the transaction
            card = self.card_info.get_card()
            if not card:
                abort(404, 'A card matching the criteria was not found.')
            statement_db = CreditStatementHandler()
            # Get the statement corresponding to the card and issue date
            issue_date = self.issue_date.data
            if issue_date:
                statement = statement_db.find_statement(card, issue_date)
                # Create the statement if it does not already exist
                if not statement:
                    statement = statement_db.add_statement(card, issue_date)
            else:
                # No issue date was given, so the statement must be inferred
                statement = statement_db.infer_statement(
                    card,
                    transaction_date,
                    creation=True
                )
            return statement

    class SubtransactionSubform(Subform):
        """Form to input/edit credit card subtransactions."""
        subtotal = DecimalField(
            'Amount',
            validators=[DataRequired()],
            filters=[lambda x: float(round(x, 2)) if x else None],
            places=2,
        )
        note = TextField('Note', [DataRequired()])
        tags = TextField('Tags')

    # Fields to identify the statement information for the transaction
    statement_info = FormField(StatementSubform)
    # Fields pertaining to the transaction
    transaction_date = TextField(
        'Transaction Date',
        validators=[DataRequired()],
        filters=[parse_date]
    )
    vendor = TextField('Vendor', [DataRequired()])
    # Subtransaction fields (must be at least 1 subtransaction)
    subtransactions = FieldList(FormField(SubtransactionSubform),
                                min_entries=1)
    submit = SubmitField('Save Transaction')

    @property
    def transaction_data(self):
        """
        Produce a dictionary corresponding to a database transaction.

        Creates a dictionary of transaction fields and values, in a
        format that can be added directly to the database as a new
        credit card transaction. The dictionary also includes
        subtransactions (along with tags associated with each
        subtransaction).
        """
        transaction_date = self.transaction_date.data
        statement = self.statement_info.get_statement(transaction_date)
        # Internal transaction IDs are managed by the database handler
        transaction_data = {'internal_transaction_id': None,
                            'statement_id': statement['id']}
        # Access data for each transaction-specific field
        for field in ('transaction_date', 'vendor',):
            transaction_data[field] = self[field].data
        # Aggregate subtransaction information for the transaction
        transaction_data['subtransactions'] = []
        for form in self['subtransactions']:
            subtransaction_data = {}
            # Access data for each subtransaction-specific field
            for field in ('subtotal', 'note'):
                subtransaction_data[field] = form[field].data
            # RETURN AN EMPTY LIST NOT A LIST WITH EMPTY STRING
            raw_tag_data = form['tags'].data.split(',')
            tag_data = [tag.strip() for tag in raw_tag_data if tag]
            subtransaction_data['tags'] = tag_data
            transaction_data['subtransactions'].append(subtransaction_data)
        return transaction_data


class AccountSelectField(CustomChoiceSelectField):
    """Account field that uses the database to prepare field choices."""
    _db_handler_type = CreditAccountHandler

    def __init__(self, **kwargs):
        label = 'Account'
        validators = [SelectionNotBlank()]
        super().__init__(label, validators, coerce=int, **kwargs)

    @staticmethod
    def _format_choice(account):
        card_db = CreditCardHandler()
        cards = card_db.get_entries(account_ids=(account['id'],))
        digits = [f"*{card['last_four_digits']}" for card in cards]
        # Create a description for the account using the bank and card digits
        display_name = f"{account['bank_name']} (cards: {', '.join(digits)})"
        return display_name


class CreditCardForm(MonopylyForm):
    """Form to input/edit credit cards."""

    class AccountSubform(AcquisitionSubform):
        """Form to input/edit account identification."""
        _db_handler_type = CreditAccountHandler
        account_id = AccountSelectField()
        bank_name = TextField('Bank')
        statement_issue_day = IntegerField('Statement Issue Day', [Optional()])
        statement_due_day = IntegerField('Statement Due Day', [Optional()])

        def get_account(self):
            return self.get_entry(self.account_id.data, creation=True)

        def _prepare_mapping(self):
            # Mapping relies on knowing the bank, which must also be acquired
            bank_db = BankHandler()
            bank_name = self.bank_name.data
            banks = bank_db.get_entries(bank_names=(bank_name,))
            if not banks:
                bank_data = {
                    'user_id': bank_db.user_id,
                    'bank_name': bank_name
                }
                bank = bank_db.add_entry(bank_data)
            else:
                bank = banks[0]
            # Mapping must match format for `credit_accounts` database table
            account_data = {
                'bank_id': bank['id'],
                'statement_issue_day': self.statement_issue_day.data,
                'statement_due_day': self.statement_due_day.data,
            }
            return account_data

    account_info = FormField(AccountSubform)
    last_four_digits = TextField(
        'Last Four Digits',
        validators=[DataRequired(), Length(4), NumeralsOnly()]
    )
    active = BooleanField('Active', default='checked')
    submit = SubmitField('Save Card')

    @property
    def card_data(self):
        """Produce a dictionary corresponding to a database card."""
        account = self.account_info.get_account()
        card_data = {'account_id': account['id']}
        for field in ('last_four_digits', 'active'):
            card_data[field] = self[field].data
        return card_data


class CardStatementTransferForm(MonopylyForm):
    """Form indicating if an unpaid statement should be transferred to a new card."""
    transfer = RadioField("transfer", choices=[("yes", "Yes"), ("no", "No")])
    submit = SubmitField("Continue")

