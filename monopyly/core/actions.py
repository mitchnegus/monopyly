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
