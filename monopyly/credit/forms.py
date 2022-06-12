"""
Generate credit card forms for the user to complete.
"""
from werkzeug.exceptions import abort
from wtforms.fields import (
    FormField, DecimalField, IntegerField, StringField, BooleanField,
    RadioField, SubmitField, FieldList
)
from wtforms.validators import Optional, DataRequired, Length

from ..common.utils import parse_date
from ..common.form_utils import (
    EntryForm, EntrySubform, AcquisitionSubform, CustomChoiceSelectField,
    Autocompleter, NumeralsOnly, SelectionNotBlank
)
from ..banking.banks import BankHandler
from .accounts import CreditAccountHandler
from .cards import CreditCardHandler
from .statements import CreditStatementHandler
from .transactions import (
    CreditTransactionHandler, CreditSubtransactionHandler, CreditTagHandler
)


class CreditTransactionForm(EntryForm):
    """Form to input/edit credit card transactions."""

    class StatementSubform(EntrySubform):
        """Form to input/edit credit statement identification."""

        class CardSubform(EntrySubform):
            """Form to input/edit credit account identification."""
            bank_name = StringField('Bank')
            last_four_digits = StringField(
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
        issue_date = StringField('Statement Date', filters=[parse_date])

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

    class SubtransactionSubform(EntrySubform):
        """Form to input/edit credit card subtransactions."""
        subtotal = DecimalField(
            'Amount',
            validators=[DataRequired()],
            filters=[lambda x: float(round(x, 2)) if x else None],
            places=2,
        )
        note = StringField('Note', [DataRequired()])
        tags = StringField('Tags')

    # Fields to identify the statement information for the transaction
    statement_info = FormField(StatementSubform)
    # Fields pertaining to the transaction
    transaction_date = StringField(
        'Transaction Date',
        validators=[DataRequired()],
        filters=[parse_date]
    )
    vendor = StringField('Vendor', [DataRequired()])
    # Subtransaction fields (must be at least 1 subtransaction)
    subtransactions = FieldList(FormField(SubtransactionSubform),
                                min_entries=1)
    submit = SubmitField('Save Transaction')

    class TransactionAutocompleter(Autocompleter):
        """Tool to provide autocompletion suggestions for the form."""
        _autocompletion_handler_map = {
            'bank_name': BankHandler,
            'last_four_digits': CreditCardHandler,
            'vendor': CreditTransactionHandler,
            'note': CreditSubtransactionHandler,
        }

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

    def get_transaction_statement(self):
        """Get the credit card statement associated with the transaction."""
        return self.statement_info.get_statement(self.transaction_date.data)

    def prepopulate_transaction(self, transaction):
        """
        Prepopulate the form with credit transaction information.
        """
        subtransaction_db = CreditSubtransactionHandler()
        tag_db = CreditTagHandler()
        subtransactions = subtransaction_db.get_entries((transaction['id'],))
        subtransactions_data = []
        for subtransaction in subtransactions:
            subtransaction_ids = (subtransaction['id'],)
            tags = tag_db.get_entries(subtransaction_ids=subtransaction_ids)
            tag_list = ', '.join([tag['tag_name'] for tag in tags])
            subtransaction_data = {**subtransaction, 'tags': tag_list}
            subtransactions_data.append(subtransaction_data)
        self.prepopulate(transaction, subtransactions=subtransactions_data)

    @classmethod
    def autocomplete(cls, field):
        """Provide autocompletion suggestions for form fields."""
        return cls.TransactionAutocompleter.autocomplete(field)

    @classmethod
    def autocomplete_note(cls, vendor):
        """
        Provide autocompletion suggestions for the note field.

        The note field should be sorted in two levels. The first items
        in the list should be suggested notes based on transactions
        performed at this vendor, since it's likely that a similar
        note may be used at the vendor again. Then, once notes are
        sorted by vendor, they should be organized by their frequency,
        in the database, as is standard for autocompletion suggestions.

        Parameters
        ----------
        vendor : str
            The name of the vendor who's prior notes should be
            prioritized in the autocompletion suggestions.

        Returns
        -------
        suggestions : list of str
            A list of strings giving transaction note suggestions,
            first sorted by the named vendor, then by frequency of
            occurrence in the database.
        """
        suggestions = cls.autocomplete('note')
        db = CreditSubtransactionHandler()
        entries = db.get_entries(fields=('vendor', 'note'))
        # Generate a map of notes for the current vendor
        note_by_vendor = {}
        for entry in entries:
            note = entry['note']
            # Update note if not yet recorded or not yet associated with vendor
            if not note_by_vendor.get(note):
                note_by_vendor[note] = (entry['vendor'] == vendor)
        suggestions.sort(key=note_by_vendor.get, reverse=True)
        return suggestions



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


class CreditCardForm(EntryForm):
    """Form to input/edit credit cards."""

    class AccountSubform(AcquisitionSubform):
        """Form to input/edit account identification."""
        _db_handler_type = CreditAccountHandler
        account_id = AccountSelectField()
        bank_name = StringField('Bank')
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
    last_four_digits = StringField(
        'Last Four Digits',
        validators=[DataRequired(), Length(4), NumeralsOnly()]
    )
    active = BooleanField('Active', default='checked')
    submit = SubmitField('Save Card')

    class CardAutocompleter(Autocompleter):
        """Tool to provide autocompletion suggestions for the form."""
        _autocompletion_handler_map = {
            'bank_name': BankHandler,
        }

    @property
    def card_data(self):
        """Produce a dictionary corresponding to a database card."""
        account = self.account_info.get_account()
        card_data = {'account_id': account['id']}
        for field in ('last_four_digits', 'active'):
            card_data[field] = self[field].data
        return card_data

    @classmethod
    def autocomplete(cls, field):
        """Provide autocompletion suggestions for form fields."""
        return cls.CardAutocompleter.autocomplete(field)


class CardStatementTransferForm(EntryForm):
    """Form indicating if an unpaid statement should be transferred to a new card."""
    transfer = RadioField("transfer", choices=[("yes", "Yes"), ("no", "No")])
    submit = SubmitField("Continue")

