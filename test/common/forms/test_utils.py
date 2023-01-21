"""Tests for form utilities."""
from unittest.mock import Mock, patch
from contextlib import nullcontext as does_not_raise

import pytest
from flask_wtf import FlaskForm
from wtforms.fields import FieldList, StringField
from wtforms.validators import ValidationError

from monopyly.common.forms.utils import *


class MockForm(FlaskForm):
    mock_field_list = FieldList(StringField("mock_field"))


def test_extend_field_list_for_ajax(client_context):
    new_field = extend_field_list_for_ajax(MockForm, "mock_field_list", 2)
    assert "mock_field_list-2" in str(new_field)

@pytest.mark.parametrize(
    'validated, expectation',
    [[True, does_not_raise()],
     [False, pytest.raises(ValidationError)]]
)
@patch('monopyly.common.forms.utils.flash', new=lambda x: None)
def test_execute_on_form_validation(validated, expectation):
    func = Mock()
    form = Mock()
    form.validate.return_value = validated
    wrapped_func = execute_on_form_validation(func)
    with expectation:
        wrapped_func(form)

