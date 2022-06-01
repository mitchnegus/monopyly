"""
Generate banking forms for the user to fill out.
"""
from functools import wraps

from wtforms.fields import (
    FormField, DecimalField, TextField, BooleanField, SubmitField, FieldList
)
from wtforms.validators import Optional, DataRequired, Length

from ..common.utils import parse_date
from ..common.form_utils import (
    MonopylyForm, Subform, AcquisitionSubform, CustomChoiceSelectField,
    NumeralsOnly, SelectionNotBlank
)
from .banks import BankHandler
from .accounts import BankAccountTypeHandler, BankAccountHandler
from .transactions import BankTransactionHandler, BankSubtransactionHandler


class BankTransactionForm(MonopylyForm):
    """Form to input/edit bank transactions."""

    class AccountSubform(Subform):
        """Form to input/edit bank account identification."""
        bank_name = TextField('Bank')
        last_four_digits = TextField(
            'Last Four Digits',
            validators=[DataRequired(), Length(4), NumeralsOnly()]
        )
        type_name = TextField('AccountType', validators=[DataRequired()])

        def get_account(self):
            """Get the bank account described by the form data."""
            account_db = BankAccountHandler()
            return account_db.find_account(self.bank_name.data,
                                           self.last_four_digits.data,
                                           self.type_name.data)

    class SubtransactionSubform(Subform):
        """Form to input/edit bank subtransactions."""
        subtotal = DecimalField(
            'Amount',
            validators=[DataRequired()],
            filters=[lambda x: float(round(x, 2)) if x else None],
            places=2,
        )
        note = TextField('Note', [DataRequired()])

    # Fields to identify the bank account information for the transaction
    account_info = FormField(AccountSubform)
    # Fields pertaining to the transaction
    transaction_date = TextField(
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

    @classmethod
    def generate_new(cls, bank_id=None, account_id=None):
        """
        Create a bank account transaction form for a new transaction.

        Generate a form for a new bank account transaction. This form
        should be prepopulated with any bank and account information
        that is available (as determined by a bank ID or account ID from
        the database that is provided as an argument).

        Parameters
        ----------
        bank_id : int
            The ID of a bank to use when prepolating the form.
        account_id : int
            The ID of a bank account to use when prepolating the form.

        Returns
        -------
        form : BankTransactionForm
            An instance of this class with any prepopulated information.
        """
        # Bank ID must be known (at least) for there to be data to prepare
        data = cls._prepare_new_data(bank_id, account_id) if bank_id else None
        return cls(data=data)

    @classmethod
    def _prepare_new_data(cls, bank_id, account_id):
        bank_info = cls._prepare_submapping(
            bank_id,
            BankHandler,
            ('bank_name',),
        )
        data = {'account_info': bank_info}
        # Add account info to the data if that is known
        if account_id:
            account_info = cls._prepare_submapping(
                account_id,
                BankAccountHandler,
                ('last_four_digits', 'type_name'),
            )
            data['account_info'].update(account_info)
        return data

    @classmethod
    def generate_update(cls, transaction_id):
        """
        Prepare a bank account transaction form to update a transaction.

        Generate a form to update an existing bank account transaction.
        This form should be prepopulated with all transaction
        information that has previously been provided so that it can be
        updated.

        Parameters
        ----------
        transaction_id : int
            The ID of the transaction to be updated.

        Returns
        -------
        form : BankTransactionForm
            An instance of this class with any prepopulated information.
        """
        data = cls._prepare_update_data(transaction_id)
        return cls(data=data)

    @classmethod
    def _prepare_update_data(cls, transaction_id):
        # Get the transaction information from the database
        transaction_info = cls._prepare_submapping(
            transaction_id,
            BankTransactionHandler,
            ('bank_name', 'last_four_digits', 'type_name', 'transaction_date'),
        )
        data = {'transaction_date': transaction_info.pop('transaction_date')}
        data['account_info'] = transaction_info
        # Transfer data is cannot be updated (update transfers independently)
        data['transfer_account_info'] = {}
        # Get the subtransaction information from the database
        data['subtransactions'] = cls._prepare_subtransactions_submapping(
            transaction_id
        )
        return data

    @classmethod
    def _prepare_subtransactions_submapping(cls, transaction_id):
        """Prepare a subset of a mapping for bank subtransactions."""
        subtransaction_db = BankSubtransactionHandler()
        subtransactions = subtransaction_db.get_entries((transaction_id,))
        fields = ('subtotal', 'note')
        return [{field: subtransaction[field] for field in fields}
                for subtransaction in subtransactions]


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


class BankAccountForm(MonopylyForm):
    """Form to input/edit bank accounts."""

    class BankSubform(AcquisitionSubform):
        """Form to input/edit bank identification."""
        _db_handler_type = BankHandler
        bank_id = BankSelectField()
        bank_name = TextField('Bank Name')

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
        type_name = TextField('Account Type Name')

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
    last_four_digits = TextField(
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

