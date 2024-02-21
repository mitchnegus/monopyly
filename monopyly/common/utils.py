"""
General utility objects.
"""

import datetime
from collections import Counter
from datetime import timezone

from dateutil.relativedelta import relativedelta


def parse_date(given_date):
    """
    Given a string in an accepted format, return a Python date object.

    All dates should be stored in the database as YYYY-MM-DD, but can be
    added to the database directly from Python date objects. This
    function takes a date that is given as any of the acceptable formats
    and returns a date object (which can be added into the database).
    The following are acceptable date formats (in order of parsing
    precedence):
        - YYYYMMDD
        - YYYY/[M]M/[D]D
        - [M]M/[D]D/[YY]YY
    Dates with a delimiter between time categories (day, month, year)
    are not required to have two digit values (e.g., 'August' could be
    indicated by '08' or just '8'). For dates that are given with a
    delimiter, it may be either "/", ".", or "-".

    If a `datetime.date` object is given, it is returned without
    processing.

    Parameters
    ----------
    given_date : str, datetime.date
        A date given in one of the acceptable formats to be formatted
        consistently with the database.

    Returns
    -------
    date : datetime.date
        A Python `date` object based on the given date string.
    """
    if not given_date:
        return None
    if isinstance(given_date, datetime.date):
        return given_date
    # Handle options for alternate delimiters
    return _DateParser(given_date).parse()


class _DateParser:
    """Class used to parse dates within the `parse_date` function."""

    alt_delimiters = (".", "/")
    date_formats = ("%Y-%m-%d", "%m-%d-%Y", "%m-%d-%y")

    def __init__(self, given_date):
        self.given_date = given_date
        self.err_msg = (
            f"The given date ('{given_date}') was not in an "
            "acceptable format. Try entering the date in the "
            "format 'YYYY-MM-DD'."
        )

    def parse(self):
        """Parse the date (string) into a Python `datetime.date` object."""
        components = self._get_date_components(self.given_date)
        parseable_string = "-".join(components)
        return self._attempt_datetime_parsing(parseable_string)

    def _get_date_components(self, given_date):
        """Split the date string into year, month, and day components."""
        if len(given_date) == 8 and given_date.isnumeric():
            # Assign components by their place (sans delimiter)
            components = [given_date[:4], given_date[4:6], given_date[6:]]
        else:
            delimited_date = self._standardize_delimiters(given_date)
            components = self._split_delimited_date(delimited_date)
        return components

    def _standardize_delimiters(self, date_string):
        """Set the delimiter in all dates to '-' for simplified parsing."""
        for delimiter in self.alt_delimiters:
            date_string = date_string.replace(delimiter, "-")
        return date_string

    def _split_delimited_date(self, delimited_date_string):
        """Split a delimited date into components (padding if necessary)."""
        split_date = delimited_date_string.split("-")
        if len(split_date) == 3:
            return self._pad_components(split_date)
        else:
            # There should not be anything other than three date components
            raise ValueError(self.err_msg)

    def _pad_components(self, split_date):
        """Pad each component with leading zeros if less than two digits."""
        return [f"{_:0>2}" if len(_) < 2 else _ for _ in split_date]

    def _attempt_datetime_parsing(self, parseable_string):
        """Attempt to parse the string into a date using the valid formats."""
        for fmt in self.date_formats:
            try:
                date = datetime.datetime.strptime(parseable_string, fmt).date()
                return date
            except ValueError:
                pass
        raise ValueError(self.err_msg)


def convert_date_to_midnight_timestamp(date, milliseconds=False):
    """
    Convert a date to the corresponding Unix timestamp (at midnight UTC).

    Parameters
    ----------
    date : datetime.date
        The date to be converted to a timestamp.
    milliseconds : bool
        A flag indicating if the converted date should be represented
        in milliseconds. The default is `False`, and the timestamp will
        be given in full seconds since the epoch.

    Returns
    -------
    timestamp : int
        The timestamp corresponding to the given date (at midnight UTC).
    """
    midnight = datetime.datetime.min.time()
    utc_datetime = datetime.datetime.combine(date, midnight, tzinfo=timezone.utc)
    timestamp = int(utc_datetime.timestamp())
    if milliseconds:
        timestamp *= 1000
    return timestamp


def get_next_occurrence_of_day(day, given_date):
    """
    Given a day of the month and a date, find the next occurrence of the day.
    """
    day_date_in_given_date_month = given_date.replace(day=day)
    if given_date.day < day:
        # The next occurrence of the day happens later in the same month
        next_date = day_date_in_given_date_month
    else:
        # The next occurrence of the day happens in the next month
        next_date = day_date_in_given_date_month + relativedelta(months=+1)
    return next_date


def dedelimit_float(value, delimiter=","):
    """Remove delimiters from strings before conversion to floats."""
    try:
        return float(value.replace(delimiter, ""))
    except AttributeError:
        return float(value)


def sort_by_frequency(items):
    """Return a sorted (unique) list ordered by decreasing frequency."""
    item_counts = Counter(items)
    unique_items = set(items)
    return sorted(unique_items, key=item_counts.get, reverse=True)
