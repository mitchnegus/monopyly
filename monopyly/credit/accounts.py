"""
Tools for interacting with credit accounts in the database.
"""
from ..database.handler import DatabaseHandler
from ..database.models import CreditAccount


class CreditAccountHandler(DatabaseHandler):
    """
    A database handler for managing credit accounts.

    Parameters
    ----------
    user_id : int
        The ID of the user who is the subject of database access. If not
        given, the handler defaults to using the logged-in user.

    Attributes
    ----------
    table : str
        The name of the database table that this handler manages.
    db : sqlite3.Connection
        A connection to the database for interfacing.
    user_id : int
        The ID of the user who is the subject of database access.
    """
    model = CreditAccount

    @classmethod
    def get_accounts(cls, bank_ids=None):
        """
        Get credit accounts from the database.

        Query the database to select credit account fields. Accounts can
        be filtered by the issuing bank.

        Parameters
        ----------
        bank_ids : tuple of int, optional
            A sequence of bank IDs for which accounts will be selected
            (if `None`, all banks will be selected).

        Returns
        -------
        accounts : sqlalchemy.engine.ScalarResult
            Returns credit accounts matching the criteria.
        """
        criteria = [
            cls._filter_values(cls.model.bank_id, bank_ids),
        ]
        accounts = super().get_entries(*criteria)
        return accounts

    @classmethod
    def delete_entry(cls, entry_id):
        """
        Delete a credit card account from the database.

        Given an account ID, delete the credit card account from the
        database. Deleting an account will also delete all credit cards
        (along with statements and transactions) for that account.

        Parameters
        ----------
        entry_id : int
            The ID of the account to be deleted.
        """
        super().delete_entry(entry_id)

