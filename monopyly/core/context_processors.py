"""
Filters defined for the application.
"""

from dry_foundation.web import define_basic_template_global_variables

from .actions import calculate_svg_viewbox_balance_width
from .blueprint import bp


@bp.app_context_processor
def inject_global_template_variables():
    """Inject template variables globally into the template context."""
    return define_basic_template_global_variables("monopyly._version")


@bp.app_context_processor
def inject_utility_functions():
    """Inject utility functions globally into the template context."""
    utility_functions = {
        "calculate_svg_balance_width": calculate_svg_viewbox_balance_width,
    }
    return utility_functions
