"""
Tools for connecting to and working with the SQLite database.
"""


def validate_sort_order(sort_order):
    """
    Ensure that a valid sort order was provided.

    Parameters
    ----------
    sort_order : str
        The order, ascending or descending, that should be used when
        sorting the returned values from the database query. The order
        must be either 'ASC' or 'DESC'.
    """
    if sort_order not in ('ASC', 'DESC'):
        raise ValueError('Provide a valid sort order.')

