"""Data structures for working with credit card activity data."""
from collections import UserList, namedtuple


class TransactionActivities(UserList):
    """
    A list-like datatype for storing transaction activity information.

    A subclass of `UserList` that stores transaction activity data in an
    easily accessible format. The object is constructed by passing a
    normal list of ordered lists/tuples, and converts each row into an
    equivalent `namedtuple` object, with data recorded according to
    its column type.

    Parameters
    ----------
    data : list
        A list of ordered lists/tuples that contain the data to be
        converted into this `TransactionActivities` instance.
    """

    column_types = ("transaction_date", "total", "description")

    def __init__(self, data=()):
        row_cls = namedtuple("TransactionActivity", self.column_types)
        super().__init__([row_cls(*row) for row in data])
