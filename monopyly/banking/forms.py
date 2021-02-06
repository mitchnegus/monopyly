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
from .accounts import BankAccountHandler


class BankTransactionForm(FlaskForm):
    """Form to input/edit transactions."""
    # Fields to identify the bank account information for the transaction
    bank_name = TextField('Bank')
    last_four_digits = TextField(
        'Last Four Digits',
        validators=[DataRequired(), Length(4), NumeralsOnly()]
    )
    account_type = TextField('Account Type', validators=[DataRequired()])
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
                                          self.account_type.data)
        return account


class BankAccountForm(FlaskForm):
    """Form to input/edit bank accounts."""
    bank_id = SelectField('Bank', [SelectionNotBlank()], coerce=int)
    bank_name = TextField('Bank Name')
    last_four_digits = TextField(
        'Last Four Digits',
        validators=[DataRequired(), Length(4), NumeralsOnly()]
    )
    account_type = TextField('Account Type', [DataRequired()])
    #type_ = SelectField('Account Type', [SelectionNotBlank()], coerce=int)
    active = BooleanField('Active', default='checked')
    submit = SubmitField('Save Account')

    @property
    def account_data(self):
        """Produce a dictionary corresponding to a database bank account."""
        bank = self.get_bank()
        account_data = {'bank_id': bank['id']}
        for field in ('last_four_digits', 'account_type', 'active'):
            account_data[field] = self[field].data
        return account_data

    def get_bank(self, bank_creation=True):
        bank_db = BankHandler()
        # Check if the bank exists and potentially create it if not
        if self.bank_id.data == 0:
            if bank_creation:
                # Add the bank to the database if it does not already exist
                bank_name = self.bank_name.data
                bank_data = {
                    'user_id': bank_db.user_id,
                    'bank_name': bank_name,
                }
                bank = bank_db.add_entry(bank_data)
            else:
                bank = None
        else:
            bank = bank_db.get_entry(self.bank_id.data)
        return bank
