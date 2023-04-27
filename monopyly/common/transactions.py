"""
Tools for building a common transaction interface.
"""
from abc import abstractmethod

from authanor.database.handler import DatabaseHandler, DatabaseViewHandler
from flask import current_app

from ..database.models import (
    BankAccountTypeView,
    BankTransactionView,
    CreditTransactionView,
    TransactionTag,
)


class TransactionHandler(DatabaseViewHandler):
    """
    An abstract database handler for accessing transactions.

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
    def _customize_entries_query(cls, query, criteria, column_orders):
        # Group transactions and order by transaction date
        query = query.group_by(cls.model.id)
        return super()._customize_entries_query(query, criteria, column_orders)

    @classmethod
    def _get_transactions(cls, criteria=None, sort_order="DESC"):
        # Specify transaction order
        column_orders = {cls.model.transaction_date: sort_order}
        entries = cls.get_entries(
            entry_ids=None, criteria=criteria, column_orders=column_orders
        )
        return entries

    @classmethod
    def add_entry(cls, **field_values):
        """
        Add a transaction to the database.

        Uses values acquired from a `TransactionForm` to add a new
        transaction into the database. The values include information
        for the transaction, along with information for all
        subtransactions.

        Parameters
        ----------
        **field_values :
            Values for each field in the transaction (including
            subtransaction values).

        Returns
        -------
        transaction : database.models.BankTransaction
            The saved transaction.
        """
        # Extend the default method to account for subtransactions
        subtransactions_data = field_values.pop("subtransactions")
        transaction = super().add_entry(**field_values)
        cls._add_subtransactions(transaction, subtransactions_data)
        # Refresh the transaction with the subtransaction information
        cls._db.session.refresh(transaction)
        return transaction

    @classmethod
    def update_entry(cls, entry_id, **field_values):
        """Update a transaction in the database."""
        # Extend the default method to account for subtransactions
        subtransactions_data = field_values.pop("subtransactions", None)
        transaction = super().update_entry(entry_id, **field_values)
        if subtransactions_data:
            # Replace all subtransactions when updating any subtransaction
            for subtransaction in transaction.subtransactions:
                cls._db.session.delete(subtransaction)
            cls._add_subtransactions(transaction, subtransactions_data)
        # Refresh the transaction with the subtransaction information
        cls._db.session.refresh(transaction)
        return transaction

    @classmethod
    def _add_subtransactions(cls, transaction, subtransactions_data):
        """Add subtransactions to the database for the data given."""
        for subtransaction_data in subtransactions_data:
            subtransaction = cls._prepare_subtransaction(
                transaction, subtransaction_data
            )
            cls._db.session.add(subtransaction)
        # Flush to the database after all subtransactions have been added
        cls._db.session.flush()


def get_linked_transaction(transaction):
    """
    Find a transaction that is linked to the given transaction.

    Checks all transaction databases for a transaction that matches
    the given transaction.

    Parameters
    ----------
    transaction : Transaction
        The transaction for which to find a linked transaction.

    Returns
    -------
    linked_transaction : Transaction
        A transaction that is linked to the given transaction. If no
        linked transaction is found, `None` is returned.
    """
    internal_transaction_id = transaction.internal_transaction_id
    if not internal_transaction_id:
        return None
    # First, check if there is a matching bank transaction
    linked_transaction = _get_linked_bank_transaction(
        transaction.id, internal_transaction_id
    )
    if not linked_transaction:
        # Otherwise, check if there is a matching credit transaction
        linked_transaction = _get_linked_credit_transaction(
            transaction.id, internal_transaction_id
        )
    return linked_transaction


def _get_linked_bank_transaction(transaction_id, internal_transaction_id):
    """Get a bank transaction linked to the given transaction."""
    query = BankTransactionView.select_for_user().join(BankAccountTypeView)
    criteria = [
        BankTransactionView.id != transaction_id,
        BankTransactionView.internal_transaction_id == internal_transaction_id,
    ]
    query = query.where(*criteria)
    transaction = current_app.db.session.execute(query).scalar_one_or_none()
    return transaction


def _get_linked_credit_transaction(transaction_id, internal_transaction_id):
    """Get a credit transaction linked to the given transaction."""
    query = CreditTransactionView.select_for_user()
    criteria = [
        CreditTransactionView.id != transaction_id,
        CreditTransactionView.internal_transaction_id == internal_transaction_id,
    ]
    query = query.where(*criteria)
    transaction = current_app.db.session.execute(query).scalar_one_or_none()
    return transaction


class TransactionTagHandler(DatabaseHandler, model=TransactionTag):
    """
    A database handler for managing transaction tags.

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
    def _get_tags(
        cls,
        criteria,
        tag_names=None,
        transaction_ids=None,
        subtransaction_ids=None,
        ancestors=None,
    ):
        """
        Get transaction tags from the database.

        Query the database to select transaction tag fields. Tags can
        be filtered by tag name or transaction.

        Parameters
        ----------
        criteria : database.handler.QueryCriteria
            Criteria used to select tags from the database.
        ancestors : bool, optional
            A flag indicating whether the query should include tags
            that are the ancestor tags of other explictly selected tags
            returned from the database based on selection criteria. If
            `True`, all tags matching the criteria will be returned
            along with their ancestor tags. If `False`, any tag that is
            an ancestor of another tag in the list will be removed from
            the list. The default is `None`, in which case all tags
            matching the criteria will be returned, and no others.

        Returns
        -------
        tags : list of database.models.TransactionTag
            Returns transaction tags matching the criteria.
        """
        tags = super().get_entries(criteria=criteria).all()
        if ancestors is True:
            # Add all ancestors for each tag in the list
            for tag in tags:
                for ancestor in cls.get_ancestors(tag):
                    if ancestor not in tags:
                        tags.append(ancestor)
        elif ancestors is False:
            # Remove ancestors of other tags in the list from the list
            for tag in tags:
                for ancestor in cls.get_ancestors(tag):
                    if ancestor in tags:
                        tags.remove(ancestor)
        return tags

    @classmethod
    def _filter_entries(cls, query, criteria):
        # Only get distinct tag entries
        query = query.distinct()
        return super()._filter_entries(query, criteria)

    @classmethod
    def get_subtags(cls, tag):
        """
        Get subcategories (children) of a given transaction tag.

        Parameters
        ----------
        tag : database.models.TransactionTag
            The parent tag for which to find subtags. (A value of `None`
            indicates that top level tags should be found.)

        Returns
        -------
        subtags : sqlalchemy.engine.ScalarResult
            A list of transaction tags that are subcategories of the
            given parent tag.
        """
        query = cls.model.select_for_user()
        # Filter the query to get only subtags of the given tag
        parent_id = tag.id if tag else None
        query = query.where(cls.model.parent_id == parent_id)
        subtags = cls._db.session.execute(query).scalars()
        return subtags

    @classmethod
    def get_supertag(cls, tag):
        """
        Get the supercategory (parent) of a transaction tag.

        Parameters
        ----------
        tag_id : int
            The child tag for which to find supertags.

        Returns
        -------
        supertag : database.models.TransactionTag
            The transaction tag that is the parent category of the given
            tag. Returns `None` if no parent tag is found.
        """
        parent_id = tag.parent_id
        supertag = cls.get_entry(parent_id) if parent_id else None
        return supertag

    @classmethod
    def get_hierarchy(cls, root_tag=None):
        """
        Get the hierarchy of tags as a dictionary.

        Recurses through the tags database to return a dictionary
        representation of the tags. The dictionary has keys representing
        each tag, and each key is paired to a similar dictionary of
        subtags for that tag. The top level of the dictionary consists
        only of tags without root tags.

        Parameters
        ----------
        root_tag : database.models.TransactionTag
            The root tag to use as the starting point when recursing
            through the tree. If the parent is `None`, the recursion
            begins at the highest level of tags.

        Returns
        -------
        hierarchy : dict
            The dictionary representing the user's tags. Keys are
            `TransactionTag` objects.
        """
        hierarchy = {}
        for tag in cls.get_subtags(root_tag):
            hierarchy[tag] = cls.get_hierarchy(tag)
        return hierarchy

    @classmethod
    def get_ancestors(cls, tag):
        """
        Get the ancestor tags of a given tag.

        Traverses the hierarchy, starting from the given tag and returns
        a list of all tags that are ancestors of the given tag.

        Parameters
        ----------
        tag : database.models.TransactionTag
            The tag for which to find ancestors.

        Returns
        -------
        ancestors : list of database.models.TransactionTag
            The ancestors of the given tag.
        """
        ancestors = []
        ancestor = cls.get_supertag(tag)
        while ancestor:
            ancestors.append(ancestor)
            ancestor = cls.get_supertag(ancestor)
        return ancestors

    @classmethod
    def find_tag(cls, tag_name):
        """
        Find a tag using uniquely identifying characteristics.

        Queries the database to find a transaction tag based on the
        provided criteria (the tag's name).

        Parameters
        ----------
        tag_name : str
            The name of the tag to be found.

        Returns
        -------
        tag : database.models.TransactionTag
            The tag entry matching the given criteria. If no matching
            tag is found, returns `None`.
        """
        criteria = [cls.model.tag_name == tag_name]
        query = cls.model.select_for_user().where(*criteria)
        tag = cls._db.session.execute(query).scalar_one_or_none()
        return tag
