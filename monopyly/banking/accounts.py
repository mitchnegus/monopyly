"""
Tools for interacting with bank accounts in the database.
"""

import sqlalchemy.sql.functions as sql_func
from dry_foundation.database.handler import DatabaseViewHandler
from flask import abort

from ..common.forms.utils import execute_on_form_validation
from ..database.models import (
    Bank,
    BankAccount,
    BankAccountType,
    BankAccountTypeView,
    BankAccountView,
)


class BankAccountTypeHandler(
    DatabaseViewHandler, model=BankAccountType, model_view=BankAccountTypeView
):
    """
    A database handler for managing bank account types.

    Attributes
    ----------
    user_id : int
        The ID of the user who is the subject of database access.
    model : type
        The type of database model that the handler is primarily
        designed to manage.
    table : str
        The name of the database table that this handler manages.
    """

    @classmethod
    @DatabaseViewHandler.view_query
    def get_account_types(cls):
        """
        Get bank account types from the database.

        Returns
        -------
        account_types : sqlalchemy.engine.ScalarResult
            Returns bank account types matching the criteria.
        """
        return super().get_entries()

    @classmethod
    @DatabaseViewHandler.view_query
    def get_types_for_bank(cls, bank_id):
        """Return a list of the bank account type IDs that exist for a bank."""
        # This may duplicate `get_account_types` method
        query = cls.model.select_for_user()
        # Join the view with the original table
        query = query.join(BankAccountType)
        # Join (distinctly) with bank accounts & banks to determine bank types
        query = query.join(BankAccount).join(Bank).distinct()
        # Get only types for the specified bank
        query = query.where(Bank.id == bank_id)
        account_types = cls._db.session.scalars(query)
        return account_types

    @classmethod
    @DatabaseViewHandler.view_query
    def find_account_type(cls, type_name=None, type_abbreviation=None):
        """
        Find an account type using uniquely identifying characteristics.

        Queries the database to find a bank account type based on the
        provided criteria. Bank account types in the database can always
        be identified uniquely given the user's ID and either the name
        of an account type or the abbreviation of that name.

        Parameters
        ----------
        type_name : str, optional
            The bank account type to find.
        type_abbreviation : str, optional
            The bank account type abbreviation to find.

        Returns
        -------
        account_type : database.models.BankAccountType
            A model containing bank account type information from the
            database matching the given criteria. If no matching account
            type is found, returns `None`.
        """
        criteria = cls._initialize_criteria_list()
        criteria.add_match_filter(cls.model, "type_name", type_name)
        criteria.add_match_filter(cls.model, "type_abbreviation", type_abbreviation)
        account_type = super().find_entry(criteria=criteria)
        return account_type

    @classmethod
    def add_entry(cls, **mapping):
        # To Do: Should prevent a user from duplicating the common entries
        return super().add_entry(**mapping)

    @classmethod
    def delete_entry(cls, entry_id):
        """
        Delete a bank account type from the database.

        Given an account type ID, delete the bank account type from the
        database. Deleting an account type will also delete all accounts
        (and transactions) associated with that account type.

        Parameters
        ----------
        entry_id : int
            The ID of the account type to be deleted.
        """
        super().delete_entry(entry_id)

    @classmethod
    def _retrieve_authorized_manipulable_entry(cls, entry_id):
        account_type = super()._retrieve_authorized_manipulable_entry(entry_id)
        if account_type.user_id != cls.user_id:
            abort_msg = (
                "The current user is not authorized to manipulate "
                "this account type entry."
            )
            abort(403, abort_msg)
        return account_type


class BankAccountHandler(
    DatabaseViewHandler, model=BankAccount, model_view=BankAccountView
):
    """
    A database handler for managing bank accounts.

    Attributes
    ----------
    user_id : int
        The ID of the user who is the subject of database access.
    model : type
        The type of database model that the handler is primarily
        designed to manage.
    table : str
        The name of the database table that this handler manages.
    """

    @classmethod
    @DatabaseViewHandler.view_query
    def get_accounts(cls, bank_ids=None, account_type_ids=None):
        """
        Get bank accounts from the database.

        Query the database to select bank account fields. Accounts can
        be filtered by the issuing bank or the type of account.

        Parameters
        ----------
        bank_ids : tuple of int, optional
            A sequence of bank IDs for which accounts will be selected
            (if `None`, all banks will be selected).
        account_type_ids : tuple of int, optional
            A sequence of bank account type IDs for which account types
            will be selected (if `None`, all account types will be
            selected).

        Returns
        -------
        accounts : sqlalchemy.engine.ScalarResult
            Returns bank accounts matching the criteria.
        """
        criteria = cls._initialize_criteria_list()
        criteria.add_match_filter(cls.model, "bank_id", bank_ids)
        criteria.add_match_filter(cls.model, "account_type_id", account_type_ids)
        accounts = super().get_entries(criteria=criteria)
        return accounts

    @classmethod
    @DatabaseViewHandler.view_query
    def get_bank_balance(cls, bank_id):
        """Get the balance of all accounts at one bank."""
        query = cls.model.select_for_user(sql_func.sum(cls.model.balance))
        query = query.where(Bank.id == bank_id)
        balance = cls._db.session.execute(query).scalar()
        if balance is None:
            abort_msg = (
                "No balance was found for the given combination of user and account."
            )
            abort(404, abort_msg)
        return balance

    @classmethod
    @DatabaseViewHandler.view_query
    def find_account(
        cls, bank_name=None, account_type_name=None, last_four_digits=None
    ):
        """
        Find a bank account using uniquely identifying characteristics.

        Queries the database to find a bank account based on the
        provided criteria. Bank accounts in the database can almost
        always be uniquely identified given the user's ID, the last
        four digits of the account number, and the account type.
        In rare cases where a user has two accounts of the same type
        both with the same last four digits, the bank name can be used to
        to help determine the account. (It is expected to be
        exceptionally rare that a user has two accounts of the same
        type, both with the same last four digits, and both from the
        same bank.) If multiple cards do match the criteria, only the
        first one found is returned.

        Parameters
        ----------
        bank_name : str, optional
            The bank of the account to find.
        account_type_name : str, optional
            The name of the account type to find.
        last_four_digits : int, optional
            The last four digits of the bank account to find.

        Returns
        -------
        account : database.models.BankAccountView
            A bank account entry matching the given criteria. If no
            matching account is found, returns `None`.
        """
        criteria = cls._initialize_criteria_list()
        criteria.add_match_filter(Bank, "bank_name", bank_name)
        criteria.add_match_filter(BankAccountTypeView, "type_name", account_type_name)
        criteria.add_match_filter(cls.model, "last_four_digits", last_four_digits)
        account = super().find_entry(criteria=criteria)
        return account

    @classmethod
    def _filter_entries(cls, query, criteria, offset, limit):
        # Add a join to enable filtering by bank account type
        query = query.join(BankAccountTypeView)
        return super()._filter_entries(query, criteria, offset, limit)

    @classmethod
    def delete_entry(cls, entry_id):
        """
        Delete a bank account from the database.

        Given an account ID, delete the bank account from the database.
        Deleting an account will also delete all transactions associated
        with that account.

        Parameters
        ----------
        entry_id : int
            The ID of the account to be deleted.
        """
        super().delete_entry(entry_id)


@execute_on_form_validation
def save_account(form, account_id=None):
    """
    Save a bank account.

    Saves a bank account in the database. The form information is added
    as a new entry, and the ability to update the account is not yet
    supported.

    Parameters
    ----------
    form : BankAccountForm
        The form being used to provide the data being saved.

    Returns
    -------
    account : database.models.BankAccountView
        The saved account.
    """
    account_data = form.account_data
    if account_id:
        raise NotImplementedError(
            "The ability to update the account is not yet supported."
        )
    else:
        # Insert the new account into the database
        account = BankAccountHandler.add_entry(**account_data)
    return account
