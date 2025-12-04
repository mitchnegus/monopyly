"""
Generate banking forms for the user to complete.
"""

from wtforms.fields import BooleanField, FieldList, FormField, SubmitField
from wtforms.validators import DataRequired, Optional

from ..common.forms import AcquisitionSubform, EntryForm, EntrySubform, TransactionForm
from ..common.forms.fields import (
    CustomChoiceSelectField,
    LastFourDigitsField,
    StringField,
)
from ..common.forms.utils import Autocompleter
from ..database.models import (
    Bank,
    BankAccountTypeView,
    BankAccountView,
    BankSubtransaction,
    BankTransaction,
    BankTransactionView,
    TransactionTag,
)
from .accounts import BankAccountHandler, BankAccountTypeHandler
from .banks import BankHandler


class BankSelectField(CustomChoiceSelectField):
    """Bank field that uses the database to prepare field choices."""

    _db_handler = BankHandler

    def __init__(self, **kwargs):
        super().__init__(label="Bank", **kwargs)

    @staticmethod
    def _format_choice(bank):
        display_name = bank.bank_name
        return display_name


class BankAccountTypeSelectField(CustomChoiceSelectField):
    """Account type field that uses the database to prepare field choices."""

    _db_handler = BankAccountTypeHandler

    def __init__(self, **kwargs):
        super().__init__(label="Account Type", **kwargs)

    @staticmethod
    def _format_choice(account_type):
        display_name = account_type.type_name
        # Display name abbreviations in parentheses
        if account_type.type_common_name != display_name:
            display_name += f" ({account_type.type_common_name})"
        return display_name


class BankSubform(AcquisitionSubform):
    """Form to input/edit bank identification."""

    _db_handler = BankHandler
    # Fields pertaining to the bank
    bank_id = BankSelectField()
    bank_name = StringField("Bank Name", [Optional()])

    def get_bank(self):
        """Get the bank described by the form data."""
        return self._produce_entry_from_field("bank_id")

    def _prepare_mapping(self):
        bank_name = self.bank_name.data
        if not bank_name:
            raise ValueError("A bank name must be provided.")
        # Mapping must match format for `banks` database table
        bank_data = {
            "user_id": self._db_handler.user_id,
            "bank_name": self.bank_name.data,
        }
        return bank_data

    def gather_entry_data(self, entry):
        """Gather data for the form from the given database entry."""
        if isinstance(entry, Bank):
            data = {
                "bank_id": entry.id,
                "bank_name": entry.bank_name,
            }
        else:
            self._raise_gather_fail_error((Bank,), entry)
        return data


class BankAccountForm(EntryForm):
    """Form to input/edit bank accounts."""

    class AccountTypeSubform(AcquisitionSubform):
        """Form to input/edit bank account types."""

        _db_handler = BankAccountTypeHandler
        # Fields pertaining to the account type
        account_type_id = BankAccountTypeSelectField()
        type_name = StringField("Account Type Name")

        def get_account_type(self):
            """Get the bank account type described by the form data."""
            return self._produce_entry_from_field("account_type_id")

        def _prepare_mapping(self):
            # Mapping must match format for `bank_account_types` database table
            account_type_data = {
                "user_id": self._db_handler.user_id,
                "type_name": self.type_name.data,
                "type_abbreviation": None,
            }
            return account_type_data

        def gather_entry_data(self, entry):
            """Gather data for the form from the given database entry."""
            raise NotImplementedError

    # Fields to identify the bank/account type information for the account
    bank_info = FormField(BankSubform)
    account_type_info = FormField(AccountTypeSubform)
    # Fields pertaining to the account
    last_four_digits = LastFourDigitsField(
        "Last Four Digits", validators=[DataRequired()]
    )
    active = BooleanField("Active", default="checked")
    submit = SubmitField("Save Account")

    @property
    def account_data(self):
        """Produce a dictionary corresponding to a database bank account."""
        bank = self.bank_info.get_bank()
        account_type = self.account_type_info.get_account_type()
        account_data = {
            "bank_id": bank.id,
            "account_type_id": account_type.id,
            "last_four_digits": self["last_four_digits"].data,
            "active": self["active"].data,
        }
        return account_data

    def gather_entry_data(self, entry):
        """Gather data for the form from the given database entry."""
        if isinstance(entry, Bank):
            data = {}
            bank_info = entry
        else:
            self._raise_gather_fail_error((Bank,), entry)
        data["bank_info"] = self.bank_info.gather_entry_data(bank_info)
        return data


class BankTransactionForm(TransactionForm):
    """Form to input/edit bank transactions."""

    class AccountSubform(EntrySubform):
        """Form to input/edit bank account identification."""

        _db_handler = BankAccountHandler
        # Fields pertaining to the account
        bank_name = StringField("Bank")
        last_four_digits = LastFourDigitsField(
            "Last Four Digits", validators=[DataRequired()]
        )
        type_name = StringField("Account Type", validators=[DataRequired()])

        def get_account(self):
            """Get the bank account described by the form data."""
            return self._db_handler.find_account(
                bank_name=self.bank_name.data,
                account_type_name=self.type_name.data,
                last_four_digits=self.last_four_digits.data,
            )

        def gather_entry_data(self, entry):
            """Gather data for the form from the given database entry."""
            if isinstance(entry, BankAccountView):
                data = {
                    "bank_name": entry.bank.bank_name,
                    "last_four_digits": entry.last_four_digits,
                    "type_name": entry.account_type_view.type_name,
                }
            elif isinstance(entry, Bank):
                data = {"bank_name": entry.bank_name}
            else:
                self._raise_gather_fail_error((BankAccountView, Bank), entry)
            return data

    class SubtransactionSubform(TransactionForm.SubtransactionSubform):
        """Form to input/edit bank subtransactions."""

        subtransaction_model = BankSubtransaction

    # Fields to identify the bank account information for the transaction
    account_info = FormField(AccountSubform)
    # Fields pertaining to the bank transaction
    merchant = StringField("Merchant")
    # Subtransaction fields (must be at least 1 subtransaction)
    subtransactions = FieldList(
        FormField(SubtransactionSubform, render_kw={"class": "subtransaction-form"}),
        min_entries=1,
    )
    # Fields to identify a second bank involved in a funds transfer
    transfer_accounts_info = FieldList(
        FormField(AccountSubform),
        min_entries=0,
        max_entries=1,
    )
    # Define an autocompleter for the form
    _autocompleter = Autocompleter(
        {
            "bank_name": Bank,
            "type_name": BankAccountTypeView,
            "last_four_digits": BankAccountView,
            "merchant": BankTransaction,
            "note": BankSubtransaction,
            "tags": TransactionTag,
        }
    )

    @property
    def transfer_account_info(self):
        if not self.transfer_accounts_info:
            return None
        # Simulate a normal `FormField` (not a `FieldList`)
        return self.transfer_accounts_info[0]

    @property
    def transaction_data(self):
        """
        Produce a dictionary corresponding to a database transaction.

        Creates a dictionary of transaction fields and values, in a
        format that can be added directly to the database as a new
        bank transaction. The dictionary also includes subtransactions.
        """
        account = self.get_transaction_account()
        return self._prepare_transaction_data(account)

    @property
    def transfer_data(self):
        """
        Produce a dictionary corresponding to the transfer transaction.

        Creates a dictionary of transaction fields and values, in a
        format that can be added directly to the database as a new
        bank transaction for the transfer. The transfer data is
        identical to the transaction data except that the account is
        different and the subtotals of subtransactions have the opposite
        (negated) amount.
        """
        if not self.transfer_account_info:
            return None
        account = self.get_transfer_account()
        transfer_data = self._prepare_transaction_data(account)
        # Use the bank initiating the transaction as the merchant
        transfer_data["merchant"] = self.get_transaction_account().bank.bank_name
        # Negate transfer subtotals as the opposite of the original transaction
        for subtransaction_data in transfer_data["subtransactions"]:
            subtransaction_data["subtotal"] = -subtransaction_data["subtotal"]
        return transfer_data

    def get_transaction_account(self):
        """Get the bank account associated with the transaction."""
        return self.account_info.get_account()

    def get_transfer_account(self):
        """Get the bank account linked in a transfer."""
        return self.transfer_account_info.get_account()

    def _prepare_transaction_data(self, account):
        data = super()._prepare_transaction_data()
        data["account_id"] = account.id
        return data

    def gather_entry_data(self, entry):
        """Gather data for the form from the given database entry."""
        if isinstance(entry, BankTransactionView):
            data = self._gather_transaction_data(entry)
            account_info = entry.account_view
            # Do not prepopulate any transfer information
        elif isinstance(entry, (BankAccountView, Bank)):
            data = {}
            account_info = entry
        else:
            self._raise_gather_fail_error((BankTransactionView, BankAccountView), entry)
        # Prepare data for the account/subtransaction subforms
        data["account_info"] = self.account_info.gather_entry_data(account_info)
        return data
