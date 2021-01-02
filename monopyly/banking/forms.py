"""
Generate banking forms for the user to fill out.
"""
from flask_wtf import FlaskForm
from wtforms.fields import (
    TextField, BooleanField, SelectField, SubmitField
)
from wtforms.validators import Optional, DataRequired, Length

from ..form_utils import NumeralsOnly, SelectionNotBlank


class BankAccountForm(FlaskForm):
    """Form to input/edit bank accounts."""
    bank_id = SelectField('Bank', [SelectionNotBlank()], coerce=int)
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
        account_data = {}
        for field in ('bank_id', 'last_four_digits', 'account_type', 'active'):
            account_data[field] = self[field].data
        return account_data
