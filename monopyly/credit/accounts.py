"""
Tools for interacting with credit accounts in the database.
"""
from werkzeug.exceptions import abort

from ..utils import (
    DatabaseHandler, fill_place, fill_places, filter_item, filter_items,
    reserve_places
)
from .constants import ACCOUNT_FIELDS
from .tools import select_fields



class AccountHandler(DatabaseHandler):
    """
    A database handler for managing credit accounts.

    Parameters
    ––––––––––
    db : sqlite3.Connection
        A connection to the database for interfacing.
    user_id : int
        The ID of the user who is the subject of database access. If not
        given, the handler defaults to using the logged-in user.
    check_user : bool
        A flag indicating whether the handler should check that the
        provided user ID matches the logged-in user.

    Attributes
    ––––––––––
    table_name : str
        The name of the database table that this handler manages.
    db : sqlite3.Connection
        A connection to the database for interfacing.
    cursor : sqlite.Cursor
        A cursor for executing database interactions.
    user_id : int
        The ID of the user who is the subject of database access.
    """
    table_name = 'credit_accounts'

    def __init__(self, db=None, user_id=None, check_user=True):
        super().__init__(db=db, user_id=user_id, check_user=check_user)

    def get_accounts(self, fields=None, banks=None):
        """
        Get credit accounts from the database.

        Query the database to select credit account fields. Accounts can
        be filtered by the issuing bank. All fields for all accounts are
        shown by default.

        Parameters
        ––––––––––
        fields : tuple of str, optional
            A sequence of fields to select from the database (if `None`,
            all fields will be selected). Can be any field in the
            'credit_accounts' table.
        banks : tuple of str, optional
            A sequence of banks for which cards will be selected (if
            `None`, all banks will be selected).

        Returns
        –––––––
        accounts : list of sqlite3.Row
            A list of credit accounts matching the criteria.
        """
        bank_filter = filter_items(banks, 'bank', 'AND')
        query = (f"SELECT {select_fields(fields, 'a.id')} "
                  "  FROM credit_accounts AS a "
                  " WHERE user_id = ? "
                 f"       {bank_filter} ")
        placeholders = (self.user_id, *fill_places(banks))
        accounts = self.cursor.execute(query, placeholders).fetchall()
        return accounts

    def get_account(self, account_id, fields=None):
        """Get a credit account from the database given its account ID."""
        query = (f"SELECT {select_fields(fields, 'a.id')} "
                  "  FROM credit_accounts AS a "
                  " WHERE a.id = ? AND user_id = ?")
        placeholders = (account_id, self.user_id)
        account = self.cursor.execute(query, placeholders).fetchone()
        # Check that a account was found
        if account is None:
            abort_msg = f'Account ID {account_id} does not exist for the user.'
            abort(404, abort_msg)
        return account

    def save_account(self, form, account_id=None):
        """
        Save a new credit account in the database from a submitted form.

        Accept a user provided form and either insert the information
        into the database as a new credit account or update the account
        with matching ID. All fields are processed and sanitized using
        the database handler.

        Parameters
        ––––––––––
        form : AccountForm
            An object containing the submitted form information.
        account_id : int, optional
            If given, the ID of the card to be updated. If left as
            `None`, a new credit card is created.

        Returns
        –––––––
        account : sqlite3.Row
            The saved account.
        """
        mapping = self.process_account_form(form)
        if ACCOUNT_FIELDS != tuple(mapping.keys()):
            raise ValueError('The mapping does not match the database. Fields '
                            f'({", ".join(ACCOUNT_FIELDS)}) must be provided.')
        # Either create a new entry or update an existing entry
        if not account_id:
            self.new_entry(mapping)
            account_id = self.cursor.lastrowid
        else:
            self.update_entry(account_id, mapping)
        account = self.get_account(account_id)
        return account

    def process_account_form(self, form):
        """
        Process credit account information submitted on a form.

        Collect all credit account information submitted through the
        form. This aggregates all credit account data from the form,
        fills in defaults and makes inferrals when necessary, and then
        returns a dictionary mapping of the account information.

        Parameters
        ––––––––––
        form : CardForm
            An object containing the submitted form information.

        Returns
        –––––––
        mapping : dict
            A dictionary of account information collected from the user
            submission.
        """
        # Iterate through the transaction submission and create the dictionary
        mapping = {}
        for field in ACCOUNT_FIELDS:
            if field == 'user_id':
                mapping[field] = self.user_id
            else:
                mapping[field] = form[field].data
        return mapping

#    def delete_card(self, card_id):
#        """Delete a credit card from the database given its ID."""
#        # Check that the card exists and belongs to the user
#        self.get_card(card_id)
#        super().delete_entry(card_id)
