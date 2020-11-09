"""
Generate forms for the user to fill out.
"""
from flask import url_for
from flask_wtf import FlaskForm
from werkzeug.exceptions import abort
from wtforms.fields import (
    FormField, DecimalField, IntegerField, TextField, BooleanField,
    SelectField, SubmitField, HiddenField, FieldList
)
from wtforms.validators import Optional, DataRequired, Length

from ..utils import parse_date
from ..form_utils import NumeralsOnly, SelectionNotBlank
from ..banking import BankHandler
from . import credit
from .accounts import AccountHandler
from .cards import CardHandler
from .statements import StatementHandler


class TransactionForm(FlaskForm):
    """Form to input/edit transactions."""

    class SubtransactionForm(FlaskForm):
        """Form to input/edit subtransactions."""
        def __init__(self, *args, **kwargs):
            # Deactivates CSRF as a subform
            super().__init__(meta={'csrf': False}, *args, **kwargs)

        subtotal = DecimalField(
            'Amount',
            validators=[DataRequired()],
            filters=[lambda x: float(round(x, 2)) if x else None],
            places=2
        )
        note = TextField('Note', [DataRequired()])
        tags = TextField('Tags')

    # Fields to identify the card/bank information for the transaction
    bank = TextField('Bank')
    last_four_digits = TextField(
        'Last Four Digits',
        validators=[DataRequired(), Length(4), NumeralsOnly()]
    )
    issue_date = TextField('Statement Date', filters=[parse_date])
    # Fields pertaining to the transaction
    transaction_date = TextField(
        'Transaction Date',
        validators=[DataRequired()],
        filters=[parse_date]
    )
    vendor = TextField('Vendor', [DataRequired()])
    # Subtransaction fields (must be at least 1 subtransaction)
    subtransactions = FieldList(FormField(SubtransactionForm), min_entries=1)
    submit = SubmitField('Save Transaction')

    @property
    def transaction_data(self):
        """
        Produce a dictionary corresponding to a database transaction.

        Creates a dictionary of transaction fields and values, in a
        format that can be added directly to the database as a new
        transaction. The dictionary also includes subtransactions (along
        with tags associated with each subtransaction).
        """
        statement = self.get_transaction_statement()
        transaction_data = {'statement_id': statement['id']}
        # Loop over the transaction-specific fields
        for field in ('transaction_date', 'vendor',):
            transaction_data[field] = self[field].data
        # Aggregate subtransaction information for the transaction
        transaction_data['subtransactions'] = []
        for form in self['subtransactions']:
            subtransaction_data = {}
            # Loop over the subtransaction-specific fields
            for field in ('subtotal', 'note'):
                subtransaction_data[field] = form[field].data
            # RETURN AN EMPTY LIST NOT A LIST WITH EMPTY STRING
            raw_tag_data = form['tags'].data.split(',')
            tag_data = [tag.strip() for tag in raw_tag_data if tag]
            subtransaction_data['tags'] = tag_data
            transaction_data['subtransactions'].append(subtransaction_data)
        return transaction_data

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
        bank_db, account_db = BankHandler(), AccountHandler()
        # Check if the account exists and potentially create it if not
        if self.account_id.data == 0:
            if account_creation:
                # Add the bank to the database if it does not already exist
                bank_name = self.bank.data
                matching_banks = bank_db.get_entries(banks=(bank_name,))
                if not matching_banks:
                    bank_data = {
                        'user_id': bank_db.user_id,
                        'bank': bank_name,
                    }
                    bank = bank_db.add_entry(bank_data)
                else:
                    bank = matching_banks[0]
                # Add the account to the database
                account_data = {
                    'bank_id': bank['id'],
                    'statement_issue_day': self.statement_issue_day.data,
                    'statement_due_day': self.statement_due_day.data,
                }
                account = account_db.add_entry(account_data)
            else:
                account = None
        else:
            account = account_db.get_entry(self.account_id.data)
        return account
