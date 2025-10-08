"""Module describing logical core actions (to be used in routes)."""

import markdown


class MarkdownConverter:
    """An object to convert Markdown to HTML."""

    replacements = {
        "src": [
            ["monopyly/static", "/static"],
        ],
        "href": [
            ["README.md", '{{ url_for("core.about") }}'],
            ["CHANGELOG.md", '{{ url_for("core.changelog") }}'],
        ],
    }

    @classmethod
    def convert(cls, markdown_path, title, id_="", class_="", extra_content=""):
        """Given a Markdown file, convert it to a renderable HTML template."""
        raw_markdown = cls._read_markdown(markdown_path)
        html_content = cls._convert_markdown_to_html(raw_markdown)
        return cls._generate_html_template(
            html_content, title, id_=id_, class_=class_, extra_content=extra_content
        )

    @staticmethod
    def _read_markdown(markdown_path):
        with markdown_path.open(encoding="utf-8") as markdown_file:
            raw_markdown = markdown_file.read()
        return raw_markdown

    @classmethod
    def _convert_markdown_to_html(cls, raw_markdown):
        raw_html = markdown.markdown(raw_markdown, extensions=["fenced_code"])
        return cls._replace_links(raw_html)

    @classmethod
    def _replace_links(cls, raw_html):
        html = raw_html
        for tag, pairs in cls.replacements.items():
            for original, replacement in pairs:
                html = html.replace(f'{tag}="{original}', f'{tag}="{replacement}')
        return html

    @staticmethod
    def _generate_html_template(content, title, id_="", class_="", extra_content=""):
        # Format the HTML as a valid Jinja template
        html_template = (
            '{% extends "layout.html" %}'
            "{% block title %}"
            f"  {title}"
            "{% endblock %}"
            "{% block content %}"
            f'  <div id="{id_}" class="{class_}">'
            f"    {content}"
            f"    {extra_content}"
            "{% endblock %}"
        )
        return html_template


def convert_readme_to_html_template(readme_path):
    """Given a README file in Markdown, convert it to a renderable HTML template."""
    return MarkdownConverter.convert(
        readme_path,
        title="About",
        id_="readme",
        class_="about",
        extra_content=(
            '<div class="resource-links">'
            "  <h2>Links</h2>"
            '  <p><a href="{{ url_for("core.story") }}">Story</a></p>'
            '  <p><a href="{{ url_for("core.application_credits") }}">Credits</a></p>'
            "</div>"
        ),
    )


def convert_changelog_to_html_template(changelog_path):
    """Given a CHANGELOG file in Markdown, convert it to a renderable HTML template."""
    return MarkdownConverter.convert(
        changelog_path,
        title="Changes",
        id_="changelog",
    )


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
