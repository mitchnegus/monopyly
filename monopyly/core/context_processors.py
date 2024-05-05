"""
Filters defined for the application.
"""

from datetime import date
from importlib import import_module

from .actions import determine_summary_balance_svg_viewbox_width
from .blueprint import bp


@bp.app_context_processor
def inject_global_template_variables():
    """Inject template variablees globally into the template context."""
    template_globals = {
        "app_version": _display_version(),
        "copyright_statement": f"© {date.today().year}",
        "date_today": date.today(),
    }
    return template_globals


@bp.app_context_processor
def inject_utility_functions():
    """Inject utility functions globally into the template context."""
    utility_functions = {
        "calculate_summary_balance_width": determine_summary_balance_svg_viewbox_width,
    }
    return utility_functions


def _display_version():
    """Show the version (without commit information)."""
    try:
        version = import_module("monopyly._version").version
    except ModuleNotFoundError:
        # Fallback action in case Hatch VCS fails
        display_version = ""
    else:
        display_version = version.split("+")[0]
    return display_version
