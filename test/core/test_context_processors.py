from datetime import date
from unittest.mock import patch

import pytest

from monopyly.core.context_processors import inject_global_template_variables


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


class TestContextProcessors:
    @patch("monopyly.core.context_processors.date")
    def test_inject_date_today(self, mock_date_module, template_globals):
        assert template_globals["date_today"] == "2000-01-01"

    def test_inject_version(self, template_globals):
        assert template_globals["monopyly_version"] == "M.m.p.devX"

    @patch("monopyly.core.context_processors.import_module")
    def test_inject_missing_version(self, mock_importer):
        mock_importer.side_effect = ModuleNotFoundError
        template_globals = inject_global_template_variables()
        assert template_globals["monopyly_version"] == ""

    def test_inject_copyright(self, template_globals):
        assert "2000" in template_globals["copyright_statement"]
