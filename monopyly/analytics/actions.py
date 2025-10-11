"""Module describing logical analytics actions (to be used in routes)."""

from collections import UserDict, UserList
from datetime import date, datetime, timedelta
from itertools import chain
from operator import attrgetter

from ..database.models import BankSubtransaction, CreditSubtransaction


def get_tag_statistics_chart_data(tags, limit=5):
    """
    Build a dataset to be passed to a `chartist.js` chart constructor.

    Parameters
    ----------
    tags : list
        A sequence of tags, such as that produced by a tag repository.
    limit : int
        A maximum number of tags to serve as the limit on the chart.

    Returns
    -------
    chart_data : TagStatisticsChartData
        A dictionary-like object containing a Chartist compatible data
        structure, including labels corresponding to each month of
        statistics and series corresponding to tag subtotals for each of
        those months.
    """
    return TagStatisticsChartData(tags, limit=limit)


class TagStatisticsChartData(UserDict):
    """
    A mapping of tag statistics to be passed to a `chartist.js` chart constructor.

    A special dictionary-like object containing data for tag-based
    statistics formatted for use in a bar chart created by the
    `chartist.js` library. The dictionary contains an entry for labels
    (corresponding to the months of data covered by the selected tags)
    and a set of series corresponding to the subtotals for each of those
    tags in any given month.

    Tags are sorted (and the limit applied) according to tags with the
    greatest subtransaction volume by expenditure amount over the course
    of the most recent year.

    Parameters
    ----------
    tags : list
        A sequence of tags, such as that produced by a tag repository.
    limit : int
        A maximum number of tags to serve as the limit on the chart.
        Performance may suffer if the limit is too large.
    """

    def __init__(self, tags, limit=5):
        if not tags:
            raise ValueError("No tags were provided.")
        if limit <= 0:
            raise ValueError("The tag limit must be a positive integer.")
        # Collect the data and rank/limit it
        ranked_tag_stats = sorted(
            [_TagStatistics(tag) for tag in tags],
            key=attrgetter("past_year_total"),
            reverse=True,
        )
        self.statistics = ranked_tag_stats[:limit]
        # Prepare chart elements
        month_bins = self._prepare_chart_bins(self.statistics)
        labels = month_bins.milliseconds
        values = self._prepare_chart_values(month_bins, self.statistics)
        # Set metadata for the chart (using attributes)
        super().__init__({"labels": labels, "series": values})

    @property
    def title(self):
        if (tag_count := len(self.statistics)) > 1:
            return f"Top {tag_count} Tags by Subtotal"
        return self.statistics[0].tag.tag_name

    @staticmethod
    def _prepare_chart_bins(tag_statistics_collection):
        # Determine all the months with expenditure amounts in the data
        recorded_months = chain.from_iterable(
            [month for month, subtotal in tag_stats.monthly_amounts.items()]
            for tag_stats in tag_statistics_collection
        )
        return _MonthRange.load_from_collection(set(recorded_months))

    @staticmethod
    def _prepare_chart_values(month_bins, tag_statistics_collection):
        return [
            [round(tag_stats.monthly_amounts.get(month, 0), 2) for month in month_bins]
            for tag_stats in tag_statistics_collection
        ]


class _MonthRange(UserList):
    """
    A helper object to store (and generate) a continuous range of months.

    Given an interval specified by a minimum date and a maximum date,
    create a list-like object containing the full range of months
    represented by the interval.

    Notes:
        Be aware that the month range is _inclusive_, unlike typical
        Python ranges.
    """

    def __init__(self, min_date, max_date):
        # Convert date boundaries into dates corresponding to the first day of the month
        min_date_month = min_date.replace(day=1)
        max_date_month = max_date.replace(day=1)
        # Generate a range of dates between the boundaries
        month_range = [min_date_month]
        while (month := self._increment_month(month_range[-1])) <= max_date_month:
            month_range.append(month)
        super().__init__(month_range)

    @property
    def milliseconds(self):
        return [int(self._get_month_min_timestamp(month) * 1000) for month in self]

    @classmethod
    def load_from_collection(cls, month_collection):
        oldest_month, newest_month = min(month_collection), max(month_collection)
        return cls(oldest_month, newest_month)

    @staticmethod
    def _increment_month(month):
        # Adding 31 days from the first of a month always lands in the next month
        return (month + timedelta(days=31)).replace(day=1)

    @staticmethod
    def _get_month_min_timestamp(month):
        # Get the minimum Unix timestamp for a month (represented by a `date` object)
        return datetime.combine(month, datetime.min.time()).timestamp()


class _TagStatistics:
    """
    An object storing statistics about a tag.

    Parameters
    ----------
    tag : TransactionTag
        A tag representing a category of transaction for which
        statistics will be collected.
    """

    def __init__(self, tag):
        self.tag = tag
        self._today = date.today()
        # Determine the amounts spent on the tag category each month over its lifetime
        self.monthly_amounts = self._calculate_monthly_amounts()
        # Determine the amounts spent on the tag category
        this_month = self._get_current_month()
        this_month_last_year = this_month.replace(year=this_month.year - 1)
        self.all_time_total = sum(
            month_subtotal for month, month_subtotal in self.monthly_amounts.items()
        )
        self.all_time_average = self.all_time_total / len(self.monthly_amounts)
        self.past_year_total = self._get_interval_total(
            this_month_last_year, this_month
        )
        self.past_year_average = (
            # Get the average over the past year (or the tag's lifetime, if shorter)
            self.past_year_total / min(12, len(self.monthly_amounts))
        )

    def _get_current_month(self):
        return self._today.replace(day=1)

    def _calculate_monthly_amounts(self):
        # Ensure that entry exists for the current month
        monthly_amounts = {self._get_current_month(): 0}
        # Populate entries for months with expenditures
        for subtransaction in self.tag.subtransactions:
            # Determine the month of the subtransaction
            transaction_month = self._get_subtransaction_month(subtransaction)
            monthly_amounts.setdefault(transaction_month, 0)
            # For the given month, calculate the cumulative expenditure amount
            expenditure_subtotal = self._calculate_expenditure_subtotal(subtransaction)
            monthly_amounts[transaction_month] += expenditure_subtotal
        # Populate entries for months in the tag's lifetime without expenditures
        # (ensuring correctly calculated expenditure averages)
        for month in _MonthRange.load_from_collection(monthly_amounts.keys()):
            monthly_amounts.setdefault(month, 0)
        return monthly_amounts

    @staticmethod
    def _get_subtransaction_month(subtransaction):
        # Get the month of the subtransaction from the transaction date
        return subtransaction.transaction_view.transaction_date.replace(day=1)

    @staticmethod
    def _calculate_expenditure_subtotal(subtransaction):
        if isinstance(subtransaction, BankSubtransaction):
            # Bank subtransaction expenditures are given as negative values
            expenditure_subtotal = -subtransaction.subtotal
        elif isinstance(subtransaction, CreditSubtransaction):
            expenditure_subtotal = subtransaction.subtotal
        else:
            raise TypeError("The subtransaction must be a known subtransaction type.")
        return expenditure_subtotal

    def _get_interval_total(self, start_date, end_date):
        # Given monthly tag totals, calculate the total expenditures in the interval
        return sum(
            month_subtotal
            for month, month_subtotal in self.monthly_amounts.items()
            if month >= start_date and month < end_date
        )
