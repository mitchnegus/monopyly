"""
Tools for interacting with credit accounts in the database.
"""

from dry_foundation.database.handler import DatabaseHandler

from ..database.models import CreditAccount


class CreditAccountHandler(DatabaseHandler, model=CreditAccount):
    """
    A database handler for managing credit accounts.

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
        criteria = cls._initialize_criteria_list()
        criteria.add_match_filter(cls.model, "bank_id", bank_ids)
        accounts = super().get_entries(criteria=criteria)
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
