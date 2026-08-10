"""Module describing logical analytics actions (to be used in routes)."""

from .tools import TagStatisticsChartData


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
