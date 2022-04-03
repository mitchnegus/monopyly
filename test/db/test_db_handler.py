"""Tests for the database handler."""
from datetime import date
from unittest.mock import patch

import pytest

from monopyly.db.handler.queries import *


class TestHandlerQueryFunctions:

    test_fields = ['test_field_0', 'test_field_1', 'test_field_2']

    @pytest.mark.parametrize(
        'field_string',
        ['test_field',
         'SUM(test_field)',
         'COALESCE(test_field)',
         'MAX(test_field)',
         'MIN(test_field)',
         'COALESCE(SUM(test_field))']
    )
    def test_strip_function(self, field_string):
        assert strip_function(field_string) == 'test_field'

    @pytest.mark.parametrize(
        'placeholders, placeholder_string',
        [[(1, ), '?'],
         [(1, 2), '?, ?'],
         [(1, 2, 3), '?, ?, ?'],
         [('a', 'b', 'c'), '?, ?, ?'],
         [(1, 2, 'three'), '?, ?, ?']]
    )
    def test_reserve_places(self, placeholders, placeholder_string):
        assert reserve_places(placeholders) == placeholder_string

    @pytest.mark.parametrize(
        'placeholder, placeholder_tuple',
        [[1, (1,)],
         [2, (2,)],
         [3.14, (3.14,)],
         ['test', ('test',)],
         [None, ()]]
    )
    def test_fill_place(self, placeholder, placeholder_tuple):
        assert fill_place(placeholder) == placeholder_tuple

    @pytest.mark.parametrize(
        'placeholders, placeholder_tuple',
        [[(1, 2, 3), (1, 2, 3)],
         [[2, 4, 6], (2, 4, 6)],
         [[3.1415, 3.1068], (3.1415, 3.1068)],
         [['test0', 'test1', 'test2'], ('test0', 'test1', 'test2')],
         [[1, 2.0, 'three'], (1, 2.0, 'three')],
         [None, ()]]
    )
    def test_fill_places(self, placeholders, placeholder_tuple):
        assert fill_places(placeholders) == placeholder_tuple

    @pytest.mark.parametrize(
        'item, db_item_name, prefix, filter_output',
        [['item', 'db_item', 'AND', 'AND db_item = ?'],
         ['item', 'db_item', 'OR', 'OR db_item = ?'],
         ['item', 'db_item', '', ' db_item = ?'],
         [1, 'db_item', 'AND', 'AND db_item = ?'],
         [None, 'db_item', '', '']]
    )
    def test_filter_item(self, item, db_item_name, prefix, filter_output):
        db_filter = filter_item(item, db_item_name, prefix)
        assert db_filter == filter_output

    @pytest.mark.parametrize(
        'items, db_item_name, prefix, filter_output',
        [[('item0', 'item1'), 'db_item', 'AND', 'AND db_item IN (<test>)'],
         [('item0', 'item1'), 'db_item', 'OR', 'OR db_item IN (<test>)'],
         [('item0', 'item1'), 'db_item', '', ' db_item IN (<test>)'],
         [(1, 2, 3), 'db_item', 'AND', 'AND db_item IN (<test>)'],
         [('item',), 'db_item', 'AND', 'AND db_item IN (<test>)'],
         [('item0', 'item1'), 'db_item', '', ' db_item IN (<test>)'],
         [None, 'db_item', '', '']]
    )
    @patch('monopyly.db.handler.queries.reserve_places', return_value='<test>')
    def test_filter_items(self, mock_function, items, db_item_name, prefix,
                          filter_output):
        db_filter = filter_items(items, db_item_name, prefix)
        assert db_filter == filter_output

    @pytest.mark.parametrize(
        'start_date, end_date, db_date_name, prefix, filter_output',
        [[date(2000, 1, 2), date(2001, 3, 4), 'db_date', 'AND',
          "AND db_date >= 2000-01-02 AND db_date <= 2001-03-04"],
         [date(2000, 1, 2), date(2001, 3, 4), 'db_date', 'OR',
          "OR db_date >= 2000-01-02 AND db_date <= 2001-03-04"],
         [date(2000, 1, 2), date(2001, 3, 4), 'db_date', '',
          " db_date >= 2000-01-02 AND db_date <= 2001-03-04"],
         [date(2000, 1, 2), None, 'db_date', 'AND',
          "AND db_date >= 2000-01-02"],
         [None, date(2001, 3, 4), 'db_date', 'AND',
          "AND db_date <= 2001-03-04"],
         [None, None, 'db_date', 'AND',
          ""]]
    )
    def test_filter_dates(self, start_date, end_date, db_date_name, prefix,
                          filter_output):
        db_filter = filter_dates(start_date, end_date, db_date_name, prefix)
        assert db_filter == filter_output

    def test_prepare_date_query(self):
        assert prepare_date_query('test') == 'test "test [date]"'

    @pytest.mark.parametrize(
        'sort_order', ['ASC', 'DESC']
    )
    def test_validate_sort_order(self, sort_order):
        validate_sort_order(sort_order)


    @pytest.mark.parametrize(
        'sort_order', ['test', None]
    )
    def test_validate_sort_order_invalid(self, sort_order):
        with pytest.raises(ValueError):
            validate_sort_order(sort_order)

    test_fields = ['test_field_0', 'test_field_1', 'test_field_2']

    @pytest.mark.parametrize(
        'field, field_list',
        [['test_field_0', None],
         ['test_field_1', None],
         ['table.test_field_1', None],
         ['test_field_a', ('test_field_a', 'test_field_b', 'test_field_c')],
         ['test_field_b', ('test_field_a', 'test_field_b', 'test_field_c')]]
    )
    @patch('monopyly.db.handler.queries.ALL_FIELDS', new=test_fields)
    def test_validate_field(self, field, field_list):
        validate_field(field, field_list)

    @pytest.mark.parametrize(
        'field, field_list',
        [['test_field_a', None],
         ['table.test_field_a', None],
         ['test_field_0', ('test_field_a', 'test_field_b', 'test_field_c')]]
    )
    @patch('monopyly.db.handler.queries.ALL_FIELDS', new=test_fields)
    def test_validate_field_invalid(self, field, field_list):
         with pytest.raises(ValueError):
            validate_field(field, field_list)

    @pytest.mark.parametrize(
        'fields, id_field, convert_dates, selected_fields',
        [[None, None, True,
          '*'],
         [('test_field',), None, True,
         'test_field'],
         [('test_field_0', 'test_field_1'), None, True,
         'test_field_0, test_field_1'],
         [('test_field_0', 'test_field_1'), 'id', True,
         'id, test_field_0, test_field_1'],
         [('test_field', 'test_field_date'), None, True,
         'test_field, <test_date_query>'],
         [('test_field', 'test_field_date'), None, False,
         'test_field, test_field_date']]
    )
    @patch('monopyly.db.handler.queries.validate_field', return_value=True)
    @patch('monopyly.db.handler.queries.prepare_date_query',
           return_value='<test_date_query>')
    def test_select_fields(self, mock_validate_function, mock_prepare_function,
                           fields, id_field, convert_dates, selected_fields):
        db_fields = select_fields(fields, id_field, convert_dates)
        assert db_fields == selected_fields
