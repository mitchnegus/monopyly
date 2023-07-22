"""Data structures for working with credit card activity data."""

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
        row_cls = namedtuple("TransactionActivity", self.column_types)
        super().__init__([row_cls(*row) for row in data])

    @property
    def total(self):
        """The sum of the totals of each activity in the list."""
        return sum(_.total for _ in self.data)


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
