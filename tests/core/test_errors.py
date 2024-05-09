"""Tests for error handling in the application."""

from unittest.mock import patch

import pytest
from werkzeug.exceptions import abort

from test_helpers import TestRoutes


def abort_factory(error_code):
    # A factory for creating functions that just run `abort` for a specific error code
    def abort_with_error(*args, **kwargs):
        abort(error_code)

    return abort_with_error


class TestAppErrors(TestRoutes):

    handled_error_codes = [
        400,
        401,
        403,
        404,
        405,
        408,
        418,
        # 425 -- not yet supported
        500,
    ]

    def validate_error_page(self, error_code):
        criteria = [
            self.page_title_includes_substring(f"{error_code}"),
            self.page_header_includes_substring("No dice!"),
        ]
        return all(criteria)

    @pytest.mark.parametrize("error_code", handled_error_codes)
    @patch("monopyly.core.routes.render_template")
    def test_error_code_generic(self, mock_render_template, error_code):
        mock_render_template.side_effect = abort_factory(error_code)
        self.get_route("/")
        assert self.validate_error_page(error_code)

    def test_404(self):
        self.get_route("/invalid")
        assert self.validate_error_page(404)

    def test_418(self):
        self.get_route("/change_password")
        assert self.validate_error_page(418)
