"""
Generate a form for the user to fill out with new transactions.
"""
from flask_wtf import FlaskForm
from wtforms.fields import (
    DateField, DecimalField, IntegerField, TextField, BooleanField, SubmitField
)
from wtforms.validators import DataRequired

from .utils import parse_date


class TransactionForm(FlaskForm):
    bank = TextField('Bank')
    last_four_digits = IntegerField('Last Four Digits', [DataRequired()])
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
    last_four_digits = IntegerField('Last Four Digits', [DataRequired()])
    statement_issue_day = IntegerField('Statement Issue Day', [DataRequired()])
    statement_due_day = IntegerField('Statement Due Day', [DataRequired()])
    active = BooleanField('Active Card', default='checked')
    submit = SubmitField('Save Card')
