"""Tests for form utilities."""
from unittest.mock import Mock, patch
from contextlib import nullcontext as does_not_raise

import pytest
from wtforms.validators import ValidationError

from monopyly.common.forms.utils import *


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

