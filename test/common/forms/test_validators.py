"""Tests for form utilities."""
from unittest.mock import patch

import pytest
from wtforms.validators import ValidationError

from monopyly.common.forms.validators import *


@pytest.fixture
def mock_form():
    with patch('flask_wtf.FlaskForm') as mock_form:
        yield mock_form


@pytest.fixture
def mock_field():
    with patch('wtforms.fields.Field') as mock_field:
        yield mock_field


class TestValidators:

    @pytest.mark.parametrize(
        'value', [0, 1, 2, 3, 1000]
    )
    def test_numerals_only(self, mock_form, mock_field, value):
        validator = NumeralsOnly()
        mock_field.data = value
        validator(mock_form, mock_field)

    @pytest.mark.parametrize(
        'value', ['a', '1a', '1.1']
    )
    def test_numerals_only_invalid(self, mock_form, mock_field, value):
        validator = NumeralsOnly()
        mock_field.data = value
        with pytest.raises(ValidationError):
            validator(mock_form, mock_field)

    def test_numerals_only_custom_message(self):
        validator = NumeralsOnly(message='test message')
        assert validator.message == 'test message'

    @pytest.mark.parametrize(
        'value', [0, 1, 2, 3, 1000]
    )
    def test_selection_not_blank(self, mock_form, mock_field, value):
        validator = SelectionNotBlank()
        mock_field.data = value
        validator(mock_form, mock_field)

    def test_selection_not_blank_invalid(self, mock_form, mock_field):
        validator = SelectionNotBlank()
        mock_field.data = -1
        with pytest.raises(ValidationError):
            validator(mock_form, mock_field)

    def test_selection_not_blank_custom_blank(self, mock_form, mock_field):
        validator = SelectionNotBlank(blank=0)
        mock_field.data = -1
        validator(mock_form, mock_field)

    def test_selection_not_blank_custom_message(self):
        validator = SelectionNotBlank(message='test message')
        assert validator.message == 'test message'

