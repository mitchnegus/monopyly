"""
Tools for handling app errors.
"""

from flask import render_template


def render_error_template(exception):
    return render_template(f"core/errors/{exception.code}.html", exception=exception)
