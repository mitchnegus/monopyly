"""Module describing logical credit actions (to be used in routes)."""
from ..common.actions import get_groupings
from .statements import CreditStatementHandler


def get_card_statement_groupings(cards):
    """
    Get groupings (by card) of credit card statements.

    Parameters
    ----------
    cards : list of sqlite3.Row
        The database card entries for which to get statements.

    Returns
    -------
    card_statements : dict
        A mapping between the card entries and a list of all
        corresponding statement entries for that card.
    """
    statement_db = CreditStatementHandler()
    # Specify the fields explicitly to make use of date converters
    fields = ('card_id', 'issue_date', 'due_date', 'balance', 'payment_date')
    # Get groupings of statements (grouped by card)
    card_statements = get_groupings(cards, statement_db, fields=fields)
    return card_statements

