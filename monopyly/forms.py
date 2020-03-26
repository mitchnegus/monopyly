"""
Generate forms for the user to fill out.
"""
from flask_wtf import FlaskForm
from wtforms.fields import (
    DecimalField, IntegerField, TextField, BooleanField, SelectField,
    SubmitField, HiddenField
)
from wtforms.validators import ValidationError, Optional, DataRequired, Length

from .utils import parse_date


class NumeralsOnly:
    """
    Validates text contains only numerals.

    Parameters
    ––––––––––
    message : str
        Error message to raise in case of a validation error.
    """

    def __init__(self, message=None):
        if not message:
            message = 'Field can only contain numerals.'
        self.message = message

    def __call__(self, form, field):
        try:
            int(field.data)
        except ValueError:
            raise ValidationError(self.message)


class SelectionNotBlank:
    """
    Validates that a selection is not a blank submission.

    Parameters
    ––––––––––
    blank : int
        The integer representing a blank selection.
    message : str
        Error message to raise in case of a validation error.
    """

    def __init__(self, blank=-1, message=None):
        self.blank = blank
        if not message:
            message = 'A selection must be made.'
        self.message = message

    def __call__(self, form, field):
        if field.data == self.blank:
            raise ValidationError(self.message)


class TransactionForm(FlaskForm):
    bank = TextField('Bank')
    last_four_digits = TextField(
        'Last Four Digits',
        validators=[DataRequired(), Length(4), NumeralsOnly()]
    )
    transaction_date = TextField(
        'Transaction Date',
        validators=[DataRequired()],
        filters=[parse_date]
    )
    vendor = TextField('Vendor', [DataRequired()])
    amount = DecimalField(
        'Amount',
        validators=[DataRequired()],
        filters=[lambda x: float(round(x, 2)) if x else None],
        places=2
    )
    notes = TextField('Notes', [DataRequired()])
    issue_date = TextField(
        'Statement Date',
        filters=[parse_date])
    submit = SubmitField('Save Transaction')


class CardForm(FlaskForm):
    account_id = SelectField('Account', [SelectionNotBlank()], coerce=int)
    bank = TextField('Bank')
    last_four_digits = TextField(
        'Last Four Digits',
        validators=[DataRequired(), Length(4), NumeralsOnly()]
    )
    statement_issue_day = IntegerField('Statement Issue Day', [Optional()])
    statement_due_day = IntegerField('Statement Due Day', [Optional()])
    active = BooleanField('Active', default='checked')
    submit = SubmitField('Save Card')
