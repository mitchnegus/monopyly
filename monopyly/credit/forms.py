"""
Generate forms for the user to fill out.
"""
from flask_wtf import FlaskForm
from werkzeug.exceptions import abort
from wtforms.fields import (
    FormField, DecimalField, IntegerField, TextField, BooleanField,
    SelectField, SubmitField, HiddenField
)
from wtforms.validators import Optional, DataRequired, Length

from ..utils import parse_date
from ..form_utils import NumeralsOnly, SelectionNotBlank
from .cards import CardHandler
from .statements import StatementHandler, determine_due_date
from .transactions import determine_statement_date


class TransactionForm(FlaskForm):
    """Form to input/edit transactions."""
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
    issue_date = TextField('Statement Date', filters=[parse_date])
    submit = SubmitField('Save Transaction')

    @property
    def database_data(self):
        """Produce a dictionary corresponding to a database transaction."""
        statement = self.get_transaction_statement()
        database_data = {'statement_id': statement['id']}
        for field in ('transaction_date', 'vendor', 'amount', 'notes'):
            database_data[field] = self[field].data
        return database_data

    def get_transaction_card(self):
        """Get the credit card associated with the transaction."""
        ch = CardHandler()
        card = ch.find_card(self.bank.data, self.last_four_digits.data)
        return card

    def get_transaction_statement(self):
        """Get the credit card statement associated with the transaction."""
        # Get the card for the transaction
        card = self.get_transaction_card()
        if not card:
            abort(404, 'A card matching the criteria was not found.')
        # Determine the date the statement was issued
        if self.issue_date.data:
            issue_date = self.issue_date.data
        else:
            issue_date = determine_statement_date(card['statement_issue_day'],
                                                  self.transaction_date.data)
        # Get the statement corresponding to the card and issue date
        sh = StatementHandler()
        statement = sh.find_statement(card['id'], issue_date)
        # Create the statement if it does not exist
        if not statement:
            statement_data = {
                'card_id': card['id'],
                'issue_date': issue_date,
                'due_date': determine_due_date(card['statement_due_day'],
                                               issue_date),
                'paid': 0,
                'payment_date': ''
            }
            statement = sh.new_entry(statement_data)
        return statement


class CardForm(FlaskForm):
    """Form to input/edit credit cards."""
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
