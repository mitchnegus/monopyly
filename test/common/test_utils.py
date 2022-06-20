"""Tests for general utilities."""
from datetime import date

import pytest

from monopyly.common.utils import (
    parse_date, get_next_occurrence_of_day, dedelimit_float, sort_by_frequency
)


class TestDateParser:

    def test_no_value_given(self):
        assert parse_date(None) is None

    def test_date_object_given(self):
        date_obj = date(2022, 4, 2)
        assert parse_date(date_obj) is date_obj

    @pytest.mark.parametrize(
        'date_string, date_obj_conversion',
        [['20220402', date(2022, 4, 2)],
         ['2022-04-02', date(2022, 4, 2)],
         ['2022.04.02', date(2022, 4, 2)],
         ['2022/04/02', date(2022, 4, 2)],
         ['2022/4/02', date(2022, 4, 2)],
         ['2022/04/2', date(2022, 4, 2)],
         ['2022/4/2', date(2022, 4, 2)],
         ['04-02-2022', date(2022, 4, 2)],
         ['04.02.2022', date(2022, 4, 2)],
         ['04/02/2022', date(2022, 4, 2)],
         ['4/02/2022', date(2022, 4, 2)],
         ['04/2/2022', date(2022, 4, 2)],
         ['04/02/22', date(2022, 4, 2)],
         ['4/2/22', date(2022, 4, 2)],
         # See https://docs.python.org/3/library/time.html#module-time for
         # pivot years of 2 digit years (1969-1999 and 2000-2068 as of 2022)
         ['19700101', date(1970, 1, 1)],
         ['19991231', date(1999, 12, 31)],
         ['20000101', date(2000, 1, 1)]]
    )
    def test_date_string_formats(self, date_string, date_obj_conversion):
        assert parse_date(date_string) == date_obj_conversion

    @pytest.mark.parametrize(
        'date_string',
        ['202204023',    # extra number
         '-20220402',    # wrong symbol
         '12345',        # arbitrary number
         '123abc',       # arbitrary string
         '2022#04#02',   # invalid delimiter
         '04//22',       # missing day value
         '2000/04',      # missing day section
         '22/04/02',     # backwards format
         '20220132',     # invalid day value
         '2022-01-32',   # invalid day value (dash delimited)
         '01/32/2022',   # invalid day value (slash delimited)
         '20221301',     # invalid month value
         '2022-13-01',   # invalid month value (dash delimited)
         '13/01/2022']   # invalid month value (slash delimited)
    )
    def test_invalid_date_string_formats(self, date_string):
        with pytest.raises(ValueError):
            parse_date(date_string)


class TestDateOccurrenceFinder:

    @pytest.mark.parametrize(
        'day, given_date, next_date',
        [[1, date(1990, 1, 15), date(1990, 2, 1)],
         [10, date(2000, 3, 15), date(2000, 4, 10)],
         [15, date(2005, 5, 1), date(2005, 5, 15)],
         [25, date(2020, 2, 14), date(2020, 2, 25)]]
    )
    def test_get_next_occurrence_of_day(self, day, given_date, next_date):
        assert get_next_occurrence_of_day(day, given_date) == next_date

    @pytest.mark.parametrize(
        'day, given_date',
        [[30, date(2020, 2, 27)],  # this month has no day 30
         [31, date(2020, 4, 30)]]   # this month has no day 31
    )
    def test_get_next_occurrence_of_day_invalid(self, day, given_date):
        with pytest.raises(ValueError):
            get_next_occurrence_of_day(day, given_date)


class TestFloatDedelimiter:

    @pytest.mark.parametrize(
        'value, expected_value',
        [['1,000', 1000.0],
         ['1,000.00', 1_000.0],
         ['5,000,000', 5_000_000.0],
         ['5,000,000.67', 5_000_000.67],
         [5000, 5000.0]]
    )
    def test_dedelimit_float(self, value, expected_value):
        assert dedelimit_float(value) == expected_value

    @pytest.mark.parametrize(
        'value, exception',
        [['abc', ValueError],
         [None, TypeError]]
    )
    def test_dedelimit_float_invalid(self, value, exception):
        with pytest.raises(exception):
            dedelimit_float(value)


class TestFrequencySorter:

    @pytest.mark.parametrize(
        'items, sorted_items',
        [[[1, 2, 3, 3], [3, 1, 2]],
         [[1, 1, 2, 3, 3], [1, 3, 2]],
         [[1, 1, 2, 3, 3, 3], [3, 1, 2]],
         [['one', 'two', 'two'], ['two', 'one']],
         [['a', 'a', 'b', 'c', 'c', 'c'], ['c', 'a', 'b']]]
    )
    def test_sort_by_frequency(self, items, sorted_items):
        assert sort_by_frequency(items) == sorted_items

