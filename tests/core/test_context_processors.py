from unittest.mock import patch

import pytest

from monopyly.core.actions import calculate_svg_viewbox_balance_width
from monopyly.core.context_processors import (
    inject_global_template_variables,
    inject_utility_functions,
)


@pytest.fixture
def utility_functions():
    # NOTE: Context processors must return a dictionary
    return inject_utility_functions()


class TestContextProcessors:
    @patch("monopyly.core.context_processors.define_basic_template_global_variables")
    def test_inject_template_globals(self, mock_global_variable_function):
        template_globals = inject_global_template_variables()
        assert template_globals == mock_global_variable_function.return_value

    def test_inject_utility(self, utility_functions):
        expected_action = calculate_svg_viewbox_balance_width
        assert utility_functions["calculate_svg_balance_width"] == expected_action
