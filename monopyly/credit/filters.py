"""
Filters for making database selections.
"""
from ..utils import reserve_places
from .constants import ALL_FIELDS


def select_fields(fields):
    """Create placeholders for given fields (all fields if none are given)."""
    if fields is None:
        return "*"
    elif not all(field.split('.')[-1] in ALL_FIELDS for field in fields):
        raise ValueError('The given field does not exist in the database.')
    return ', '.join(fields)


def filter_banks(banks, prefix=""):
    """Create a filter based on a set of banks."""
    if banks is None:
        return ""
    return f"{prefix} bank IN ({reserve_places(banks)})"


def filter_cards(card_ids, prefix=""):
    """Create a filter based on a set of card IDs."""
    if card_ids is None:
        return ""
    return f"{prefix} card_id IN ({reserve_places(card_ids)})"


def filter_statements(statement_ids, prefix=""):
    """Create a filter based on a set of statement IDs."""
    if statement_ids is None:
        return ""
    return f"{prefix} statement_id IN ({reserve_places(statement_ids)})"
