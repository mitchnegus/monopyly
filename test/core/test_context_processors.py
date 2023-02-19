from datetime import date
from unittest.mock import patch

import pytest

from monopyly.core.context_processors import inject_global_template_variables


@pytest.fixture
def template_globals():
    # NOTE: Context processors must return a dictionary
    with patch("monopyly.core.context_processors.date") as mock_date_module:
        mock_date_module.today.return_value = date(2000, 1, 1)
        return inject_global_template_variables()


class TestContextProcessors:
    @patch("monopyly.core.context_processors.date")
    def test_inject_date_today(self, mock_date_module, template_globals):
        assert template_globals["date_today"] == "2000-01-01"

    def test_inject_version(self, template_globals):
        # This will remind you to change the version until making it automatic...
        assert template_globals["monopyly_version"] == "1.2.2.dev1"

    def test_inject_copyright(self, template_globals):
        assert "2000" in template_globals["copyright_statement"]
