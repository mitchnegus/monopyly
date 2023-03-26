"""Tests for the actions performed by the credit blueprint."""
import pytest

from monopyly.core.actions import format_readme_as_html_template


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
