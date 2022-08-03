"""
Tools for interacting with banks in the database.
"""
from ..database.handler import DatabaseHandler
from ..database.models import Bank


class BankHandler(DatabaseHandler):
    """
    A database handler for managing bank information.

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
    model = Bank

    @classmethod
    def get_banks(cls, bank_names=None):
        """
        Get banks from the database.

        Query the database to select bank fields. Banks can be filtered
        by name.

        Parameters
        ----------
        bank_names : list of str, optional
            A sequence of bank names for which banks will be selected
            (if `None`, all banks will be selected).

        Returns
        -------
        banks : sqlalchemy.engine.ScalarResult
            Returns bank entries matching the criteria.
        """
        criteria = [cls._filter_values(cls.model.bank_name, bank_names)]
        return super().get_entries(*criteria)

    @classmethod
    def delete_entry(cls, entry_id):
        """
        Delete a bank from the database.

        Given a bank ID, delete the bank from the database. Deleting an
        account will also delete all accounts (and transactions)
        associated with that account.

        Parameters
        ----------
        entry_id : int
            The ID of the bank to be deleted.
        """
        super().delete_entry(entry_id)

