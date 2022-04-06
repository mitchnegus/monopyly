"""
Filters defined for the application.
"""
from datetime import date

from . import core_bp


@core_bp.app_context_processor
def inject_date_today():
    """Inject a variable with today's date into the template context."""
    return dict(date_today=str(date.today()))

