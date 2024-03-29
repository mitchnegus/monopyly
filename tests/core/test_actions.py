"""Tests for the actions performed by the credit blueprint."""
from datetime import datetime
from unittest.mock import patch

import pytest

from monopyly.core.actions import format_readme_as_html_template, get_timestamp


@patch("monopyly.core.actions.datetime")
def test_get_timestamp(mock_datetime_module):
    mock_datetime_module.now.return_value = datetime(2023, 4, 1, 0, 0, 0)
    timestamp = get_timestamp()
    assert timestamp == "20230401_000000"


def test_format_readme_as_html_template():
    test_readme = (
        "# Header\n"
        "This is text on the first line.\n"
        "This is text on the second line, along with a [link](link_url).\n"
        "![image](monopyly/static/image_url)\n"
        "This is text after the image.\n"
    )
    html_readme_template = format_readme_as_html_template(test_readme)
    assert '{% extends "layout.html" %}' in html_readme_template
    assert "<h1>Header</h1>" in html_readme_template
    assert '<img alt="image" src="/static/image_url" />' in html_readme_template
