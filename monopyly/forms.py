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
    statement_date = TextField('Statement Date')
    submit = SubmitField('Add Transaction')

class UpdateTransactionForm(TransactionForm):
    submit = SubmitField('Update Transaction')
