"""
Generate banking forms for the user to fill out.
"""
from flask_wtf import FlaskForm
#from werkzeug.exceptions import abort
from wtforms.fields import (
    DecimalField, TextField, BooleanField, SelectField, SubmitField
)
from wtforms.validators import Optional, DataRequired, Length

from ..utils import parse_date
from ..form_utils import NumeralsOnly, SelectionNotBlank
from .banks import BankHandler
from .accounts import BankAccountTypeHandler, BankAccountHandler


class BankTransactionForm(FlaskForm):
    """Form to input/edit transactions."""
    # Fields to identify the bank account information for the transaction
    bank_name = TextField('Bank')
    last_four_digits = TextField(
        'Last Four Digits',
        validators=[DataRequired(), Length(4), NumeralsOnly()]
    )
    type_name = TextField('Account Type', validators=[DataRequired()])
    # Fields pertaining to the transaction
    transaction_date = TextField(
        'Transaction Date',
        validators=[DataRequired()],
        filters=[parse_date]
    )
    total = DecimalField(
        'Amount',
        validators=[DataRequired()],
        filters=[lambda x: float(round(x, 2)) if x else None],
        places=2
    )
    note = TextField('Note', [DataRequired()])
    submit = SubmitField('Save Transaction')

    @property
    def transaction_data(self):
        """
        Produce a dictionary corresponding to a database transaction.

        Creates a dictionary of transaction fields and values, in a
        format that can be added directly to the database as a new
        bank transaction.
        """
        account = self.get_transaction_account()
        transaction_data = {'account_id': account['id']}
        # Loop over the transaction-specific fields
        for field in ('transaction_date', 'total', 'note'):
            transaction_data[field] = self[field].data
        return transaction_data

    def get_transaction_account(self):
        """Get the bank account associated with the transaction."""
        account_db = BankAccountHandler()
        account = account_db.find_account(self.bank_name.data,
                                          self.last_four_digits.data,
                                          self.type_name.data)
        return account


class BankAccountForm(FlaskForm):
    """Form to input/edit bank accounts."""
    bank_id = SelectField('Bank', [SelectionNotBlank()], coerce=int)
    bank_name = TextField('Bank Name')
    account_type_id = SelectField('Account Type', [SelectionNotBlank()],
                                  coerce=int)
    account_type_name = TextField('Account Type Name')
    last_four_digits = TextField(
        'Last Four Digits',
        validators=[DataRequired(), Length(4), NumeralsOnly()]
    )
    active = BooleanField('Active', default='checked')
    submit = SubmitField('Save Account')

    @property
    def account_data(self):
        """Produce a dictionary corresponding to a database bank account."""
        bank = self.get_bank()
        account_type = self.get_account_type()
        account_data = {'bank_id': bank['id'],
                        'account_type_id': account_type['id']}
        for field in ('last_four_digits', 'active'):
            account_data[field] = self[field].data
        return account_data

    def get_bank(self, bank_creation=True):
        bank_db = BankHandler()
        # Check if the bank exists and potentially create it if not
        if self.bank_id.data == 0:
            if bank_creation:
                # Add the bank to the database if it does not already exist
                bank_data = {
                    'user_id': bank_db.user_id,
                    'bank_name': self.bank_name.data,
                }
                bank = bank_db.add_entry(bank_data)
            else:
                bank = None
        else:
            bank = bank_db.get_entry(self.bank_id.data)
        return bank

    def get_account_type(self, account_type_creation=True):
        account_type_db = BankAccountTypeHandler()
        # Check if the account type exists and potentially create it if not
        if self.account_type_id.data == 0:
            if account_type_creation:
                # Add the type to the database if it does not already exist
                account_type_data = {
                    'user_id': account_type_db.user_id,
                    'type_name': self.account_type_name.data,
                    'type_abbreviation': None,
                }
                account_type = account_type_db.add_entry(account_type_data)
            else:
                account_type = None
        else:
            account_type = account_type_db.get_entry(self.account_type_id.data)
        return account_type

    def prepare_choices(self):
        """Prepare choices to fill select fields."""
        self._prepare_bank_choices()
        self._prepare_account_type_choices()

    def _prepare_bank_choices(self):
        bank_db = BankHandler()
        # Collect all available user banks
        user_banks = bank_db.get_entries()
        # Set bank choices
        bank_choices = [(-1, '-')]
        for bank in user_banks:
            bank_choices.append((bank['id'], bank['bank_name']))
        bank_choices.append((0, 'New bank'))
        self.bank_id.choices = bank_choices

    def _prepare_account_type_choices(self):
        account_type_db = BankAccountTypeHandler()
        # Collect all available user account types
        user_account_types = account_type_db.get_entries()
        # Set account type choices
        account_type_choices = [(-1, '-')]
        for account_type in user_account_types:
            display_name = account_type['type_full_name']
            # Display name abbreviations in parentheses
            if account_type['type_name'] != display_name:
                display_name += f" ({account_type['type_name']})"
            account_type_choices.append((account_type['id'], display_name))
        account_type_choices.append((0, 'New account type'))
        self.account_type_id.choices = account_type_choices

