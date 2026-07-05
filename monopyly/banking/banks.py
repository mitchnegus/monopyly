"""
Tools for interacting with banks in the database.
"""

from dry_foundation.database.repository import Repository

from ..database.models import Bank


class BankRepository(Repository, model=Bank):
    """
    A database repository for managing bank information.

    Attributes
    ----------
    user_id : int
        The ID of the user who is the subject of database access.
    model : type
        The type of database model that the repository is primarily
        designed to manage.
    table : str
        The name of the database table that this repository manages.
    """

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
            (if unset, all banks will be selected).

        Returns
        -------
        banks : sqlalchemy.engine.ScalarResult
            Returns bank entries matching the criteria.
        """
        criteria = cls._initialize_criteria_list()
        criteria.add_membership_filter(cls.model, "bank_name", bank_names)
        return super().get_entries(criteria=criteria)

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
