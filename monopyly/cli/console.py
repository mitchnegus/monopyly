"""Console utilities for the application."""

import click

CLI_COLORS = {
    "white": 15,
    "deep_sky_blue1": 39,
}


def echo_text(text, color=None):
    """Echo text to the terminal in a given color."""
    click.secho(text, fg=CLI_COLORS.get(color))
