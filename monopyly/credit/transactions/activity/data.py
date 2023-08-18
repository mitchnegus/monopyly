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


class TransactionActivityGroup(UserList):
    """A minimalistic class for aggregating individual transaction activities."""

    def __init__(self, transaction_activities):
        transaction_activities = list(transaction_activities)
        self._check_grouping_validity(transaction_activities)
        super().__init__(transaction_activities)

    @property
    def transaction_date(self):
        return self.data[0].transaction_date

    @property
    def total(self):
        return sum(activity.total for activity in self.data)

    @property
    def description(self):
        return self.data[0].description

    def _check_grouping_validity(self, activities):
        self._ensure_field_commonality("transaction_date", activities)
        self._ensure_field_commonality("description", activities)

    @staticmethod
    def _ensure_field_commonality(field, activities):
        field_value = getattr(activities[0], field)
        if not all(getattr(activity, field) == field_value for activity in activities):
            raise ValueError(
                "All transaction activities in a grouping must share the same value "
                f"for the '{field}' field."
            )
