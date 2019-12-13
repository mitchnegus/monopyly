"""
Generate a form for the user to fill out with new transactions.
"""
from flask_wtf import FlaskForm
from wtforms.fields import (
    DateField, DecimalField, IntegerField, TextField, SubmitField
)
from wtforms.validators import DataRequired

class TransactionForm(FlaskForm):
    bank = TextField('Bank')
    last_four_digits = IntegerField('Last Four Digits', [DataRequired()])
    transaction_date = TextField('Transaction Date', [DataRequired()])
    vendor = TextField('Vendor', [DataRequired()])
    price = DecimalField('Price', [DataRequired()], places=2)
    notes = TextField('Notes', [DataRequired()])
    issue_date = TextField('Statement Date')
    submit = SubmitField('Save Transaction')


def error_unless_all_fields_provided(form, fields):
    """Check that all fields have been given on a submitted form."""
    if not all(form[field] for field in fields):
        error = 'All fields are required.'
    else:
        error = None
    return error
