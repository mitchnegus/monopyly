"""
Generate credit card forms for the user to complete.
"""
from werkzeug.exceptions import abort
from wtforms.fields import (
    FormField, FieldList, IntegerField, StringField, BooleanField, RadioField,
    SubmitField
)
from wtforms.validators import Optional, DataRequired, Length

from ..database.models import (
    Bank, CreditAccount, CreditCard, CreditStatementView,
    CreditTransactionView, CreditSubtransaction
)
from ..common.utils import parse_date
from ..common.forms import (
    EntryForm, EntrySubform, AcquisitionSubform, TransactionForm
)
from ..common.forms.fields import CustomChoiceSelectField
from ..common.forms.utils import Autocompleter
from ..common.forms.validators import NumeralsOnly, SelectionNotBlank
from ..banking.banks import BankHandler
from ..banking.forms import BankSelectField, BankSubform
from .accounts import CreditAccountHandler
from .cards import CreditCardHandler
from .statements import CreditStatementHandler


class CreditAccountSelectField(CustomChoiceSelectField):
    """Account field that uses the database to prepare field choices."""
    _db_handler = CreditAccountHandler

    def __init__(self, **kwargs):
        super().__init__(label="Account", **kwargs)

    @staticmethod
    def _format_choice(account):
        cards = CreditCardHandler.get_cards(account_ids=(account.id,))
        digits = [f"*{card.last_four_digits}" for card in cards]
        bank_name = account.bank.bank_name
        # Display cards associated with the credit account in parentheses
        display_name = f"{bank_name} (cards: {', '.join(digits)})"
        return display_name


class CreditCardForm(EntryForm):
    """Form to input/edit credit cards."""

    class AccountSubform(AcquisitionSubform):
        """Form to input/edit account identification."""
        _db_handler = CreditAccountHandler
        # Fields to identify the bank information for the account
        bank_info = FormField(BankSubform)
        # Fields pertaining to the account
        account_id = CreditAccountSelectField()
        statement_issue_day = IntegerField('Statement Issue Day', [Optional()])
        statement_due_day = IntegerField('Statement Due Day', [Optional()])

        def get_account(self):
            return self._produce_entry_from_field("account_id")

        def _prepare_mapping(self):
            # Mapping relies on knowing the bank, which must also be acquired
            bank = self.bank_info.get_bank()
            # Mapping must match format for `credit_accounts` database table
            account_data = {
                'bank_id': bank.id,
                'statement_issue_day': self.statement_issue_day.data,
                'statement_due_day': self.statement_due_day.data,
            }
            return account_data

        def gather_entry_data(self, entry):
            """Gather data for the form from the given database entry."""
            if isinstance(entry, CreditAccount):
                data = {
                    'account_id': entry.id,
                    'statement_issue_day': entry.statement_issue_day,
                    'statement_due_day': entry.statement_due_day,
                }
            else:
                self._raise_gather_fail_error((CreditAccount,), entry)
            return data

    # Fields to identify the account information for the card
    account_info = FormField(AccountSubform)
    # Fields pertaining to the card
    last_four_digits = StringField(
        'Last Four Digits',
        validators=[DataRequired(), Length(4), NumeralsOnly()]
    )
    active = BooleanField('Active', default='checked')
    submit = SubmitField('Save Card')

    @property
    def card_data(self):
        """Produce a dictionary corresponding to a database card."""
        account = self.account_info.get_account()
        card_data = {
            'account_id': account.id,
            'last_four_digits': self.last_four_digits.data,
            'active': self.active.data
        }
        return card_data

    def gather_entry_data(self, entry):
        """Gather data for the form from the given database entry."""
        if isinstance(entry, CreditCard):
            data = {
                'last_four_digits': entry.last_four_digits,
                'active': entry.active,
            }
            account_info = entry.account
        else:
            self._raise_gather_fail_error((CreditCard,), entry)
        data['account_info'] = self.account_info.gather_entry_data(account_info)
        return data


class CardStatementTransferForm(EntryForm):
    """Form indicating if an unpaid statement should be transferred to a new card."""
    transfer = RadioField("transfer", choices=[("yes", "Yes"), ("no", "No")])
    submit = SubmitField("Continue")


class CreditTransactionForm(TransactionForm):
    """Form to input/edit credit card transactions."""

    class StatementSubform(EntrySubform):
        """Form to input/edit credit statement identification."""
        _db_handler = CreditStatementHandler

        class CardSubform(EntrySubform):
            """Form to input/edit credit account identification."""
            _db_handler = CreditCardHandler
            # Fields pertaining to the card
            bank_name = StringField('Bank')
            last_four_digits = StringField(
                'Last Four Digits',
                validators=[DataRequired(), Length(4), NumeralsOnly()],
            )

            def get_card(self):
                """Get the credit card described by the form data."""
                return self._db_handler.find_card(
                    bank_name=self.bank_name.data,
                    last_four_digits=self.last_four_digits.data,
                )

            def gather_entry_data(self, entry):
                """Gather data for the form from the given database entry."""
                if isinstance(entry, CreditCard):
                    data = {
                        'bank_name': entry.account.bank.bank_name,
                        'last_four_digits': entry.last_four_digits,
                    }
                else:
                    self._raise_gather_fail_error((CreditCard,), entry)
                return data

        # Fields to identify the card/bank information for the statement
        card_info = FormField(CardSubform)
        # Fields pertaining to the statement
        issue_date = StringField('Statement Date', filters=[parse_date])

        def get_statement(self, transaction_date):
            """Get the credit card statement described by the form data."""
            # Get the card for the transaction
            card = self.card_info.get_card()
            if not card:
                msg = (
                    "No statement was found because no cards matched the "
                    "necessary criteria."
                )
                abort(404, msg)
            return self.determine_statement(card, transaction_date)

        def determine_statement(self, card, transaction_date):
            """
            Determine the statement based on the given information.

            Given a credit card and transaction date, determine the
            statement belonging to the transaction. If the form includes
            a statement issue date, then either the matching statement
            is returned, or a new matching statement is created.
            Otherwise, a statement is inferred based on the given
            transaction date (and, again, created if it does not already
            exist in the database).

            Parameters
            ----------
            card : database.models.CreditCard
                The credit card used for this transaction.
            transaction_date : datetime.date
                The date of the transaction.

            Returns
            -------
            statement : database.models.CreditStatementView
                The credit statement belonging to this transaction.
            """
            issue_date = self.issue_date.data
            if issue_date:
                statement = self._db_handler.find_statement(
                    card.id, issue_date
                )
                # Create the statement if it does not already exist
                if not statement:
                    statement = self._db_handler.add_statement(
                        card, issue_date
                    )
            else:
                # No issue date was given, so the statement must be inferred
                statement = self._db_handler.infer_statement(
                    card, transaction_date, creation=True
                )
            return statement

        def gather_entry_data(self, entry):
            """Gather data for the form from the given database entry."""
            if isinstance(entry, CreditStatementView):
                data = {
                    'issue_date': entry.issue_date
                }
                card_info = entry.card
            elif isinstance(entry, CreditCard):
                data = {}
                card_info = entry
            else:
                self._raise_gather_fail_error(
                    (CreditStatementView, CreditCard), entry
                )
            # Prepare data for the card subforms
            data['card_info'] = self.card_info.gather_entry_data(card_info)
            return data

    class SubtransactionSubform(TransactionForm.SubtransactionSubform):
        """Form to input/edit credit card subtransactions."""
        # Fields pertaining to the credit subtransaction
        tags = StringField('Tags')

        @property
        def subtransaction_data(self):
            """
            Produce a dictionary corresponding to a database subtransaction.
            """
            raw_tag_data = self.tags.data.split(',')
            data = super().subtransaction_data
            data["tags"] = [tag.strip() for tag in raw_tag_data if tag]
            return data

        def gather_entry_data(self, entry):
            """Gather data for the form from the given database entry."""
            if isinstance(entry, CreditSubtransaction):
                tag_names = [tag.tag_name for tag in entry.tags]
                data = {
                    'subtotal': entry.subtotal,
                    'note': entry.note,
                    'tags': ', '.join(tag_names),
                }
            else:
                self._raise_gather_fail_error((CreditSubtransaction,), entry)
            return data

    # Fields to identify the statement information for the transaction
    statement_info = FormField(StatementSubform)
    # Fields pertaining to the credit transaction
    vendor = StringField('Vendor', [DataRequired()])
    # Subtransaction fields (must be at least 1 subtransaction)
    subtransactions = FieldList(
        FormField(SubtransactionSubform),
        min_entries=1,
    )
    # Define an autocompleter for the form
    _autocompleter = Autocompleter({
        'bank_name': Bank,
        'last_four_digits': CreditCard,
        'vendor': CreditTransactionView,
        'note': CreditSubtransaction,
    })

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
        statement = self.get_transaction_statement()
        return self._prepare_transaction_data(statement)

    def get_transaction_statement(self):
        """Get the credit card statement associated with the transaction."""
        return self.statement_info.get_statement(self.transaction_date.data)

    def _prepare_transaction_data(self, statement):
        data = super()._prepare_transaction_data()
        data["statement_id"] = statement.id
        data["vendor"] = self.vendor.data
        return data

    def gather_entry_data(self, entry):
        """Gather data for the form from the given database entry."""
        if isinstance(entry, CreditTransactionView):
            data = self._gather_transaction_data(entry)
            statement_info = entry.statement
        elif isinstance(entry, (CreditCard, CreditStatementView)):
            data = {}
            statement_info = entry
        else:
            self._raise_gather_fail_error(
                (CreditCard, CreditStatementView), entry
            )
        # Prepare data for the statement/subtransaction subforms
        data['statement_info'] = self.statement_info.gather_entry_data(
            statement_info
        )
        return data

    def _gather_transaction_data(self, transaction):
        """Gather credit transaction-specific data."""
        data = super()._gather_transaction_data(transaction)
        data["vendor"] = transaction.vendor
        return data

