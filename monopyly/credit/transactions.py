"""
Tools for interacting with the credit transactions in the database.
"""
from ..common.forms.utils import execute_on_form_validation
from ..common.transactions import TransactionHandler
from ..database.handler import DatabaseHandler, DatabaseViewHandler
from ..database.models import (
    Bank,
    CreditAccount,
    CreditCard,
    CreditStatementView,
    CreditSubtransaction,
    CreditTag,
    CreditTransaction,
    CreditTransactionView,
    tag_link_table,
)


class CreditTransactionHandler(
    TransactionHandler, model=CreditTransaction, model_view=CreditTransactionView
):
    """
    A database handler for accessing credit transactions.

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
    def get_transactions(
        cls, statement_ids=None, card_ids=None, active=None, sort_order="DESC"
    ):
        """
        Get credit card transactions from the database.

        Query the database to select credit card transaction information.
        Transaction information includes details specific to the
        transaction, the transaction's statement, and the credit card
        used to make the transaction. Transactions can be filtered by
        statement or the credit card used. Query results can be ordered
        by either ascending or descending transaction date.

        Parameters
        ----------
        statement_ids : tuple of str, optional
            A sequence of statement IDs with which to filter
            transactions (if `None`, all statement IDs will be shown).
        card_ids : tuple of int, optional
            A sequence of card IDs with which to filter transactions (if
            `None`, all card IDs will be shown).
        active : bool, optional
            A flag indicating whether only transactions for active cards
            will be returned. The default is `None` (all transactions
            are returned).
        sort_order : {'ASC', 'DESC'}
            An indicator of whether the transactions should be ordered
            in ascending (oldest at top) or descending (newest at top)
            order.

        Returns
        -------
        transactions : sqlalchemy.engine.ScalarResult
            Returns credit card transactions matching the criteria.
        """
        criteria = cls._initialize_criteria_list()
        criteria.add_match_filter(cls.model, "statement_id", statement_ids)
        criteria.add_match_filter(CreditCard, "id", card_ids)
        criteria.add_match_filter(CreditCard, "active", active)
        transactions = super().get_entries(criteria, sort_order=sort_order)
        return transactions

    @classmethod
    def add_entry(cls, **field_values):
        """
        Add a transaction to the database.

        Uses values acquired from a `CreditTransactionForm` to add a new
        transaction into the database. The values include information
        for the transaction, along with information for all
        subtransactions (including tags associated with each
        subtransaction).

        Parameters
        ----------
        **field_values :
            Values for each field in the transaction (including
            subtransaction values and tags).

        Returns
        -------
        transaction : database.models.CreditTransaction
            The saved transaction.
        """
        return super().add_entry(**field_values)

    @staticmethod
    def _prepare_subtransaction(transaction, subtransaction_data):
        """Prepare a subtransaction for the given transaction."""
        # NOTE I don't believe that this adds new tags to the database
        tag_names = subtransaction_data.pop("tags")
        return CreditSubtransaction(
            transaction_id=transaction.id,
            **subtransaction_data,
            tags=CreditTagHandler.get_tags(tag_names, ancestors=True),
        )


class CreditTagHandler(DatabaseHandler, model=CreditTag):
    """
    A database handler for managing credit transaction tags.

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
    def get_tags(
        cls,
        tag_names=None,
        transaction_ids=None,
        subtransaction_ids=None,
        ancestors=None,
    ):
        """
        Get credit card transaction tags from the database.

        Query the database to select credit transaction tag fields. Tags
        can be filtered by tag name or transaction.

        Parameters
        ----------
        tag_names : tuple of str, optional
            A sequence of names of tags to be selected (if `None`, all
            tag names will be selected).
        transaction_ids : tuple of int, optional
            A sequence of transaction IDs for which tags will be
            selected (if `None`, all transaction tags will be selected).
        subtransaction_ids : tuple of int, optional
            A sequence of subtransaction IDs for which tags will be
            selected (if `None`, all subtransaction tags will be selected).
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
        tags : list of database.models.CreditTag
            Returns credit card transaction tags matching the criteria.
        """
        criteria = cls._initialize_criteria_list()
        criteria.add_match_filter(cls.model, "tag_name", tag_names)
        criteria.add_match_filter(CreditTransactionView, "id", transaction_ids)
        criteria.add_match_filter(CreditSubtransaction, "id", subtransaction_ids)
        tags = super().get_entries(criteria).all()
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
        # Add a join to enable filtering by transaction ID or subtransaction ID
        query = (
            query.join(tag_link_table)
            .join(CreditSubtransaction)
            .join(CreditTransactionView)
            .join(CreditStatementView)
            .join(CreditCard)
            .join(CreditAccount)
            .join(Bank)
        )
        # Only get distinct tag entries
        query = query.distinct()
        return super()._filter_entries(query, criteria)

    @classmethod
    def get_subtags(cls, tag):
        """
        Get subcategories (children) of a given credit transaction tag.

        Parameters
        ----------
        tag : database.models.CreditTag
            The parent tag for which to find subtags. (A value of `None`
            indicates that top level tags should be found.)

        Returns
        -------
        subtags : sqlalchemy.engine.ScalarResult
            A list of credit card transaction tags that are
            subcategories of the given parent tag.
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
        Get the supercategory (parent) of a credit transaction tag.

        Parameters
        ----------
        tag_id : int
            The child tag for which to find supertags.

        Returns
        -------
        supertag : database.models.CreditTag
            The credit card transaction tag that is the parent category
            of the given tag. Returns `None` if no parent tag is found.
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
        root_tag : database.models.CreditTag
            The root tag to use as the starting point when recursing
            through the tree. If the parent is `None`, the recursion
            begins at the highest level of tags.

        Returns
        -------
        hierarchy : dict
            The dictionary representing the user's tags. Keys are
            `CreditTag` objects.
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
        tag : database.models.CreditTag
            The tag for which to find ancestors.

        Returns
        -------
        ancestors : list of database.models.CreditTag
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
        tag : database.models.CreditTag
            The tag entry matching the given criteria. If no matching
            tag is found, returns `None`.
        """
        criteria = cls._initialize_criteria_list()
        criteria.add_match_filter(cls.model, "tag_name", tag_name)
        tag = super().find_entry(criteria=criteria)
        return tag


@execute_on_form_validation
def save_transaction(form, transaction_id=None):
    """
    Save a credit transaction.

    Saves a transaction in the database. If a transaction ID is given,
    then the transaction is updated with the form information. Otherwise
    the form information is added as a new entry.

    Parameters
    ----------
    form : CreditTransactionForm
        The form being used to provide the data being saved.
    transaction_id : int
        The ID of the transaction to be saved. If provided, the
        named transaction will be updated in the database. Otherwise, if
        the transaction ID is `None`, a new transaction will be added.

    Returns
    -------
    transaction : database.models.CreditTransactionView
        The saved transaction.
    """
    transaction_data = form.transaction_data
    if transaction_id:
        transaction = CreditTransactionHandler.get_entry(transaction_id)
        transaction_data.update(
            internal_transaction_id=transaction.internal_transaction_id
        )
        # Update the database with the updated transaction
        transaction = CreditTransactionHandler.update_entry(
            transaction_id,
            **transaction_data,
        )
    else:
        # Insert the new transaction into the database
        transaction = CreditTransactionHandler.add_entry(**transaction_data)
    return transaction
