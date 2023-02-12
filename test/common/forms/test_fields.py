"""Tests for custom form fields."""
from unittest.mock import Mock, patch

import pytest
from flask_wtf import FlaskForm
from wtforms.validators import ValidationError

from monopyly.common.forms.fields import *


@pytest.fixture
def mock_field_form(client_context):
    # This factory will return a simple form with just the specified field

    def _mock_field_form(test_field_class, *args, **kwargs):
        class TestForm(FlaskForm):
            field = test_field_class("Test", *args, **kwargs)
        return TestForm

    return _mock_field_form


class TestFields:
    # Test all non-ABC fields

    @patch("monopyly.common.forms.fields.parse_date")
    def test_date_field(self, mock_parse_date_method, mock_field_form):
        form_class = mock_field_form(DateField)
        mock_data = {"field": "test_date"}
        form = form_class(data=mock_data)
        mock_parse_date_method.assert_called_once_with(mock_data["field"])

    @pytest.mark.parametrize(
        "test_value, expected_value",
        [[100, 100.00],
         [100.003, 100.00],
         [100.999, 101.00],
         [None, None]]
    )
    def test_currency_field(self, mock_field_form, test_value, expected_value):
        form_class = mock_field_form(CurrencyField)
        form = form_class(data={"field": test_value})
        # Note that this is not a decimal.Decimal object, because it has not
        # yet been processed as submitteed `formdata`
        assert form.field.data == expected_value

    @pytest.mark.parametrize(
        "test_value, expected_value",
        [["test string", "test string"],
         ["  test string   ", "test string"],
         [None, ""]]
    )
    def test_string_field(self, mock_field_form, test_value, expected_value):
        form_class = mock_field_form(StringField)
        form = form_class(data={"field": test_value})
        assert form.field.data == expected_value

    @pytest.mark.parametrize(
        "test_value, validated",
        [["1234", True],
         ["12345", False],
         ["a1234", False]]
    )
    def test_last_four_digits_field_validation(self, mock_field_form,
                                               test_value, validated):
        form_class = mock_field_form(LastFourDigitsField)
        form = form_class(data={"field": test_value})
        v = form.validate()
        assert v == validated
