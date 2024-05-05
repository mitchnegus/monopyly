from datetime import date
from unittest.mock import patch

import pytest

from monopyly.core.actions import determine_summary_balance_svg_viewbox_width
from monopyly.core.context_processors import (
    inject_global_template_variables,
    inject_utility_functions,
)


@pytest.fixture
def template_globals():
    # NOTE: Context processors must return a dictionary
    with (
        patch("monopyly.core.context_processors._display_version") as mock_version_func,
        patch("monopyly.core.context_processors.date") as mock_date_module,
    ):
        mock_version_func.return_value = "M.m.p.devX"
        mock_date_module.today.return_value = date(2000, 1, 1)
        return inject_global_template_variables()


@pytest.fixture
def utility_functions():
    # NOTE: Context processors must return a dictionary
    return inject_utility_functions()


class TestContextProcessors:
    @patch("monopyly.core.context_processors.date")
    def test_inject_date_today(self, mock_date_module, template_globals):
        assert template_globals["date_today"] == date(2000, 1, 1)

    def test_inject_version(self, template_globals):
        assert template_globals["app_version"] == "M.m.p.devX"

    @patch("monopyly.core.context_processors.import_module")
    def test_inject_missing_version(self, mock_importer):
        mock_importer.side_effect = ModuleNotFoundError
        template_globals = inject_global_template_variables()
        assert template_globals["app_version"] == ""

    def test_inject_copyright(self, template_globals):
        assert "2000" in template_globals["copyright_statement"]

    def test_inject_utility(self, utility_functions):
        expected_action = determine_summary_balance_svg_viewbox_width
        assert utility_functions["calculate_summary_balance_width"] == expected_action
