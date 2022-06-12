"""
Generate banking forms for the user to fill out.
"""
from wtforms.fields import (
    FormField, DecimalField, StringField, BooleanField, SubmitField, FieldList
)
from wtforms.validators import Optional, DataRequired, Length

from ..common.utils import parse_date
from ..common.form_utils import (
    EntryForm, EntrySubform, AcquisitionSubform, CustomChoiceSelectField,
    Autocompleter, NumeralsOnly, SelectionNotBlank
)
from .banks import BankHandler
from .accounts import BankAccountTypeHandler, BankAccountHandler
from .transactions import BankTransactionHandler, BankSubtransactionHandler


class BankTransactionForm(EntryForm):
    """Form to input/edit bank transactions."""

    class AccountSubform(EntrySubform):
        """Form to input/edit bank account identification."""
        bank_name = StringField('Bank')
        last_four_digits = StringField(
            'Last Four Digits',
            validators=[DataRequired(), Length(4), NumeralsOnly()]
        )
        type_name = StringField('AccountType', validators=[DataRequired()])

        def get_account(self):
            """Get the bank account described by the form data."""
            account_db = BankAccountHandler()
            return account_db.find_account(self.bank_name.data,
                                           self.last_four_digits.data,
                                           self.type_name.data)

    class SubtransactionSubform(EntrySubform):
        """Form to input/edit bank subtransactions."""
        subtotal = DecimalField(
            'Amount',
            validators=[DataRequired()],
            filters=[lambda x: float(round(x, 2)) if x else None],
            places=2,
        )
        note = StringField('Note', [DataRequired()])

    # Fields to identify the bank account information for the transaction
    account_info = FormField(AccountSubform)
    # Fields pertaining to the transaction
    transaction_date = StringField(
        'Transaction Date',
        validators=[DataRequired()],
        filters=[parse_date]
    )
    # Subtransaction fields (must be at least 1 subtransaction)
    subtransactions = FieldList(FormField(SubtransactionSubform),
                                min_entries=1)
    # Fields to identify a second bank involved in a funds transfer
    transfer_account_info = FieldList(FormField(AccountSubform),
                                      min_entries=0, max_entries=1)
    submit = SubmitField('Save Transaction')

    class TransactionAutocompleter(Autocompleter):
        """Tool to provide autocompletion suggestions for the form."""
        _autocompletion_handler_map = {
            'bank_name': BankHandler,
            'last_four_digits': BankAccountHandler,
            'type_name': BankAccountTypeHandler,
            'note': BankSubtransactionHandler,
        }

    @property
    def transaction_data(self):
        """
        Produce a dictionary corresponding to a database transaction.

        Creates a dictionary of transaction fields and values, in a
        format that can be added directly to the database as a new
        bank transaction. The dictionary also includes subtransactions.
        """
        account = self.get_transaction_account()
        # Internal transaction IDs are managed by the database handler
        transaction_data = {'internal_transaction_id': None,
                            'account_id': account['id']}
        # Access data for each transaction-specific field
        for field in ('transaction_date',):
            transaction_data[field] = self[field].data
        # Aggregate subtransaction information for the transaction
        transaction_data['subtransactions'] = []
        for form in self['subtransactions']:
            subtransaction_data = {}
            # Access data for each subtransaction-specific field
            for field in ('subtotal', 'note'):
                subtransaction_data[field] = form[field].data
            transaction_data['subtransactions'].append(subtransaction_data)
        return transaction_data

    @property
    def transfer_data(self):
        """
        Produce a dictionary corresponding to the transfer transaction.

        Creates a dictionary of transaction fields and values, in a
        format that can be added directly to the database as a new
        bank transaction, for the transfer.
        """
        if not self.transfer_account_info:
            return None
        account = self.get_transfer_account()
        # Internal transaction IDs are managed by the database handler
        transfer_data = {'internal_transaction_id': None,
                         'account_id': account['id'],
                         'transaction_date': self['transaction_date'].data}
        # Aggregate subtransaction information for the transaction
        transfer_data['subtransactions'] = []
        for subform in self['subtransactions']:
            subtransaction_data = {}
            # Access data for each subtransaction-specific field
            subtransaction_data['subtotal'] = -subform['subtotal'].data
            subtransaction_data['note'] = subform['note'].data
            transfer_data['subtransactions'].append(subtransaction_data)
        return transfer_data

    def get_transaction_account(self):
        """Get the bank account associated with the transaction."""
        return self.account_info.get_account()

    def get_transfer_account(self):
        """Get the bank account linked in a transfer."""
        return self.transfer_account_info[0].get_account()

    def prepopulate_transaction(self, transaction):
        """
        Prepopulate the form with bank transaction information.
        """
        subtransaction_db = BankSubtransactionHandler()
        subtransactions = subtransaction_db.get_entries((transaction['id'],))
        # Prepare and prepopulate data from the transaction/subtransaction info
        self.prepopulate(transaction, subtransactions=subtransactions)

    @classmethod
    def autocomplete(cls, field):
        """Provide autocompletion suggestions for form fields."""
        return cls.TransactionAutocompleter.autocomplete(field)


class BankSelectField(CustomChoiceSelectField):
    """Bank field that uses the database to prepare field choices."""
    _db_handler_type = BankHandler

    def __init__(self, **kwargs):
        label = 'Bank'
        validators = [SelectionNotBlank()]
        super().__init__(label, validators, coerce=int, **kwargs)

    @staticmethod
    def _format_choice(bank):
        display_name = bank['bank_name']
        return display_name


class AccountTypeSelectField(CustomChoiceSelectField):
    """Account type field that uses the database to prepare field choices."""
    _db_handler_type = BankAccountTypeHandler

    def __init__(self, **kwargs):
        label = 'Account Type'
        validators = [SelectionNotBlank()]
        super().__init__(label, validators, coerce=int, **kwargs)

    @staticmethod
    def _format_choice(account_type):
        display_name = account_type['type_name']
        # Display name abbreviations in parentheses
        if account_type['type_common_name'] != display_name:
            display_name += f" ({account_type['type_common_name']})"
        return display_name


class BankAccountForm(EntryForm):
    """Form to input/edit bank accounts."""

    class BankSubform(AcquisitionSubform):
        """Form to input/edit bank identification."""
        _db_handler_type = BankHandler
        bank_id = BankSelectField()
        bank_name = StringField('Bank Name')

        def get_bank(self):
            """Get the bank described by the form data."""
            return self.get_entry(self.bank_id.data, creation=True)

        def _prepare_mapping(self):
            # Mapping must match format for `banks` database table
            bank_data = {
                'user_id': self.db.user_id,
                'bank_name': self.bank_name.data,
            }
            return bank_data

    class AccountTypeSubform(AcquisitionSubform):
        """Form to input/edit bank account types."""
        _db_handler_type = BankAccountTypeHandler
        account_type_id = AccountTypeSelectField()
        type_name = StringField('Account Type Name')

        def get_account_type(self):
            """Get the bank account type described by the form data."""
            return self.get_entry(self.account_type_id.data, creation=True)

        def _prepare_mapping(self):
            # Mapping must match format for `bank_account_types` database table
            account_type_data = {
                'user_id': self.db.user_id,
                'type_name': self.type_name.data,
                'type_abbreviation': None,
            }
            return account_type_data

    bank_info = FormField(BankSubform)
    account_type_info = FormField(AccountTypeSubform)
    last_four_digits = StringField(
        'Last Four Digits',
        validators=[DataRequired(), Length(4), NumeralsOnly()]
    )
    active = BooleanField('Active', default='checked')
    submit = SubmitField('Save Account')

    @property
    def account_data(self):
        """Produce a dictionary corresponding to a database bank account."""
        bank = self.bank_info.get_bank()
        account_type = self.account_type_info.get_account_type()
        account_data = {'bank_id': bank['id'],
                        'account_type_id': account_type['id']}
        for field in ('last_four_digits', 'active'):
            account_data[field] = self[field].data
        return account_data

