"""Data structures for working with credit card activity data."""

import datetime
from collections import UserList, namedtuple
from pathlib import Path

from flask import current_app
from werkzeug.utils import secure_filename


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
        super().__init__([self._load_activity_from_data(*row) for row in data])

    @classmethod
    def _load_activity_from_data(cls, date, total, description):
        activity_cls = namedtuple("TransactionActivity", cls.column_types)
        if isinstance(date, datetime.date):
            transaction_date = date
        else:
            try:
                transaction_date = datetime.datetime.strptime(date, "%Y-%m-%d").date()
            except ValueError:
                raise ValueError(
                    f"The given date '{date}' of type `{type(date)}` is not recognized. "
                    "Dates must be native `datetime.date` objects or strings given in "
                    "the form 'YYYY-MM-DD'."
                )
        return activity_cls(transaction_date, total, description)

    @property
    def total(self):
        """The sum of the totals of each activity in the list."""
        return sum(_.total for _ in self.data)

    def jsonify(self):
        """Return a JSON serializable representation of the activities."""
        return [(str(_.transaction_date), _.total, _.description) for _ in self.data]


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


class ActivityLoadingError(RuntimeError):
    """A special exception indicating that an activity CSV failed to load."""

    def __init__(self, msg="", *args, **kwargs):
        self.msg = msg
        super().__init__(msg, *args, **kwargs)


class TransactionActivityLoader:
    """
    A tool to load transaction activity CSV files.

    This is an object designed to load CSV files provided by a user. It
    loads the file, stores it in an app-local directory, and then
    provides access to uploaded file path.

    Parameters
    ----------
    activity_dir : pathlib.Path
        The path to the directory where uploaded activity files will be
        stored. The default path is a directory named `.credit_activity`
        within the app's instance directory.

    Attributes
    ----------
    activity_dir : pathlib.Path
        The path to the directory where uploaded activity files will be
        stored. If left unset, the default path will be a directory
        named `.credit_activity` within the app's instance directory.
    loaded_files : list
        A list of paths to loaded files; this list is empty before
        adding any files and after cleaning up any previously loaded
        files.
    """

    def __init__(self, activity_dir=None):
        # Create and use a directory to store uploaded activity files
        default_activity_dir = Path(current_app.instance_path) / ".credit_activity"
        self.activity_dir = Path(activity_dir) if activity_dir else default_activity_dir
        self.activity_dir.mkdir(exist_ok=True)
        self.loaded_files = []

    def upload(self, activity_file):
        """
        Upload a CSV file containing credit transaction activity.

        Parameters
        ----------
        activity_file : werkzeug.datastructures.FileStorage
            The file object to be loaded.

        Returns
        -------
        activity_filepath : pathlib.Path
            The path to the uploaded activity file.
        """
        activity_filename = secure_filename(activity_file.filename)
        if not activity_filename:
            raise ActivityLoadingError("No activity file was specified.")
        activity_filepath = self.activity_dir / activity_filename
        activity_file.save(activity_filepath)
        self.loaded_files.append(activity_filepath)
        return activity_filepath

    def cleanup(self):
        """Clean all loaded files from the activity directory."""
        while self.loaded_files:
            activity_filepath = self.loaded_files.pop()
            activity_filepath.unlink()
