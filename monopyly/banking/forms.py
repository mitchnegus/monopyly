"""
Generate banking forms for the user to fill out.
"""
from flask_wtf import FlaskForm
from wtforms.fields import (
    TextField, BooleanField, SelectField, SubmitField
)
from wtforms.validators import Optional, DataRequired, Length

from ..form_utils import NumeralsOnly, SelectionNotBlank
from .banks import BankHandler


class BankAccountForm(FlaskForm):
    """Form to input/edit bank accounts."""
    bank_id = SelectField('Bank', [SelectionNotBlank()], coerce=int)
    bank_name = TextField('Bank Name')
    last_four_digits = TextField(
        'Last Four Digits',
        validators=[DataRequired(), Length(4), NumeralsOnly()]
    )
    account_type = TextField('Account Type', [DataRequired()])
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
