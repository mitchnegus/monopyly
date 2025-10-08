"""Tests for the actions performed by the credit blueprint."""

import pytest

from monopyly.core.actions import (
    convert_changelog_to_html_template,
    convert_readme_to_html_template,
    determine_summary_balance_svg_viewbox_width,
)


def test_convert_readme_to_html_template(tmp_path):
    test_readme_path = tmp_path / "test_readme.md"
    with test_readme_path.open("w") as test_file:
        test_file.write(
            "# Header\n"
            "This is text on the first line.\n"
            "This is text on the second line, along with a [link](link_url).\n"
            "![image](monopyly/static/image_url)\n"
            "This is text after the image.\n"
        )
    html_readme_template = convert_readme_to_html_template(test_readme_path)
    assert '{% extends "layout.html" %}' in html_readme_template
    assert "<h1>Header</h1>" in html_readme_template
    assert '<img alt="image" src="/static/image_url" />' in html_readme_template


def test_convert_changelog_to_html_template(tmp_path):
    test_changelog_path = tmp_path / "test_changelog.md"
    with test_changelog_path.open("w") as test_file:
        test_file.write(
            "# Header\n"
            "This is text on the first line.\n"
            "This is text on the second line, along with a [link](link_url).\n"
            'The third line also has a link to the <a href="README.md">README</a>.\n'
            "This is text after the image.\n"
        )
    html_changelog_template = convert_changelog_to_html_template(test_changelog_path)
    assert '{% extends "layout.html" %}' in html_changelog_template
    assert "<h1>Header</h1>" in html_changelog_template
    assert '<a href="{{ url_for("core.about") }}">' in html_changelog_template


@pytest.mark.parametrize(
    ("number", "width"),
    [
        ("1.00", 400),
        ("0.99", 400),
        ("100.00", 400),
        ("2,000.00", 460),
        ("2,000.20", 460),
        ("3,030.33", 460),
        ("-3,030.33", 515),
        ("33,030.33", 515),
        ("333,030.33", 570),
        ("3,303,030.33", 650),
    ],
)
def test_summary_balance_viewbox_width_calculation(number, width):
    assert determine_summary_balance_svg_viewbox_width(number) == width
