"""Module describing logical analytics actions (to be used in routes)."""

from collections import UserDict, UserList
from datetime import date, datetime, timedelta
from itertools import chain

from ..database.models import BankSubtransaction, CreditSubtransaction


def get_tag_statistics_chart_data(tags, limit=5):
    """
    Build a dataset to be passed to a `chartist.js` chart constructor.

    Parameters
    ----------
    tags : list
        A sequence of tags, such as that produced by a tag handler.
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
        A sequence of tags, such as that produced by a tag handler.
    limit : int
        A maximum number of tags to serve as the limit on the chart.
    """

    def __init__(self, tags, limit=5):
        if not tags:
            raise ValueError("No tags were provided.")
        # Collect the data and rank/limit it
        tag_data = _RankedTagData(tags, limit=limit)
        # Determine all the months with expenditure amounts in the data
        month_iterator = chain.from_iterable(
            [month for month, stats in month_stats.items() if stats]
            for month_stats in tag_data.values()
        )
        months = _MonthRange.load_from_collection(set(month_iterator))
        # Use Unix timestamp in milliseconds as keys
        labels = months.milliseconds
        chart_data = [
            [round(stats.get(month, 0), 2) for month in months]
            for stats in tag_data.values()
        ]
        # Set metadata for the chart (using attributes)
        self.tag_names = list(tag_data.keys())
        if (tag_count := len(self.tag_names)) > 1:
            self.title = f"Top {tag_count} Tags by Subtotal"
            self.notable_statistics = None
        else:
            self.title = self.tag_names[0]
            tag_monthly_totals = chart_data[0]
            tag_lifetime_total = sum(tag_monthly_totals)
            self.notable_statistics = {
                "lifetime_total": tag_lifetime_total,
                "monthly_average": tag_lifetime_total / len(tag_monthly_totals),
            }
        super().__init__({"labels": labels, "series": chart_data})


class _MonthRange(UserList):
    """
    A helper object to store (and generate) a continuous range of months.

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


class _RankedTagData(UserDict):
    """
    A helper object to collect tag data and rank it.

    The resulting object is a dictionary-like structure containing
    tag names paired with dictionaries of monthly subtotals for those
    tags. The tags are sorted according to their expenditure totals over
    the past year. If a limit is specified, the resulting object data is
    limited to no more than that many tags.

    Parameters
    ----------
    tags : list
        A sequence of tags, such as that produced by a tag handler.
    limit : int
        A maximum number of tags to be included in the ranked data.
    """

    def __init__(self, tags, limit=None):
        if (limit := limit or len(tags)) <= 0:
            raise ValueError("The tag limit must be a positive integer.")
        # Rank tags by subtransaction volume ($) in the past year, then apply limit
        tag_stats = [self._get_sortable_data_info(tag) for tag in tags]
        ranked_tag_stats = sorted(tag_stats, reverse=True)
        super().__init__(
            {tag_name: stats for amount, tag_name, stats in ranked_tag_stats[:limit]}
        )

    def _get_sortable_data_info(self, tag):
        # Get monthly transaction expenditure statistics for a tag
        monthly_amounts = self._calculate_monthly_amounts(tag)
        # Determine relative dates for the past year and the total expenditure amount
        today = date.today()
        today_last_year = today.replace(year=today.year - 1)
        past_year_total = self._get_interval_total(
            monthly_amounts, today_last_year, today
        )
        return (past_year_total, tag.tag_name, monthly_amounts)

    def _calculate_monthly_amounts(self, tag):
        monthly_amounts = {}
        for subtransaction in tag.subtransactions:
            # Determine the month of the subtransaction
            transaction_month = self._get_subtransaction_month(subtransaction)
            monthly_amounts.setdefault(transaction_month, 0)
            # For the given month, calculate the cumulative expenditure amount
            expenditure_subtotal = self._calculate_expenditure_subtotal(subtransaction)
            monthly_amounts[transaction_month] += expenditure_subtotal
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

    @staticmethod
    def _get_interval_total(monthly_amounts, start_date, end_date):
        # Given monthly tag totals, calculate the total expenditures in the interval
        # (boundaries inclusive)
        interval_subtotals = [
            month_subtotal
            for month, month_subtotal in monthly_amounts.items()
            if month >= start_date and month <= end_date
        ]
        return sum(interval_subtotals)
