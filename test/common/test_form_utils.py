"""Tests for form utilities."""
from unittest.mock import Mock, patch
from contextlib import nullcontext as does_not_raise

import pytest
from wtforms.validators import ValidationError

from monopyly.common.form_utils import *


@pytest.mark.parametrize(
    'validated, expectation',
    [[True, does_not_raise()],
     [False, pytest.raises(ValidationError)]]
)
@patch('monopyly.common.form_utils.flash', new=lambda x: None)
def test_execute_on_form_validation(validated, expectation):
    func = Mock()
    form = Mock()
    form.validate.return_value = validated
    wrapped_func = execute_on_form_validation(func)
    with expectation:
        wrapped_func(form)


class ConcreteAutocompleter(Autocompleter):

    _autocompletion_handler_map = {
        'test_field_0': Mock(),
        'test_field_1': Mock(),
        'test_field_2': Mock(),
    }


@pytest.fixture
def concrete_autocompleter():
    handler_map = ConcreteAutocompleter._autocompletion_handler_map
    for field, mock_handler_type in handler_map.items():
        mock_db = mock_handler_type.return_value
        mock_db.get_entries.return_value = [
            {'test_field_0': 0, 'test_field_1': 1, 'test_field_2': 2},
            {'test_field_0': 0, 'test_field_1': 2, 'test_field_2': 4},
            {'test_field_0': 1, 'test_field_1': 3, 'test_field_2': 5},
            {'test_field_0': 3, 'test_field_1': 3, 'test_field_2': 3},
        ]
    return ConcreteAutocompleter


class TestAutocompleter:

    def test_autocompletion_fields(self):
        autocompleter = ConcreteAutocompleter
        autocompletion_fields = ['test_field_0',
                                 'test_field_1',
                                 'test_field_2']
        assert autocompleter.autocompletion_fields == autocompletion_fields

    @pytest.mark.parametrize(
        'field, expected_suggestions',
        [['test_field_0', [0, 1, 3]],
         ['test_field_1', [3, 1, 2]],
         ['test_field_2', [2, 3, 4, 5]]]
    )
    @patch('monopyly.common.form_utils.validate_field', new=Mock())
    def test_autocomplete(self, concrete_autocompleter, field,
                          expected_suggestions):
        suggestions = concrete_autocompleter.autocomplete(field)
        assert suggestions == expected_suggestions


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

