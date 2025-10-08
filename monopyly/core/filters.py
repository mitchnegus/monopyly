"""
Filters defined for the application.
"""

from .blueprint import bp


@bp.app_template_filter("currency")
def make_currency(amount):
    """Return the amount to two decimal places (always shown)."""
    # Correct values of -0.00 to 0
    amount = amount if round(amount, 2) != 0 else 0
    return f"{amount:,.2f}"


@bp.app_template_filter("ordinal")
def make_ordinal(integer):
    """
    Return the ordinal representation of an integer.

    Given an integer, return the number and it's ordinal indicator. For
    example:
        -   1 => 1st
        -   2 => 2nd
        -   3 => 3rd
        -   4 => 4th
        -   5 => 5th
        -  10 => 10th
        -  11 => 11th
        -  21 => 21st
        -  101 => 101st

    Notes
    -----
    This function is an adaptation of the one proposed by Stack Overflow
    user Florian Brucker (https://stackoverflow.com/a/50992575/8754471).

    Parameters
    ----------
    integer : int
        An integer to convert to its ordinal representation.

    Returns
    -------
    ordinal : str
        An integer's ordinal representation.
    """
    suffix = ["th", "st", "nd", "rd", "th"][min(integer % 10, 4)]
    if 11 <= (integer % 100) <= 13:
        suffix = "th"
    return f"{integer}{suffix}"
