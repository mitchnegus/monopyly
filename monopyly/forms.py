"""
Generate forms for the user to fill out.
"""
from flask_wtf import FlaskForm
from wtforms.fields import (
    DecimalField, IntegerField, TextField, BooleanField, SubmitField
)
from wtforms.validators import ValidationError, DataRequired, Length

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


class TransactionForm(FlaskForm):
    bank = TextField('Bank')
    last_four_digits = TextField('Last Four Digits',
                                 validators=[DataRequired(), Length(4),
                                             NumeralsOnly()])
    transaction_date = TextField('Transaction Date',
                                 validators=[DataRequired()],
                                 filters=[parse_date])
    vendor = TextField('Vendor', [DataRequired()])
    price = DecimalField('Price',
                         validators=[DataRequired()],
                         filters=[lambda x: float(round(x, 2)) if x else None],
                         places=2)
    notes = TextField('Notes', [DataRequired()])
    issue_date = TextField('Statement Date',
                           filters=[parse_date])
    submit = SubmitField('Save Transaction')


class CardForm(FlaskForm):
    bank = TextField('Bank')
    last_four_digits = TextField('Last Four Digits',
                                 validators=[DataRequired(), Length(4),
                                             NumeralsOnly()])
    statement_issue_day = IntegerField('Statement Issue Day', [DataRequired()])
    statement_due_day = IntegerField('Statement Due Day', [DataRequired()])
    active = BooleanField('Active Card', default='checked')
    submit = SubmitField('Save Card')
