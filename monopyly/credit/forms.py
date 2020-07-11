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
from .accounts import AccountHandler
from .cards import CardHandler
from .statements import StatementHandler


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
    tags = TextField('Tags')
    submit = SubmitField('Save Transaction')

    @property
    def transaction_data(self):
        """Produce a dictionary corresponding to a database transaction."""
        statement = self.get_transaction_statement()
        transaction_data = {'statement_id': statement['id']}
        for field in ('transaction_date', 'vendor', 'amount', 'notes'):
            transaction_data[field] = self[field].data
        return transaction_data

    @property
    def tag_data(self):
        """Produce a list of tags corresponding to the transaction."""
        # RETURN AN EMPTY LIST NOT A LIST WITH EMPTY STRING
        raw_tag_data = self['tags'].data.split(',')
        tag_data = [tag.strip() for tag in raw_tag_data if tag]
        return tag_data

    def get_transaction_card(self):
        """Get the credit card associated with the transaction."""
        card_db = CardHandler()
        card = card_db.find_card(self.bank.data, self.last_four_digits.data)
        return card

    def get_transaction_statement(self):
        """Get the credit card statement associated with the transaction."""
        # Get the card for the transaction
        card = self.get_transaction_card()
        if not card:
            abort(404, 'A card matching the criteria was not found.')
        statement_db = StatementHandler()
        # Get the statement corresponding to the card and issue date
        issue_date = self.issue_date.data
        if issue_date:
            statement = statement_db.find_statement(card, issue_date)
            # Create the statement if it doesn't exist
            if not statement:
                statement = statement_db.add_statement(card, issue_date)
        else:
            # No issue date was given, so the statement must be inferred
            statement = statement_db.infer_statement(card,
                                                     self.transaction_date.data,
                                                     creation=True)
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

    @property
    def card_data(self):
        """Produce a dictionary corresponding to a database card."""
        account = self.get_card_account()
        card_data = {'account_id': account['id']}
        for field in ('last_four_digits', 'active'):
            card_data[field] = self[field].data
        return card_data

    def get_card_account(self, account_creation=True):
        """Get the account associated with the credit card."""
        account_db = AccountHandler()
        # Check if the account exists and potentially create it if not
        if self.account_id.data == 0:
            if account_creation:
                account_data = {
                    'user_id': account_db.user_id,
                    'bank': self.bank.data,
                    'statement_issue_day': self.statement_issue_day.data,
                    'statement_due_day': self.statement_due_day.data
                }
                account = account_db.add_entry(account_data)
            else:
                account = None
        else:
            account = account_db.get_entry(self.account_id.data)
        return account
