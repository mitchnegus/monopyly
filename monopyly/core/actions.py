"""Module describing logical core actions (to be used in routes)."""

from datetime import datetime

import markdown


def get_timestamp():
    """Get a timestamp for backup filenames."""
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def format_readme_as_html_template(readme_text):
    """Given the README text in Markdown, convert it to a renderable HTML template."""
    # Convert Markdown to HTML
    raw_html_readme = markdown.markdown(readme_text, extensions=["fenced_code"])
    # Replace README relative links with app relevant links
    html_readme = raw_html_readme.replace('src="monopyly/static', 'src="/static')
    # Format the HTML as a valid Jinja template
    html_readme_template = (
        '{% extends "layout.html" %}'
        "{% block title %}About{% endblock %}"
        "{% block content %}"
        '  <div id="readme" class="about">'
        f"    {html_readme}"
        '    <div class="resource-links">'
        "      <h2>Links</h2>"
        '      <p><a href="{{ url_for("core.story") }}">Story</a></p>'
        '      <p><a href="{{ url_for("core.credits") }}">Credits</a></p>'
        "    </div>"
        "  </div>"
        "{% endblock %}"
    )
    return html_readme_template


def determine_summary_balance_svg_viewbox_width(currency_value):
    """
    Determine the width of the SVG viewBox attribute displayed in summary boxes.

    Parameters
    ----------
    currency_value : str
        A currency value, displayed in the format output by the
        `core.filters.make_currency` filter function.
    """
    # Set the per-character width contributions
    digit_width = 55
    punctuation_width = 25
    spacing_width = 25
    # Count the number of commas and non-comma characters in the non-decimal portion
    nondecimal_value = currency_value.rsplit(".", maxsplit=1)[0]
    comma_count = nondecimal_value.count(",")
    digit_count = len(nondecimal_value) - comma_count
    # Width is the total of the following subcomponents
    svg_currency_width_subcomponents = [
        digit_width * digit_count,  # ------------- total width of digits/sign
        punctuation_width * comma_count,  # ------- total width of commas
        punctuation_width + (2 * digit_width),  # - width of the decimal section
        digit_width + spacing_width,  # ----------- width of the dollar sign and spacing
    ]
    return max(400, sum(svg_currency_width_subcomponents))
