"""
Tools for interacting with the credit statements in the database.
"""

from dateutil.relativedelta import relativedelta
from dry_foundation.database.handler import DatabaseViewHandler

from ..common.utils import get_next_occurrence_of_day
from ..database.models import (
    CreditAccount,
    CreditCard,
    CreditStatement,
    CreditStatementView,
)


class CreditStatementHandler(
    DatabaseViewHandler, model=CreditStatement, model_view=CreditStatementView
):
    """
    A database handler for managing credit card statements.

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
    def get_statements(
        cls, card_ids=None, bank_ids=None, active=None, sort_order="DESC"
    ):
        """
        Get credit card statements from the database.

        Query the database to select credit card statement fields.
        Statements can be filtered by card, the issuing bank, or by card
        active status.

        Parameters
        ----------
        card_ids : tuple of int, optional
            A sequence of card IDs for which statements will be selected
            (if `None`, all cards will be selected).
        bank_ids : tuple of ints, optional
            A sequence of bank IDs for which statements will be selected
            (if `None`, all banks will be selected).
        active : bool, optional
            A flag indicating whether only statements for active cards
            will be returned. The default is `None` where all statements
            are returned regardless of active status.
        sort_order : {'ASC', 'DESC'}
            An indicator of whether the statements should be ordered in
            ascending (oldest at top) or descending (newest at top)
            order. The default is descending order.

        Returns
        -------
        statements : sqlalchemy.engine.ScalarResult
            Returns credit card statements matching the criteria.
        """
        criteria = cls._initialize_criteria_list()
        criteria.add_match_filter(cls.model, "card_id", card_ids)
        criteria.add_match_filter(CreditAccount, "bank_id", bank_ids)
        criteria.add_match_filter(CreditCard, "active", active)
        statements = super().get_entries(
            criteria=criteria,
            column_orders={cls.model.issue_date: sort_order, CreditCard.active: "DESC"},
        )
        return statements

    @classmethod
    @DatabaseViewHandler.view_query
    def find_statement(cls, card_id, issue_date=None):
        """
        Find a statement using uniquely identifying characteristics.

        Queries the database to find a credit card statement based on
        the provided criteria. Credit card statements should be
        identifiable given the the ID of the credit card to which the
        statement belongs and the date on which the statement was
        issued.

        Parameters
        ----------
        card_id : int
            The entry ID of the credit card belonging to the statement.
        issue_date : datetime.date, optional
            The issue date for the statement to be found (if `None`, the
            most recent statement will be found).

        Returns
        -------
        statement : database.models.CreditStatementView
            The statement entry matching the given criteria. If no
            matching statement is found, returns `None`.
        """
        criteria = cls._initialize_criteria_list()
        criteria.add_match_filter(CreditCard, "id", card_id)
        criteria.add_match_filter(cls.model, "issue_date", issue_date)
        statement = super().find_entry(
            criteria=criteria,
            column_orders={cls.model.issue_date: "DESC", CreditCard.active: "DESC"},
            require_unique=False,
        )
        return statement

    @classmethod
    def infer_statement(cls, card, transaction_date, creation=False):
        """
        Infer the statement corresponding to the date of a transaction.

        Given the date of a transaction and the card used, infer the
        statement that the transaction belongs to. If the given card
        issues statements on a date later in the month than the
        transaction, the transaction will be assumed to be on that
        statement. Otherwise, the transaction is assumed to be on the
        following statement.

        Parameters
        ----------
        card : database.models.CreditCard
            The entry for the card used in the transaction.
        transaction_date : datetime.date
            The date the transaction took place.
        creation : bool, optional
            A flag indicating whether a statement should be created
            if it is not found in the database. The default is `False`;
            a statement will not be created, even if no matching
            statement already exists in the database.

        Returns
        -------
        statement : database.models.CreditStatement
            The inferred statement entry for the transaction.
        """
        issue_day = card.account.statement_issue_day
        issue_date = get_next_occurrence_of_day(issue_day, transaction_date)
        statement = cls.find_statement(card.id, issue_date)
        if not statement and creation:
            statement = cls.add_statement(card, issue_date)
        return statement

    @classmethod
    @DatabaseViewHandler.view_query
    def get_prior_statement(cls, statement):
        """
        Given a statement, get the immediately preceding statement.

        Parameters
        ----------
        statement : database.models.CreditStatement
            The statement for which to find the preceding statement.

        Returns
        -------
        statement : database.models.CreditStatementView
            The statement immediately preceding the given statement.
        """
        issue_date = statement.issue_date + relativedelta(months=-1)
        return cls.find_statement(statement.card.id, issue_date=issue_date)

    @classmethod
    def add_statement(cls, card, issue_date, due_date=None):
        """Add a statement to the database."""
        if not due_date:
            due_day = card.account.statement_due_day
            due_date = get_next_occurrence_of_day(due_day, issue_date)
        statement_data = {
            "card_id": card.id,
            "issue_date": issue_date,
            "due_date": due_date,
        }
        statement = cls.add_entry(**statement_data)
        return statement

    @classmethod
    def delete_entry(cls, entry_id):
        """
        Delete a statement from the database.

        Given a statement ID, delete the statement from the database.
        Deleting a statement will also delete all transactions on that
        statement.

        Parameters
        ----------
        entry_id : int
            The ID of the statement to be deleted.
        """
        super().delete_entry(entry_id)
