"""Tests for general utilities."""
from datetime import date

import pytest

from monopyly.utils import parse_date


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

